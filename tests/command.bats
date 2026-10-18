#!/usr/bin/env bats

# Tests for hooks/command. `docker` is replaced by a stub that records its
# arguments, so nothing is pulled or run. Only needs bats-core and git.

setup() {
  TEST_DIR="$(mktemp -d)"
  HOOK="${BATS_TEST_DIRNAME}/../hooks/command"
  STUB_BIN="${TEST_DIR}/bin"
  export DOCKER_LOG="${TEST_DIR}/docker.log"
  mkdir -p "${STUB_BIN}" "${TEST_DIR}/repo"

  cat >"${STUB_BIN}/docker" <<'STUB'
#!/bin/bash
printf '%s\n' "$1" >>"${DOCKER_LOG}"
if [ "$1" = create ]; then
  # one argument per line, plus whether the credentials env var was visible
  printf '%s\n' "$@" >"${DOCKER_LOG}.create"
  printf 'credentials_in_env=%s\n' "${credentials:-}" >"${DOCKER_LOG}.env"
  echo fakecontainer
fi
STUB
  chmod +x "${STUB_BIN}/docker"

  cd "${TEST_DIR}/repo"
  git init -q .
  git symbolic-ref HEAD refs/heads/main
  git config user.email test@example.com
  git config user.name test
  mkdir -p schemas/ds
  echo '{"schema": []}' >schemas/ds/a.json
  git add -A && git commit -qm init

  export PATH="${STUB_BIN}:${PATH}"
  export BUILDKITE_PLUGIN_BIGQUERY_GCP_PROJECT="my-project"
  export BUILDKITE_PLUGIN_BIGQUERY_DATASET_SCHEMA_DIRECTORY="schemas"
  export BUILDKITE_PLUGIN_BIGQUERY_PROD_BUILD_BRANCH="main"
  export BUILDKITE_BRANCH="main"
  export gcp_service_account='{"private_key": "TOP-SECRET-KEY"}'
}

teardown() {
  cd /
  rm -rf "${TEST_DIR}"
}

@test "service account key never appears in the docker create arguments" {
  run "${HOOK}"
  [ "$status" -eq 0 ]
  ! grep -q "TOP-SECRET-KEY" "${DOCKER_LOG}.create"
  grep -qx -- "credentials" "${DOCKER_LOG}.create"
  grep -q "TOP-SECRET-KEY" "${DOCKER_LOG}.env"
}

@test "changed file names cannot inject shell commands" {
  git checkout -q -b evil
  echo '{}' >'schemas/ds/x$(touch PWNED).json'
  git add -A && git commit -qm evil
  export BUILDKITE_BRANCH=evil
  export BUILDKITE_PLUGIN_BIGQUERY_EXECUTE_ONLY_CHANGED_FILES=true

  run "${HOOK}"
  [ "$status" -eq 0 ]

  # The file name is only ever data in an updated_files= env value ...
  grep -q '^updated_files=.*x\$(touch PWNED)\.json' "${DOCKER_LOG}.create"
  # ... and never part of the command string that sh executes.
  command_string="$(grep -- 'pip install' "${DOCKER_LOG}.create")"
  [[ $command_string != *PWNED* ]]
}

@test "other pipeline variables are not forwarded to the container" {
  export SOME_OTHER_SECRET="hunter2"
  export BUILDKITE_AGENT_ACCESS_TOKEN="agent-token"
  run "${HOOK}"
  [ "$status" -eq 0 ]
  ! grep -q "SOME_OTHER_SECRET\|BUILDKITE_AGENT_ACCESS_TOKEN\|hunter2\|agent-token" "${DOCKER_LOG}.create"
  grep -qx "gcp_project=my-project" "${DOCKER_LOG}.create"
  grep -qx "dataset_schema_directory=schemas" "${DOCKER_LOG}.create"
}

@test "proxy settings are forwarded when set" {
  export HTTPS_PROXY="http://proxy.example:3128"
  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -qx "HTTPS_PROXY" "${DOCKER_LOG}.create"
  ! grep -q "proxy.example" "${DOCKER_LOG}.create"
}

@test "runtime dependencies are installed from the hash-pinned lockfile with a pinned uv" {
  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -Eq 'pip install --quiet uv==[0-9]+\.[0-9]+\.[0-9]+ ' "${DOCKER_LOG}.create"
  grep -q -- '--require-hashes' "${DOCKER_LOG}.create"
}

@test "fails with a clear message when the service account is missing" {
  unset gcp_service_account
  run "${HOOK}"
  [ "$status" -eq 1 ]
  [[ $output == *"gcp service account (gcp_service_account) not set"* ]]
}
