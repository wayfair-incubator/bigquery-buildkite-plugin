import json
import logging
import os
from pathlib import Path
from typing import TextIO

from gbq import BigQuery

from plugin_scripts.pipeline_exceptions import (
    DatasetSchemaDirectoryNonExistent,
    DeployFailed,
    MissingConfigError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _validate_env_variables():
    """Validate that all required environment variables are set."""
    if not os.environ.get("gcp_project"):
        raise MissingConfigError("Missing `gcp_project` config")

    if not os.environ.get("dataset_schema_directory"):
        raise MissingConfigError("Missing `dataset_schema_directory` config")


def _validate_if_path_exists():
    """Validate that the dataset schema directory exists."""
    dataset_schema_directory = os.environ.get("dataset_schema_directory")
    return Path(dataset_schema_directory).is_dir()


def _deploy():
    """Main deployment function that orchestrates the BigQuery deployment."""
    dataset_schema_directory = os.environ.get("dataset_schema_directory")
    # Optional: without a key, gbq uses Application Default Credentials
    service_account = os.environ.get("credentials") or None
    gcp_project = os.environ.get("gcp_project")

    # Newline-separated, so file names containing commas survive
    updated_files = os.environ.get("updated_files", "").splitlines()
    execute_only_changed_files = _str_to_bool(
        os.environ.get("execute_only_changed_files", "true")
    )
    fail_pipeline_on_first_exception = _str_to_bool(
        os.environ.get("fail_pipeline_on_first_exception", "true")
    )

    logger.info(f"Starting deployment to project: {gcp_project}")
    logger.info(f"Schema directory: {dataset_schema_directory}")
    logger.info(f"Execute only changed files: {execute_only_changed_files}")

    try:
        bq = BigQuery(svc_account=service_account, project=gcp_project)
        deploy_failed = _deploy_from_directory(
            bq,
            gcp_project,
            dataset_schema_directory,
            updated_files,
            execute_only_changed_files,
            fail_pipeline_on_first_exception,
        )
    except Exception as e:
        logger.error(f"Deployment failed with error: {e}", exc_info=True)
        raise DeployFailed(f"Deployment failed: {e}") from e

    if deploy_failed:
        raise DeployFailed("One or more files failed to deploy")


def _deploy_from_directory(
    bq: BigQuery,
    gcp_project: str,
    dataset_schema_directory: str,
    updated_files: list[str],
    execute_only_changed_files: bool,
    fail_pipeline_on_first_exception: bool,
) -> bool:
    """
    Deploy all schema files from the specified directory.

    Args:
        bq: BigQuery client instance
        gcp_project: GCP project ID
        dataset_schema_directory: Root directory containing schema files
        updated_files: List of files that have been updated
        execute_only_changed_files: Whether to only process changed files
        fail_pipeline_on_first_exception: Whether to fail fast on first error

    Returns:
        bool: True if any deployment failed, False otherwise
    """
    deploy_failed = False
    deployed_count = 0
    base_path = Path(dataset_schema_directory)

    # Compare resolved paths so `./schemas/x.json`, `schemas/x.json` and an
    # absolute path all name the same file
    changed = {Path(f).resolve() for f in updated_files if f}

    logger.info(f"Scanning directory: {base_path}")

    for root, dirs, files in os.walk(dataset_schema_directory):
        # Visit directories and files in a stable order so deployments are
        # reproducible
        dirs.sort()
        root_path = Path(root)
        dataset = root_path.name  # Extract dataset name from directory

        for file in sorted(files):
            file_path = root_path / file  # Proper path construction
            file_extension = file_path.suffix.lstrip(".")
            file_stem = file_path.stem

            # Skip non-schema files
            if file_extension not in ("sql", "json"):
                logger.debug(f"Skipping non-schema file: {file_path}")
                continue

            # Check if we should process this file based on changes
            if execute_only_changed_files and file_path.resolve() not in changed:
                logger.debug(f"Skipping unchanged file: {file_path}")
                continue

            logger.info(f"Processing file: {file_path}")

            try:
                with file_path.open() as contents:
                    if file_extension == "sql":
                        _deploy_sql_script(
                            bq=bq,
                            contents=contents,
                            file_name=file_stem,
                        )
                    elif file_extension == "json":
                        _deploy_json_structure(
                            bq=bq,
                            contents=contents,
                            dataset=dataset,
                            file_name=file_stem,
                            gcp_project=gcp_project,
                        )
                deployed_count += 1
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {file_path}: {e}")
                deploy_failed = True
                if fail_pipeline_on_first_exception:
                    return deploy_failed
            except FileNotFoundError as e:
                logger.error(f"File not found: {file_path}: {e}")
                deploy_failed = True
                if fail_pipeline_on_first_exception:
                    return deploy_failed
            except Exception as e:
                logger.error(f"Failed to deploy {file_path}: {e}", exc_info=True)
                deploy_failed = True
                if fail_pipeline_on_first_exception:
                    return deploy_failed

    if deploy_failed:
        logger.error("Deployment completed with errors")
    elif deployed_count == 0 and execute_only_changed_files:
        logger.info("No changed schema files to deploy")
    else:
        logger.info(
            f"Deployment completed successfully ({deployed_count} file(s) deployed)"
        )

    return deploy_failed


def _deploy_json_structure(
    bq: BigQuery,
    contents: TextIO,
    dataset: str,
    file_name: str,
    gcp_project: str,
):
    """
    Deploy a JSON schema definition to BigQuery.

    Args:
        bq: BigQuery client instance
        contents: File contents
        dataset: Dataset name
        file_name: Base name of the file (without extension)
        gcp_project: GCP project ID
    """
    structure_full_name = f"{gcp_project}.{dataset}.{file_name}"
    logger.info(f"Updating schema for {structure_full_name}")

    try:
        schema = json.loads(contents.read())
        bq.create_or_update_structure(
            project=gcp_project,
            dataset=dataset,
            structure_id=file_name,
            json_schema=schema,
        )
        logger.info(f"Successfully updated schema for {structure_full_name}")
    except Exception as e:
        logger.error(f"Failed to update schema for {structure_full_name}: {e}")
        raise


def _deploy_sql_script(bq: BigQuery, contents: TextIO, file_name: str):
    """
    Execute a SQL script in BigQuery.

    Args:
        bq: BigQuery client instance
        contents: File contents
        file_name: Base name of the file (without extension)
    """
    logger.info(f"Executing SQL file: {file_name}.sql")

    try:
        query = contents.read()
        bq.execute(query=query)
        logger.info(f"Successfully executed SQL file: {file_name}.sql")
    except Exception as e:
        logger.error(f"Failed to execute SQL file {file_name}.sql: {e}")
        raise


def _str_to_bool(value: str):
    return value.lower() in ("yes", "true", "t", "1")


def main():
    _validate_env_variables()
    if _validate_if_path_exists():
        _deploy()
    else:
        raise DatasetSchemaDirectoryNonExistent
