# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `include` and `exclude` options (arrays of globs, relative to `dataset_schema_directory`) to
  choose which files are deployed, for example one dataset or everything except SQL scripts.
  `exclude` wins; both apply before `execute_only_changed_files`. Without them every file is
  considered, as before.

### Added

- `annotate` option: adds a Buildkite annotation with a per-file table (target, result, time,
  error), created from the agent after the run, as an error annotation when the deployment
  fails. `annotation_context` (default `bigquery`) separates annotations of several steps.
  Error text and file names are HTML-escaped, and a failure to annotate never changes the
  step's result.
- A per-file summary (`N deployed, M failed` and each failed file with its error) is now
  logged at the end of every deployment.

### Changed

- The deploy container is no longer started with `--rm`; the hook removes it on exit, so the
  summary can be copied out of it.

## [3.0.0] - 2026-10-18

### Changed

- **Default deploy image is now `python:3.15-slim`** (was `python:3.14-slim`). The locked
  dependencies install and import on 3.15 (tested); set `custom_image: python:3.14-slim` to keep
  the old image.
- Updated GitHub Actions: `actions/checkout` v7.0.1, `actions/stale` v11.0.0,
  `actions/upload-artifact` v7.0.2, `astral-sh/setup-uv` v10.3.0 (all pinned by SHA).
- shfmt v3.14.1 built with Go 1.27; `uv.lock` re-resolved (already at the latest versions).

### Security

- **Fixed command injection through changed file names.** The list of changed files was
  interpolated into the shell command run inside the container, so a pull request adding a
  file such as `schemas/ds/x$(cmd).json` would run `cmd` in a container that holds the
  service account key. The list is now passed as an environment variable, newline-separated
  (it was comma-separated, so names containing a comma were also split).
- The service account key is no longer written to a temporary file or put on the
  `docker create` command line, where it was visible in `docker inspect`; it is passed to
  Docker by variable name only.
- **BREAKING (behaviour):** The container no longer receives the whole job environment
  (`BUILDKITE_ENV_FILE`), `BUILDKITE_AGENT_ACCESS_TOKEN`, `BUILDKITE_JOB_ID`,
  `BUILDKITE_BUILD_ID`, or the mounted `buildkite-agent` binary. It gets the plugin
  settings, the service account, and `HTTP(S)_PROXY`/`NO_PROXY` when set. Pipelines that
  relied on other variables inside a `custom_image` run need them added explicitly.
- `plugin_scripts/requirements.lock` now contains only runtime dependencies, with hashes,
  and is installed with `--require-hashes`. This clears all known advisories (urllib3,
  pyasn1, requests, protobuf, idna and others) and removes pytest, mypy, ruff and pip from
  the deploy container. `uv` is pinned to 0.13.1 instead of installing the latest.

### Fixed

- `fail_pipeline_on_first_exception` was ignored (the hook read a misnamed variable), so
  deployments always stopped at the first failure. The option is now honoured.
- `execute_only_changed_files: true` deployed nothing and still succeeded: the hook sent
  absolute host paths that never matched the relative paths the container compares. Paths
  are now relative to the checkout and compared after resolving, so `./x`, `x` and absolute
  forms match. When no file changed the log says so.
- The documented default of `execute_only_changed_files` was `true`, but the hook has always
  used `false`. The docs now say `false`; behaviour is unchanged.
- Git failures while detecting changed files were swallowed and led to deploying nothing.
  The step now fails with an error. On feature branches the base branch is fetched when
  missing (shallow clones) before falling back to the last commit, and a first commit
  deploys all files.
- A failed `docker pull` made the hook exit 0; it now exits with the pull's status. The
  retry count is read from `BUILDKITE_PLUGIN_BIGQUERY_DOCKER_PULL_RETRIES` (it was named
  after another plugin).
- The created container is removed if copying the checkout into it fails.
- Files are deployed in sorted path order instead of filesystem order.
- Booleans accept `true`, `on`, `yes` and `1` consistently.
- The `shfmt` lint job failed because the Dockerfile installed `shfmt@latest`, which now
  needs a newer Go than the image provides. shfmt is pinned to v3.12.0.

### Changed

- CI: workflows run with read-only `contents` permission (the repository default token was
  write), checkouts no longer persist credentials, and the action version comments now match
  the pinned SHAs (Dependabot had bumped SHAs and left stale `# v4`/`# v5` comments).
- CI: the `Unit Tests` workflow runs the whole `tests/` directory, not only `test_deploy.py`.
- `buildkite/plugin-tester` and `buildkite/plugin-linter` images are pinned to release tags.
- The container no longer allocates a TTY (`-it`), so build logs no longer contain `\r\n` line endings.

### Changed - BREAKING (gbq 2.0)

