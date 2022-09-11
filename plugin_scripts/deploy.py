import json
import os
import sys
from typing import List, TextIO

from gbq import BigQuery

from plugin_scripts.pipeline_exceptions import (
    DatasetSchemaDirectoryNonExistent,
    DeployFailed,
)

sys.tracebacklimit = 0


def _validate_env_variables():
    if not os.environ.get("gcp_project"):
        raise Exception("Missing `gcp_project` config")

    if not os.environ.get("dataset_schema_directory"):
        raise Exception("Missing `dataset_schema_directory` config")

    if not os.environ.get("credentials"):
        raise Exception("Missing `credentials` config")


def _validate_if_path_exists():
    dataset_schema_directory = os.environ.get("dataset_schema_directory")
    return os.path.isdir(dataset_schema_directory)


def _deploy():
    dataset_schema_directory = os.environ.get("dataset_schema_directory")
    credentials = os.environ.get("credentials")
    gcp_project = os.environ.get("gcp_project")

    updated_files = os.environ.get("updated_files")
    execute_only_changed_files = os.environ.get("execute_only_changed_files", "true")

    try:
        bq = BigQuery(credentials, gcp_project)
        if _str2bool(execute_only_changed_files):
            deploy_failed = _deploy_changes_files(
                bq, gcp_project, updated_files.split(",")
            )
        else:
            deploy_failed = _deploy_from_directory(
                bq, gcp_project, dataset_schema_directory
            )
    except Exception:
        deploy_failed = True

    if deploy_failed:
        raise DeployFailed


def _deploy_changes_files(bq: BigQuery, gcp_project: str, updated_files: List[str]):
    deploy_failed = False
    for file in updated_files:
        dataset = file.split("/")[-2]
        structure_id = file.split("/").pop()
        with open(file, "r") as contents:
            try:
                file_name_and_extension = structure_id.split(".")
                if file_name_and_extension[1] == "sql":
                    _deploy_sql_script(
                        bq=bq,
                        contents=contents,
                        file_name_and_extension=file_name_and_extension,
                    )
                else:
                    _deploy_json_structure(
                        bq=bq,
                        contents=contents,
                        dataset=dataset,
                        file_name_and_extension=file_name_and_extension,
                        gcp_project=gcp_project,
                    )
            except Exception as e:
                print(f"Failed to deploy to Bigquery: {str(e)}")
                deploy_failed = True

    return deploy_failed


def _deploy_from_directory(bq: BigQuery, gcp_project: str, root_folder_path: str):
    deploy_failed = False
    for root, dirs, files in os.walk(root_folder_path):
        dataset = root.split("/").pop()
        for file in files:
            with open(f"{root}/{file}", "r") as contents:
                try:
                    file_name_and_extension = file.split(".")
                    if file_name_and_extension[1] == "sql":
                        _deploy_sql_script(
                            bq=bq,
                            contents=contents,
                            file_name_and_extension=file_name_and_extension,
                        )
                    else:
                        _deploy_json_structure(
                            bq=bq,
                            contents=contents,
                            dataset=dataset,
                            file_name_and_extension=file_name_and_extension,
                            gcp_project=gcp_project,
                        )
                except Exception as e:
                    print(f"Failed to deploy to Bigquery: {str(e)}")
                    deploy_failed = True

    return deploy_failed


def _deploy_json_structure(
    bq: BigQuery,
    contents: TextIO,
    dataset: str,
    file_name_and_extension: List[str],
    gcp_project: str,
):
    print(f"Updating schema for {gcp_project}.{dataset}.{file_name_and_extension[0]}")
    schema = json.loads(contents.read())
    bq.create_or_update_structure(
        project=gcp_project,
        dataset=dataset,
        structure_id=file_name_and_extension[0],
        json_schema=schema,
    )


def _deploy_sql_script(
    bq: BigQuery, contents: TextIO, file_name_and_extension: List[str]
):
    print(f"Executing file {file_name_and_extension[0]}.{file_name_and_extension[1]}")
    query = contents.read()
    bq.execute(query=query)


def _str2bool(value: str):
    return value.lower() in ("yes", "true", "t", "1")


def main():
    _validate_env_variables()
    if _validate_if_path_exists():
        _deploy()
    else:
        raise DatasetSchemaDirectoryNonExistent
