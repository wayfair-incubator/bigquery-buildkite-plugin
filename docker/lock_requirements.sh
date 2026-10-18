#!/usr/bin/env bash
set -euo pipefail

# Compile the runtime requirements into a hash-pinned lockfile. Only runtime
# dependencies are locked; test tooling lives in requirements-test.txt.
# Pass --upgrade to refresh every pin to the latest release.
uv pip compile requirements.txt \
	--python-version 3.14 \
	--generate-hashes \
	--no-header \
	--output-file plugin_scripts/requirements.lock \
	"$@"

echo "Rebuild containers to verify there are no conflicts."
