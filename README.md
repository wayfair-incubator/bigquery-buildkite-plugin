[![Actions Status](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/workflows/Lint/badge.svg?branch=main)](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/actions)
[![Actions Status](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/workflows/Unit%20Tests/badge.svg?branch=main)](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/actions)
![Version](https://img.shields.io/static/v1.svg?label=Version&message=3.1.0&color=lightgrey&?link=http://left&link=https://github.com/wayfair-incubator/bigquery-buildkite-plugin/tree/v3.1.0)
![Plugin Status](https://img.shields.io/static/v1.svg?label=&message=Buildkite%20Plugin&color=blue&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAMAAADVRocKAAAAk1BMVEX///+DrRik1Cb+/vyErhin1yeAqhfJ5n+dzCO50X2VwiC2zna020vg8LSo1i+q1zTN3qL7/fav2UDT4q33++yXuj3z+eLO6IqMuByJsSPM54XX5bWcvUbH5Xrg6sWiwVHB1ovk7cymxFnq8deOtC2xzG7c6L6/1YfU7JbI2pj2+e+jzzPd763K3J3j8ryRtDbY7aOqCe3pAAACTElEQVRoge3Z11KDQBSAYUpItSRqVGwxEVOwxPd/OndhCbA5BTaLM87sueb83+yMStHz3Lhx48bN/5iw+2VjImy0fDvzQiNCLKVrdjn0nq++QwNCLMy+9uOzc2Y59AZBwF4F55NefxxxyxK4aEvI/C7x/QxglrMTBNxVej6V+QNALh+AhkRY5isAsVwBxFWfM/rnLsu/qnwNQIkawBBy/abMawBCaEAQXGFElt/Evo8CIHEEIESWH9XyAAAQACCIH40A8yBwRICARiB5BNAIBKgQ8tLbCZBHgRqBAgWB5wmgQhCAIt7ekTwJ5AQHSGKC1TkgiM7WIs8A0bBvCETR8H7CA4EhIPP9fgPA7AR53u91BBR53+8EKPPdACLvq3wXQC1vH9DytoGjvF0gGo71vE0gCoC8PQDJ2wJEvgfmbQFo3g5A5HNA3K+eL0yBePdO5AtAEAOUoIB4c+ONiHwBZHddjMCB5DUV6yOqfzgBQWCAzMu9ZoAiHgACBpJdmj3SNAdQAgKSXfFQ1gZQz28PlxxQ5tsCIKED+6/qU2tbQBF3lxgwn9YfitsDR0QVmE9D7bHeBNCIEphf63lToEYUAJQ3BxSxlUQGPD3Cr5DmwIGQJ8DypwHqlXX7gec5oMcAXv5OT31OYU6weuM/9tDv/iSwWnJxfghA5s0+QzUCFi828iiwWNvJI4C9PAg8WcwDAPVLYwGwndeAufV8DZB/bm3nK0A3+RyI81tdF3l1gn1neQlM4qnpp+9ms0xP/P8AP/8778aNGzdu/mh+AQp1NCB/JInXAAAAAElFTkSuQmCC)


# BigQuery Buildkite Plugin

A [Buildkite plugin](https://buildkite.com/docs/agent/v3/plugins) that deploys BigQuery tables, views and stored procedures from JSON definition files, and runs SQL files, using [gbq](https://github.com/wayfair-incubator/gbq).

## Using the plugin

Pin a released version tag (`#vX.Y.Z`, see the [releases](https://github.com/wayfair-incubator/bigquery-buildkite-plugin/releases) and the [changelog](CHANGELOG.md)). Do not use a branch name such as `master` or `main`, so that a new release cannot change your pipeline unexpectedly.

The agent needs `bash`, `docker` and `git`. The deployment runs in a Docker container, with your checkout copied in.

### Simple

```yaml
steps:
  - plugins:
      - wayfair-incubator/bigquery#v3.1.0:
          gcp_project: gcp-us-project
          dataset_schema_directory: schemas/gcp-us-project/dataset
```

## Configuration

### Required

### `gcp_project` (required, string)

The full name of the GCP project you want to deploy.

Example: `gcp-us-project`

### `dataset_schema_directory` (required, string)

The directory in your repository that holds your definition files, relative to the checkout. See [Directory layout](#directory-layout).

Example: `schemas/gcp-us-project`

### `prod_build_branch` (optional, string)

Default branch for the repo.

Example: `main`

Default: `master`

### `execute_only_changed_files` (optional, boolean)

Whether to deploy just the files that changed instead of every file in the directory. On `prod_build_branch` the files changed in the last commit are deployed; on other branches, the files changed compared with `origin/<prod_build_branch>`. If nothing changed, nothing is deployed. If git cannot compare (for example a first commit), all files are deployed; if git fails, the step fails.

Example: `true`

Default: `false`

### `fail_pipeline_on_first_exception` (optional, boolean)

Whether to stop at the first file that fails to deploy. If `false`, the remaining files are still deployed and the step fails at the end.

Example: `false`

Default: `true`

### `custom_image` (optional, string)

The Docker image the deployment runs in. It must provide Python 3.11 or newer and `pip`; the plugin installs its locked dependencies into it on every run.

Example: `python:3.13-slim`

Default: `python:3.15-slim`

### `mode` (optional, string)

- `apply` (default): deploy.
- `plan`: show what `apply` would do and **change nothing**. Every JSON definition is run through the same gbq code that `apply` uses, against your real BigQuery state, but its writes are recorded instead of sent, and any other request that could change something is refused. Each file is reported as *would create*, *would update* (with the changed fields, for example `removes label team; adds column name`), *unchanged*, or *failed* when `apply` would fail (for example a partitioning change, or an invalid definition). SQL files are checked with a BigQuery [dry run](https://cloud.google.com/bigquery/docs/dry-run-queries) (syntax, referenced tables and bytes it would scan) and are never executed. Any failed file fails the step. `plan` needs credentials with read access only: `bigquery.tables.get`, `bigquery.routines.get` and `bigquery.jobs.create` (for the dry run).
- `validate`: check that every definition parses, with gbq's own parser, and that SQL files are not empty. It works offline and uses **no credentials**, so it can run in steps that have none.

A plan shows what the deployment would write; BigQuery can still reject a write when applying (permissions, quotas), and a dry run does not prove that DML would succeed against the data. Use `annotate: true` to get the plan as a table on the build.

Example, a plan on pull requests and a real deployment on `main`:

```yaml
steps:
  - label: ":bigquery: Plan"
    if: build.branch != "main"
    plugins:
      - wayfair-incubator/bigquery#v3.1.0:
          gcp_project: gcp-us-project
          dataset_schema_directory: schemas/gcp-us-project
          mode: plan
          annotate: true
  - label: ":bigquery: Deploy"
    if: build.branch == "main"
    plugins:
      - wayfair-incubator/bigquery#v3.1.0:
          gcp_project: gcp-us-project
          dataset_schema_directory: schemas/gcp-us-project
          prod_build_branch: main
          execute_only_changed_files: true
```

Default: `apply`

### `include` (optional, array of strings)

Only deploy files whose path matches one of these globs. Paths are relative to `dataset_schema_directory` and use `/`. `*` and `?` match within one directory, `**` matches across directories (`**/a.json` also matches `a.json` at the top). Without `include`, all `*.json` and `*.sql` files are considered.

Example:

```yaml
include:
  - "sales/**"
  - "ops/*.json"
```

### `exclude` (optional, array of strings)

Skip files that match any of these globs (same syntax). `exclude` wins over `include`.

Example: `["**/*.sql", "**/drafts/**"]`

Both options apply before `execute_only_changed_files`: a file is deployed only if it is selected here and, when that option is on, changed. If `include` matches no file, the log says so.

### `annotate` (optional, boolean)

Add a [Buildkite annotation](https://buildkite.com/docs/agent/v3/cli-annotate) with a table of every file that was processed: its target (`project.dataset.structure`, or SQL), whether it deployed or failed, how long it took and the error. The annotation is created by the agent after the deployment, also when it fails (as an error annotation), and the container never receives the agent or its token. A problem creating the annotation never changes the result of the step. The same per-file summary (counts and failures) is always printed at the end of the build log, with or without this option.

Example: `true`

Default: `false`

### `annotation_context` (optional, string)

The annotation's context. Use a different one per deployment step so the annotations do not replace each other.

Example: `bigquery-eu`

Default: `bigquery`

### `debug_mode` (optional, boolean)

Print the resolved configuration, the changed files and the Docker command (never the credentials).

Example: `true`

Default: `false`

## Directory layout

Every `*.json` and `*.sql` file under `dataset_schema_directory` is deployed, in sorted path order. Other files are ignored.

```text
schemas/gcp-us-project/
  sales/                 <- directory name = BigQuery dataset
    orders.json          <- table, view or routine definition: sales.orders
    orders_by_day.json
    backfill.sql         <- SQL statement or script, run in gcp_project
```

- **JSON files** define a table, view or stored procedure ([format](https://github.com/wayfair-incubator/gbq)). The dataset is the name of the directory the file is in and the structure id is the file name without `.json`, so `sales/orders.json` deploys `<gcp_project>.sales.orders`. The dataset must already exist. A file in a nested directory deploys into the dataset named after that nested directory.
- **SQL files** are executed as written (DDL, DML or a script) in `gcp_project`. The file name is only used in logs. They are not parameterised, so use them for statements that are safe to run on every deploy, or combine them with `execute_only_changed_files`.
- Because files run in path order and one at a time, put definitions that depend on each other in names that sort correctly, or deploy them in separate steps.

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

### Deploy on the default branch, preview changes on pull requests

```yaml
steps:
  - label: ":bigquery: Deploy BigQuery"
    plugins:
      - wayfair-incubator/bigquery#v3.1.0:
          gcp_project: gcp-us-project
          dataset_schema_directory: schemas/gcp-us-project
          prod_build_branch: main
          execute_only_changed_files: true
```

On `main` this deploys the files changed by the last commit; on other branches it deploys the files changed compared with `origin/main`. Keep `fail_pipeline_on_first_exception` at its default so a broken definition stops the build.

### Troubleshooting

- **Nothing was deployed:** with `execute_only_changed_files: true` the log says `No changed files detected`. Check that your files are under `dataset_schema_directory` and that the build checked out enough history (the plugin fetches `origin/<prod_build_branch>` when it is missing).
- **`InvalidDefinitionException`:** the JSON file is not a valid definition, or a table's partitioning differs from the deployed one (partitioning cannot be changed in place).
- **Authentication errors:** see [Credentials](#credentials).

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

The project uses [uv](https://docs.astral.sh/uv/) for dependency management and `ruff` for linting/formatting. Dependencies are declared in `pyproject.toml` (runtime in `dependencies`, tools in the `dev` group) and locked in `uv.lock`; `plugin_scripts/requirements.lock` is the hash-pinned runtime subset that the plugin installs inside the deploy container. CI checks that both are up to date. The code supports Python 3.11 to 3.15; the plugin itself runs in `python:3.15-slim` unless you set `custom_image` (it needs Python 3.11 or newer with `pip`).

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
