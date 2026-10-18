import json
import logging
import os
import re
import time
from pathlib import Path
from typing import TextIO

from gbq import BigQuery
from gbq.dto import StructureType
from gbq.exceptions import InvalidDefinitionException
from gbq.helpers import get_bq_schema_from_json_schema
from google.cloud.bigquery import QueryJobConfig

from plugin_scripts.pipeline_exceptions import (
    DatasetSchemaDirectoryNonExistent,
    DeployFailed,
    MissingConfigError,
)
from plugin_scripts.plan import PlanRecorder
from plugin_scripts.report import DeployResult, annotation_markdown, summary_text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


MODES = ("apply", "plan", "validate")


def _validate_env_variables():
    """Validate that all required environment variables are set."""
    if not os.environ.get("gcp_project"):
        raise MissingConfigError("Missing `gcp_project` config")

    if not os.environ.get("dataset_schema_directory"):
        raise MissingConfigError("Missing `dataset_schema_directory` config")

    mode = os.environ.get("mode", "apply")
    if mode not in MODES:
        raise MissingConfigError(f"Invalid `mode` {mode!r}, use one of {MODES}")


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
    mode = os.environ.get("mode", "apply")
    if mode != "apply":
        logger.info(f"Mode: {mode} (nothing will be changed)")

    results: list[DeployResult] = []
    try:
        bq: BigQuery | None = None
        recorder: PlanRecorder | None = None
        if mode != "validate":  # validating needs no credentials
            bq = BigQuery(svc_account=service_account, project=gcp_project)
            if mode == "plan":
                recorder = PlanRecorder(bq.bq_client)
                bq.bq_client = recorder  # gbq now records writes instead of sending
        deploy_failed = _deploy_from_directory(
            bq,
            gcp_project,
            dataset_schema_directory,
            updated_files,
            execute_only_changed_files,
            fail_pipeline_on_first_exception,
            results,
            _parse_patterns(os.environ.get("include_patterns")),
            _parse_patterns(os.environ.get("exclude_patterns")),
            mode,
            recorder,
        )
    except Exception as e:
        logger.error(f"Deployment failed with error: {e}", exc_info=True)
        raise DeployFailed(f"Deployment failed: {e}") from e
    finally:
        _report(results, gcp_project, mode)

    if deploy_failed:
        raise DeployFailed("One or more files failed to deploy")


def _report(
    results: list[DeployResult], gcp_project: str | None, mode: str = "apply"
) -> None:
    """Log a per-file summary and, if asked, write the Buildkite annotation file."""
    if results:
        logger.info(f"Summary: {summary_text(results)}")

    annotation_file = os.environ.get("annotation_file")
    if annotation_file:
        try:
            Path(annotation_file).write_text(
                annotation_markdown(results, gcp_project or "", mode)
            )
        except OSError as e:
            logger.warning(f"Could not write the annotation file: {e}")


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """
    Translate a glob into a regex over `/`-separated relative paths.

    `*` and `?` stay within one path segment, `**` crosses segments and `**/` also
    matches no directory at all (so `**/a.json` matches `a.json`).
    """
    regex = ""
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if pattern.startswith("**/", i):
            regex += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            regex += ".*"
            i += 2
        elif char == "*":
            regex += "[^/]*"
            i += 1
        elif char == "?":
            regex += "[^/]"
            i += 1
        else:
            regex += re.escape(char)
            i += 1
    return re.compile(regex + r"\Z")


def _parse_patterns(raw: str | None) -> list[re.Pattern[str]]:
    return [_glob_to_regex(p.strip()) for p in (raw or "").splitlines() if p.strip()]


def _is_selected(
    relative_path: str,
    include: list[re.Pattern[str]],
    exclude: list[re.Pattern[str]],
) -> bool:
    """A file is selected if it matches an include (or none are set) and no exclude."""
    if include and not any(p.match(relative_path) for p in include):
        return False
    return not any(p.match(relative_path) for p in exclude)


def _process_file(
    mode: str,
    bq: BigQuery | None,
    recorder: PlanRecorder | None,
    contents: TextIO,
    is_sql: bool,
    dataset: str,
    file_name: str,
    gcp_project: str,
) -> tuple[str, str]:
    """Handle one file for the mode; return its result status and detail."""
    if mode == "validate":
        if is_sql:
            _validate_sql_script(contents, file_name)
        else:
            _validate_json_structure(contents, file_name)
        return "valid", ""

    assert bq is not None  # only validate runs without a client
    if is_sql:
        if mode == "plan":
            return "valid", _dry_run_sql_script(bq, contents, file_name)
        _deploy_sql_script(bq=bq, contents=contents, file_name=file_name)
        return "deployed", ""

    since = len(recorder.changes) if recorder else 0
    _deploy_json_structure(
        bq=bq,
        contents=contents,
        dataset=dataset,
        file_name=file_name,
        gcp_project=gcp_project,
    )
    if recorder is None:
        return "deployed", ""
    change = recorder.change_since(since)
    status = {"create": "would-create", "update": "would-update"}.get(
        change.action, "unchanged"
    )
    return status, "; ".join(change.details)


