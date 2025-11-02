#!/usr/bin/env bash

set -eo pipefail

RUFF_FIX=""

function usage
{
    echo "usage: run_tests.sh [--format-code]"
    echo ""
    echo " --format-code : Format the code instead of checking formatting."
    exit 1
}

while [[ $# -gt 0 ]]; do
    arg="$1"
    case $arg in
        --format-code)
        RUFF_FIX="--fix"
        ;;
        -h|--help)
        usage
        ;;
        "")
        # ignore
        ;;
        *)
        echo "Unexpected argument: ${arg}"
        usage
        ;;
    esac
    shift
done

# Run tests with coverage (only generate html locally)
pytest --cov plugin_scripts/ tests --cov-report html

echo "Running MyPy..."
mypy plugin_scripts tests

echo "Running Ruff linting..."
ruff check ${RUFF_FIX} plugin_scripts tests

if [ -z "${RUFF_FIX}" ]; then
    echo "Running Ruff format check..."
    ruff format --check plugin_scripts tests
else
    echo "Running Ruff formatter..."
    ruff format plugin_scripts tests
fi

echo "All checks passed!"
