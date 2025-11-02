# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