def _validate_json_structure(contents: TextIO, file_name: str) -> None:
    """Check a definition with gbq's own parser, without credentials or network."""
    logger.info(f"Validating definition {file_name}.json")
    structure = BigQuery._get_structure(json.loads(contents.read()))
    if structure.type == StructureType.stored_procedure:
        BigQuery._handle_routine_arguments(structure)
    elif structure.type in (StructureType.table, StructureType.view):
        if structure.table_schema:
            get_bq_schema_from_json_schema(structure.table_schema)
    else:
        raise InvalidDefinitionException("Missing required structure definition")


def _validate_sql_script(contents: TextIO, file_name: str) -> None:
    logger.info(f"Validating SQL file {file_name}.sql")
    if not contents.read().strip():
        raise InvalidDefinitionException("The SQL file is empty")


def _dry_run_sql_script(bq: BigQuery, contents: TextIO, file_name: str) -> str:
    """Have BigQuery check the SQL without running it; return what it would scan."""
    logger.info(f"Dry-running SQL file: {file_name}.sql")
    job = bq.execute(
        query=contents.read(),
        job_config=QueryJobConfig(dry_run=True, use_query_cache=False),
    )
    scanned = job.total_bytes_processed
    return "" if scanned is None else f"would process {scanned} bytes"


def _record(
    results: list[DeployResult],
    file_path: Path,
    target: str,
    started: float,
    status: str,
    error: str = "",
    detail: str = "",
) -> None:
    results.append(
        DeployResult(
            path=str(file_path),
            kind="sql" if file_path.suffix == ".sql" else "structure",
            target=target,
            status=status,
            seconds=time.monotonic() - started,
            error=error,
            detail=detail,
        )
    )


def _deploy_from_directory(
    bq: BigQuery | None,
    gcp_project: str,
    dataset_schema_directory: str,
    updated_files: list[str],
    execute_only_changed_files: bool,
    fail_pipeline_on_first_exception: bool,
    results: list[DeployResult] | None = None,
    include: list[re.Pattern[str]] | None = None,
    exclude: list[re.Pattern[str]] | None = None,
    mode: str = "apply",
    recorder: PlanRecorder | None = None,
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
        results: If given, a DeployResult is appended for every file processed
        include: Globs (relative to the directory); only matching files are deployed
        exclude: Globs (relative to the directory); matching files are skipped
        mode: "apply", "plan" (read-only, shows what would change) or "validate"
        recorder: In plan mode, the recorder wrapped around gbq's client

    Returns:
        bool: True if any deployment failed, False otherwise
    """
    deploy_failed = False
    deployed_count = 0
    if results is None:
        results = []
    include = include or []
    exclude = exclude or []
    selected_any = False
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

            if not _is_selected(
                file_path.relative_to(base_path).as_posix(), include, exclude
            ):
                logger.debug(f"Skipping file excluded by include/exclude: {file_path}")
                continue
            selected_any = True

            # Check if we should process this file based on changes
            if execute_only_changed_files and file_path.resolve() not in changed:
                logger.debug(f"Skipping unchanged file: {file_path}")
                continue

            logger.info(f"Processing file: {file_path}")

            target = (
                file_stem
                if file_extension == "sql"
                else f"{gcp_project}.{dataset}.{file_stem}"
            )
            started = time.monotonic()

            try:
                with file_path.open() as contents:
                    status, detail = _process_file(
                        mode=mode,
                        bq=bq,
                        recorder=recorder,
                        contents=contents,
                        is_sql=file_extension == "sql",
                        dataset=dataset,
                        file_name=file_stem,
                        gcp_project=gcp_project,
                    )
                deployed_count += 1
                _record(results, file_path, target, started, status, detail=detail)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {file_path}: {e}")
                _record(
                    results, file_path, target, started, "failed", f"Invalid JSON: {e}"
                )
                deploy_failed = True
                if fail_pipeline_on_first_exception:
                    return deploy_failed
            except FileNotFoundError as e:
                logger.error(f"File not found: {file_path}: {e}")
                _record(
                    results,
                    file_path,
                    target,
                    started,
                    "failed",
                    f"File not found: {e}",
                )
                deploy_failed = True
                if fail_pipeline_on_first_exception:
                    return deploy_failed
            except Exception as e:
                logger.error(f"Failed to deploy {file_path}: {e}", exc_info=True)
                _record(
                    results,
                    file_path,
                    target,
                    started,
                    "failed",
                    f"{type(e).__name__}: {e}",
                )
                deploy_failed = True
                if fail_pipeline_on_first_exception:
                    return deploy_failed

    if include and not selected_any:
        logger.warning("No schema file matches the include patterns")

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
