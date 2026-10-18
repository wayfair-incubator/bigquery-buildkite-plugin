[![Actions Status](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/workflows/Lint/badge.svg?branch=main)](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/actions)
[![Actions Status](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/workflows/Unit%20Tests/badge.svg?branch=main)](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/actions)
![Version](https://img.shields.io/static/v1.svg?label=Version&message=1.2.2&color=lightgrey&?link=http://left&link=https://github.com/wayfair-incubator/bigquery-buildkite-plugin/tree/v1.2.2)
![Plugin Status](https://img.shields.io/static/v1.svg?label=&message=Buildkite%20Plugin&color=blue&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAMAAADVRocKAAAAk1BMVEX///+DrRik1Cb+/vyErhin1yeAqhfJ5n+dzCO50X2VwiC2zna020vg8LSo1i+q1zTN3qL7/fav2UDT4q33++yXuj3z+eLO6IqMuByJsSPM54XX5bWcvUbH5Xrg6sWiwVHB1ovk7cymxFnq8deOtC2xzG7c6L6/1YfU7JbI2pj2+e+jzzPd763K3J3j8ryRtDbY7aOqCe3pAAACTElEQVRoge3Z11KDQBSAYUpItSRqVGwxEVOwxPd/OndhCbA5BTaLM87sueb83+yMStHz3Lhx48bN/5iw+2VjImy0fDvzQiNCLKVrdjn0nq++QwNCLMy+9uOzc2Y59AZBwF4F55NefxxxyxK4aEvI/C7x/QxglrMTBNxVej6V+QNALh+AhkRY5isAsVwBxFWfM/rnLsu/qnwNQIkawBBy/abMawBCaEAQXGFElt/Evo8CIHEEIESWH9XyAAAQACCIH40A8yBwRICARiB5BNAIBKgQ8tLbCZBHgRqBAgWB5wmgQhCAIt7ekTwJ5AQHSGKC1TkgiM7WIs8A0bBvCETR8H7CA4EhIPP9fgPA7AR53u91BBR53+8EKPPdACLvq3wXQC1vH9DytoGjvF0gGo71vE0gCoC8PQDJ2wJEvgfmbQFo3g5A5HNA3K+eL0yBePdO5AtAEAOUoIB4c+ONiHwBZHddjMCB5DUV6yOqfzgBQWCAzMu9ZoAiHgACBpJdmj3SNAdQAgKSXfFQ1gZQz28PlxxQ5tsCIKED+6/qU2tbQBF3lxgwn9YfitsDR0QVmE9D7bHeBNCIEphf63lToEYUAJQ3BxSxlUQGPD3Cr5DmwIGQJ8DypwHqlXX7gec5oMcAXv5OT31OYU6weuM/9tDv/iSwWnJxfghA5s0+QzUCFi828iiwWNvJI4C9PAg8WcwDAPVLYwGwndeAufV8DZB/bm3nK0A3+RyI81tdF3l1gn1neQlM4qnpp+9ms0xP/P8AP/8778aNGzdu/mh+AQp1NCB/JInXAAAAAElFTkSuQmCC)


# BigQuery Buildkite Plugin

This Buildkite plugin can be used to deploy tables/views schemas to BigQuery

A [Buildkite plugin](https://buildkite.com/docs/agent/v3/plugins) for deploying tables/views schemas to BigQuery.

## Using the plugin

If the version number is not provided then the most recent version of the plugin will be used. Do not use version number as `master` or any branch names.

### Simple

```yaml
steps:
  - plugins:
      - wayfair-incubator/bigquery#v1.2.2:
          gcp_project: gcp-us-project
          dataset_schema_directory: schemas/gcp-us-project/dataset
```

## Configuration

### Required

### `gcp_project` (required, string)

The full name of the GCP project you want to deploy.

Example: `gcp-us-project`

### `dataset_schema_directory` (required, string)

The directory in your repository where are you storing the schemas for your tables and views.

Example: `gcp-us-project/dataset_name`

### `prod_build_branch` (optional, string)

Default branch for the repo.

Example: `main`

Default: `master`

### `execute_only_changed_files` (optional, boolean)

Whether to deploy just the files that changed instead of every file in the directory. On `prod_build_branch` the files changed in the last commit are deployed; on other branches, the files changed compared with `origin/<prod_build_branch>`. If nothing changed, nothing is deployed. If git cannot compare (for example a first commit), all files are deployed; if git fails, the step fails.

Example: `true`

Default: `false`

### `fail_pipeline_on_first_exception` (optional, boolean)

Whether to fail pipeline as soon as there is one failure.

Example: `true`

Default: `true`

## Credentials

The plugin authenticates to BigQuery in one of two ways.

### Service account key

Place the service account key JSON in the `gcp_service_account` environment variable (lowercase). Make sure to store it [securely](https://buildkite.com/docs/pipelines/secrets)!

```yaml
env:
  gcp_service_account: '{"type": "service_account", "project_id": "..."}'
```

An invalid key fails the step with `svc_account is not valid service account JSON`; the key itself is never printed.

### Application Default Credentials

If `gcp_service_account` is **not** set, the plugin uses [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials), so no long-lived key has to be stored in Buildkite:

- **Agent running on Google Cloud** (GCE, GKE with Workload Identity): the container reaches the metadata server and uses the attached service account. Nothing to configure.
- **A credentials file:** set `GOOGLE_APPLICATION_CREDENTIALS` on the agent to a file path (for example a service account impersonation or workload identity federation configuration). The plugin mounts that file read-only into the container. The file must be self-contained: files it references (such as a token file) are not mounted.

The service account (or identity) needs permission to create and update the BigQuery resources you deploy and to run the queries in your `.sql` files.

## Example

### Basic

The following pipeline will deploy all the schemas to the `gcp-us-project` living under `directory/project/`

## Schemas

This plugin uses [GBQ](https://github.com/wayfair-incubator/gbq) to deploy to Google BigQuery.
[GBQ](https://github.com/wayfair-incubator/gbq) now supports specifying partitions with the schema as well.

To leverage this you need to nest your JSON table schema in a dictionary. An example for the same is given below. Library supports Time and Range based partitioning along with Clustering.

All the configuration options can be found [here](https://github.com/wayfair-incubator/gbq/blob/main/gbq/dto.py).

**Updating existing tables and views:** the JSON file is the source of truth. Labels, description and clustering that the file omits are removed from the existing table or view. Partitioning cannot be changed on an existing table (apart from a time partition's expiration): a definition whose partitioning differs fails the deployment with `InvalidDefinitionException`, so recreate the table (or revert the change) instead. Stored procedure arguments may use full types such as `ARRAY<INT64>` and `STRUCT<id INT64, tags ARRAY<STRING>>`.

SQL files run in `gcp_project`.

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

## Upgrading to 3.0.0

Version 3.0.0 upgrades [gbq](https://github.com/wayfair-incubator/gbq) from 1.1.0 to 2.0.0. Before you upgrade, check your schema files and pipelines:

1. **Omitted properties are now removed.** If a table or view already exists and its JSON file has no `labels`, `description` or `clustering`, those are cleared on the next deploy. Add them to the file first if you want to keep them (for example copy them from the console).
2. **Partitioning changes fail.** A deployed table whose partitioning differs from the file (other than a changed time-partition expiration, which is applied) now fails with `InvalidDefinitionException` instead of being silently ignored. Reconcile the file or recreate the table.
3. **Invalid definitions** fail with `InvalidDefinitionException` instead of a `KeyError`; the step fails either way.
4. **Container environment is restricted** (also new in 3.0.0): only the plugin settings, the service account and `HTTP(S)_PROXY`/`NO_PROXY` reach the container.
5. **New:** `gcp_service_account` is optional (see [Credentials](#credentials)).
6. **Unchanged:** `.sql` files still run in `gcp_project`, and tables are not deleted (the plugin never deletes).

Pin `wayfair-incubator/bigquery#v2.0.0` to stay on the old behaviour until you are ready.

## Contributing

See the [Contributing Guide](CONTRIBUTING.md) for additional information.

To execute tests locally (requires that `docker` and `docker-compose` are installed):

```bash
docker-compose run test
```

### Development Commands

The project uses [uv](https://docs.astral.sh/uv/) for dependency management and `ruff` for linting/formatting. Dependencies are declared in `pyproject.toml` (runtime in `dependencies`, tools in the `dev` group) and locked in `uv.lock`; `plugin_scripts/requirements.lock` is the hash-pinned runtime subset that the plugin installs inside the deploy container. CI checks that both are up to date. The code supports Python 3.11 to 3.15; the plugin itself runs in `python:3.14-slim` unless you set `custom_image` (it needs Python 3.11 or newer with `pip`).

To work without Docker:

```bash
uv sync --locked      # create .venv with the locked dev dependencies
uv run pytest
```

```bash
# Run all tests and linting with auto-formatting
docker-compose run --rm py-test

# Run tests only
docker-compose run --rm devbox pytest

# Run ruff format (auto-fix formatting issues)
docker-compose run --rm ruff-format

# Run ruff linting with auto-fix
docker-compose run --rm ruff-lint

# Run ruff check only (no auto-fix)
docker-compose run --rm ruff-check

# Run mypy type checking
docker-compose run --rm mypy

# Refresh uv.lock and the hashed runtime requirements used by the deploy container
# after changing dependencies in pyproject.toml (add `--upgrade` to bump every pin)
docker-compose run --rm lock-requirements
docker-compose build devbox
```

## Credits

This plugin was originally written by [Jash Parekh](https://github.com/jashparekh) for Wayfair.
