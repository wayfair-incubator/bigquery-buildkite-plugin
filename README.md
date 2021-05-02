[![CI pipeline status](https://github.com/wayfair-incubator/gbq/workflows/CI/badge.svg?branch=main)][ci]
[![PyPI](https://img.shields.io/pypi/v/gbq)][pypi]
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/gbq)][pypi]
[![codecov](https://codecov.io/gh/wayfair-incubator/gbq/branch/main/graph/badge.svg)][codecov]
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue)][mypy-home]
[![Code style: black](https://img.shields.io/badge/code%20style-black-black.svg)][black-home]


# BigQuery Buildkite Plugin

This Buildkite plugin can be used to deploy tables/views schemas to BigQuery

A [Buildkite plugin](https://buildkite.com/docs/agent/v3/plugins) for deploying tables/views schemas to BigQuery.

## Using the plugin

If the version number is not provided then the most recent version of the plugin will be used. Do not use version number as `master` or any branch names.

### Simple

```yaml
steps:
  - plugins:
      - wayfair-incubator/bigquery#v0.1.1:
          gcp_project: gcp-us-project
          dataset_schema_directory: schemas/gcp-us-project/dataset
          gcp_service_account: credentials
            - BUILDKITE_BUILD_NUMBER
```

## Configuration

### Required

### `gcp_project` (required, string)

The full name of the GCP project you want to deploy.

Example: `gcp-us-project`

### `dataset_schema_directory` (required, string)

The directory in your repository where are you storing the schemas for your tables and views.

Example: `wf-gcp-us-ae-buyfair/buyfair`

### `plugin_image_version` (optional, string)

**ONLY to be used when testing feature branch changes to this plugin from another pipeline**

The full hash for the latest commit to your feature branch for this plugin. This should match the plugin 'version' you are referencing in your test pipeline.

Example: `1e602649cebf27b16dc45177ef1552b068fd2f8e`


## Example

### Basic

The following pipeline will deploy all the schemas to the `gcp-us-project` living under `directory/project/`

## Schemas

This plugin uses [GBQ](https://github.com/wayfair-incubator/gbq) underneath to deploy to Google BigQuery.
[GBQ](https://github.com/wayfair-incubator/gbq) now supports specifying partitions with the schema as well.

To leverage this you need to nest your JSON table schema in a dictionary. An example for the same is given below. Library supports Time and Range based partitioning along with Clustering.

All the configuration options can be found [here](https://github.csnzoo.com/shared/buyfair-bigquery-library/blob/master/buyfair_bigquery_library/dto.py).

```json
{
  "partition": {
    "type": "range",
    "definition": {
      "field": "ID",
      "range": {
        "start": 1,
        "end": 100000,
        "interval": 10
      }
    }
  },
  "clustering": [
    "ID"
  ],
  "schema": [
    {
      "name": "ID",
      "type": "INTEGER",
      "mode": "REQUIRED"
    }
  ]
}
```

## Documentation

Check out the [project documentation](https://wayfair-incubator.github.io/gbq/)

[ci]: https://github.com/wayfair-incubator/gbq/actions
[codecov]: https://codecov.io/gh/wayfair-incubator/gbq
[mypy-home]: http://mypy-lang.org/
[black-home]: https://github.com/psf/black
[install-docker]: https://docs.docker.com/install/
[pdbpp-home]: https://github.com/pdbpp/pdbpp
[pdb-docs]: https://docs.python.org/3/library/pdb.html
[pdbpp-docs]: https://github.com/pdbpp/pdbpp#usage
[pytest-docs]: https://docs.pytest.org/en/latest/
[mypy-docs]: https://mypy.readthedocs.io/en/stable/
[black-docs]: https://black.readthedocs.io/en/stable/
[isort-docs]: https://pycqa.github.io/isort/
[flake8-docs]: http://flake8.pycqa.org/en/stable/
[bandit-docs]: https://bandit.readthedocs.io/en/stable/
[sem-ver]: https://semver.org/
[pypi]: https://semver.org/
[gbq-docs]: https://wayfair-incubator.github.io/gbq/
