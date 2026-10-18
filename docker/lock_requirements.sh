#!/usr/bin/env bash
set -euo pipefail

# Refresh uv.lock (pass --upgrade to move every pin to its latest release), then
# export the runtime dependencies, with hashes, for the deploy container. The hook
# installs plugin_scripts/requirements.lock with `--require-hashes`.
uv lock "$@"
uv export --locked --no-dev --no-emit-project --format requirements-txt --no-header \
	--output-file plugin_scripts/requirements.lock

echo "Rebuild containers to verify there are no conflicts."