- Upgraded [gbq](https://github.com/wayfair-incubator/gbq) from 1.1.0 to 2.0.0. What it means
  for your schema files and pipelines (see the README's "Upgrading to 3.0.0"):
  - Updating an existing table or view treats the JSON file as the source of truth: labels,
    description and clustering omitted from the file are **removed**.
  - An existing table whose partitioning differs from the file now fails the deployment with
    `InvalidDefinitionException` (a changed time-partition expiration is applied).
  - Invalid definitions raise `InvalidDefinitionException` instead of `KeyError`.
  - An unchanged table or view no longer triggers an update call, and updates send only the
    changed fields.
  - Stored procedure arguments can be `ARRAY<...>`/`STRUCT<...>` (full types), and column
    attributes such as policy tags, precision and default values are preserved on update.
  - SQL files still run in `gcp_project`.

### Added

- **Application Default Credentials:** `gcp_service_account` is now optional. Without it the
  plugin uses ADC: the agent's cloud identity (metadata server / Workload Identity) or the
  file in `GOOGLE_APPLICATION_CREDENTIALS`, mounted read-only into the container. A key in
  `gcp_service_account` still takes precedence.
- An invalid service account key now fails with a clear message that does not include the key.
- Bats tests for `hooks/command` (run with `docker compose run --rm test`, and in CI).

### Changed - documentation

- README: documents `custom_image` and `debug_mode`, the directory layout (dataset from the
  directory name, JSON vs SQL files, deployment order, the dataset must already exist), a
  fuller pipeline example and troubleshooting; the intro is de-duplicated and recommends pinning
  a release tag.

### Changed - release process

- Releases are created by a workflow. Merging a pull request that turns `## [Unreleased]` in
  `CHANGELOG.md` into `## [X.Y.Z] - date` (and updates the version in `README.md`) tags that
  commit `vX.Y.Z` and publishes a GitHub release with the changelog section as its notes. It uses
  the workflow's own token, needs no secrets, and does nothing if the release exists. See
  CONTRIBUTING.md.
- The `shfmt` CI job now fails on unformatted scripts (it previously rewrote files and always passed)
  and also checks `.github/scripts`.

### Changed - build and Python support

- Dependencies are managed with uv: declared in `pyproject.toml` (`dependencies` and a `dev`
  dependency group) and locked for every supported Python in a universal `uv.lock`.
  `requirements.txt` and `requirements-test.txt` are removed. `plugin_scripts/requirements.lock`
  is now exported from `uv.lock` (hash-pinned, runtime only).
- Python 3.11 to 3.15 are supported and tested in CI (`requires-python >=3.11`; it was
  `>=3.14` although CI tested 3.12-3.14). Python 3.10 is end-of-life and not supported.
  The deploy container still defaults to `python:3.14-slim`.
- CI installs a pinned uv through `astral-sh/setup-uv` instead of `curl | sh`; the devbox image
  copies uv from a digest-pinned `ghcr.io/astral-sh/uv:0.13.1` instead of `:latest`. A new
  CI job fails if `uv.lock` or `requirements.lock` is stale.
- Dependency updates: Dependabot is removed (it duplicated Renovate's pull requests). Renovate now
  uses `config:recommended` and the `pep621`, `dockerfile`, `docker-compose` and `github-actions`
  managers, plus regex managers for the uv, default image and shfmt versions in `hooks/command`
  and `docker/shfmt.dockerfile`. uv updates (docker image, `setup-uv` `version:`, hook) and
  Go/shfmt updates are grouped, and `uv.lock` is refreshed weekly (lock file maintenance).

## [2.0.0] - 2025-11-02

### Changed - BREAKING

- **Python Version**: Upgraded from Python 3.10 to Python 3.14
  - Dropped support for Python 3.7-3.11
  - GitHub Actions now test against Python 3.12, 3.13, and 3.14
- **Package Manager**: Migrated from pip to uv for faster dependency management (10-100x speedup)
- **Linting Tools**: Replaced black, isort, flake8, and bandit with unified Ruff tool (10-100x faster)
- **Configuration**: Consolidated all tool configurations into `pyproject.toml`
  - Removed `.bandit`, `.coveragerc`, `.flake8`, `.isort.cfg`, `mypy.ini`, and `pytest.ini` files
- **Path Handling**: Migrated from string manipulation to `pathlib.Path` for cross-platform compatibility

### Security

- **CRITICAL**: Fixed insecure credential handling in `hooks/command`
  - Replaced predictable `/tmp/service_account.json` with secure `mktemp` creation
  - Added restrictive file permissions (600) to prevent credential leakage
  - Implemented proper cleanup with trap handlers for EXIT, ERR, INT, and TERM signals
  - Eliminated symlink attack vulnerability

### Fixed

- **Critical Bug**: Fixed incorrect file path construction in `_deploy_from_directory`
  - Previously: Used `dataset_schema_directory + filename` (missing subdirectories)
  - Now: Uses proper path joining with `pathlib` to include all subdirectories
- **Bug**: Fixed broken git diff commands in `hooks/command`
  - Replaced invalid `origin~0` reference with proper `HEAD^..HEAD` comparison
  - Fixed feature branch comparison using proper merge-base syntax (`base...HEAD`)
  - Added error handling and fallback strategies
  - Now converts relative paths to absolute paths to match Python code expectations
- **Bug**: Fixed dataset name extraction using `pathlib` instead of fragile string splitting

### Updated

- **gbq**: Updated from 1.0.5 to 1.1.0
- **google-cloud-bigquery**: Updated from 3.4.1 to >=3.28.0
- **pydantic**: Updated from 2.4.2 to >=2.10.0
- **pytest**: Updated from 7.2.0 to >=8.3.0
- **pytest-cov**: Updated from 4.0.0 to >=6.0.0
- **pytest-mock**: Updated from 3.10.0 to >=3.14.0
- **mypy**: Updated from 0.991 to >=1.13.0
- **ruff**: Added >=0.8.0 for unified linting and formatting
- All GitHub Actions updated to latest versions (v4/v5)
- Docker base image changed to `python:3.14-slim`
- `hooks/command`: Updated default image to `python:3.14-slim`
- `plugin.yml`: Added descriptions, requirements (bash, docker, git), and debug_mode documentation

### Added

- **Logging**: Comprehensive logging throughout deployment process
  - Deployment start/end status with project information
  - File-by-file processing logs
  - Success/failure messages for each operation
  - Detailed error messages with stack traces (removed `sys.tracebacklimit = 0`)
- **Error Handling**: Custom exceptions for better error semantics
  - Added `MissingConfigError` for configuration validation
  - Specific error handling for `json.JSONDecodeError` and `FileNotFoundError`
  - Proper error chaining with `raise ... from e` for debugging
- **Testing**: 7 new integration tests with real file I/O
  - Test deployment with real files
  - Test file filtering based on changes
  - Test skipping non-schema files
  - Test invalid JSON handling
  - Test fail-fast vs continue-on-error modes
  - Test correct parameter passing to BigQuery
  - Total test count: 13 → 20 tests
  - Coverage increased from 63% to 88% with branch coverage enabled
- **Configuration**: Comprehensive `pyproject.toml` with Ruff, MyPy, Pytest, and Coverage settings
  - Enabled branch coverage for more thorough testing
  - Centralized all tool configurations
- **Documentation**: Added detailed docstrings to all functions
- **Docker Compose**: New services: `ruff-format`, `ruff-lint`, `ruff-check`, `mypy`
- **Git Detection**: Enhanced file change detection with better logging
  - Shows detected file count
  - Provides clear warnings for edge cases
  - Handles first commit scenario

### Removed

- black, isort, flake8, bandit dependencies (replaced by Ruff)
- Configuration files: `.bandit`, `.coveragerc`, `.flake8`, `.isort.cfg`, `mypy.ini`, `pytest.ini` (moved to pyproject.toml)
- `sys.tracebacklimit = 0` - stack traces are now visible for debugging

### Development

- `plugin_scripts/deploy.py`: Complete rewrite with logging, pathlib, and better error handling
- `plugin_scripts/pipeline_exceptions.py`: Added `MissingConfigError` exception
- `hooks/command`: Secure credential handling and fixed git diff logic
- `docker/run_tests.sh`: Simplified to use Ruff commands instead of 4 separate linters
- `docker/lock_requirements.sh`: Updated to use uv commands for faster dependency locking
- GitHub Actions workflows: Streamlined linting jobs into single Ruff job
- Install dependencies action: Updated to use uv instead of pip
- Test coverage: Now includes branch coverage for more thorough analysis

## [1.2.2] - 2024-08-22

### Updated 

- Updating requirements

## [1.2.1] - 2024-08-02

### Updated 

- Updated gbq library dependency to 1.0.5

## [1.2.0] - 2023-02-18

### Added

- Option to specify `fail_pipeline_on_first_exception`, default to `true`

## [1.1.0] - 2023-02-02

### Added

- Option to specify `prod_build_branch`

### Updated

- Logic to only execute changed files for default branches

## [1.0.0] - 2022-09-24

### Added

- Option to only execute changed files
- Option to execute DML statements

## [0.5.0] - 2022-04-11

### Updated

- Update dependencies

## [0.4.0] - 2021-12-16

### Updated

- Docker image for pipeline
- Use locked dependencies for pipeline

## [0.3.0] - 2021-12-05

### Added

- Fail pipeline if deploy fails for at least one schema

## [0.2.1] - 2021-11-28

### Added

- Inline Docker

## [0.2.0] - 2021-09-12

### Added

- Inline Docker

## [0.1.0] - 2021-07-14

### Added

- Initial Release
