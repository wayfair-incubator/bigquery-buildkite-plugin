import os
import sys
import json
from json import JSONDecodeError

from gbq import BigQuery

sys.tracebacklimit = 0

dataset_schema_directory = os.environ.get('dataset_schema_directory')
credentials = os.environ.get('GCP_SERVICE_ACCOUNT')
project = os.environ.get("gcp_project")

if not project:
    raise Exception('Missing `gcp_project` config')

if not dataset_schema_directory:
    raise Exception('Missing `dataset_schema_directory` config')

if not credentials:
    raise Exception('Missing `GCP_SERVICE_ACCOUNT` config')

def _lint_and_validate():
    files_with_errors = []
    for root_directory, directory, directory_contents in os.walk(dataset_schema_directory):
        for f in directory_contents:
            with open(f'{root_directory}/{f}', "r") as content:
                file_name_and_ext = f.split('.')
                if file_name_and_ext[1] == 'json':
                    try:
                        json.loads(content.read())
                    except JSONDecodeError:
                        files_with_errors.append(f"{root_directory}/{f}")
    return files_with_errors


errors = _lint_and_validate()


if errors:
    print('JSON validation failed for following files:')
    for error in errors:
        print(f'- {error}')
    raise Exception('Execution cannot continue until the above files are fixed')


try:
    bq = BigQuery(credentials, project)
    for root, dirs, files in os.walk(dataset_schema_directory):
        dataset = root.split('/').pop()
        for file in files:
            with open(f'{root}/{file}', "r") as contents:
                file_name_and_extension = file.split('.')
                print(f'Updating schema for {project}.{dataset}.{file_name_and_extension[0]}')
                if file_name_and_extension[1] == 'sql':
                    schema = contents.read()
                    bq.create_or_update_view(
                        project, dataset, file_name_and_extension[0], schema
                    )
                else:
                    schema = json.loads(contents.read())
                    bq.create_or_update_structure(
                        project, dataset, file_name_and_extension[0], schema
                    )
except Exception as e:
    print(f'Failed to deploy to Bigquery: {e}')
