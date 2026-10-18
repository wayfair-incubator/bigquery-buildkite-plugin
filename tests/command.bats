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
case "$1" in
  create)
    # one argument per line, plus whether the credentials env var was visible
    printf '%s\n' "$@" >"${DOCKER_LOG}.create"
    printf 'credentials_in_env=%s\n' "${credentials:-}" >"${DOCKER_LOG}.env"
    echo fakecontainer
    ;;
  cp)
    # copying the annotation out of the container
    if [[ $2 == *:/tmp/bigquery-annotation.md ]]; then
      [ -n "${STUB_NO_ANNOTATION:-}" ] && exit 1
      echo "STUB-ANNOTATION" >"$3"
    fi
    ;;
  start)
    exit "${STUB_START_RC:-0}"
    ;;
esac
STUB
  chmod +x "${STUB_BIN}/docker"

  cat >"${STUB_BIN}/buildkite-agent" <<'STUB'
#!/bin/bash
printf '%s\n' "$@" >"${DOCKER_LOG}.annotate"
cat >"${DOCKER_LOG}.annotate.body"
STUB
  chmod +x "${STUB_BIN}/buildkite-agent"

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

@test "fail_pipeline_on_first_exception option is honoured" {
  export BUILDKITE_PLUGIN_BIGQUERY_FAIL_PIPELINE_ON_FIRST_EXCEPTION=false
  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -qx "fail_pipeline_on_first_exception=false" "${DOCKER_LOG}.create"
}

@test "fail_pipeline_on_first_exception defaults to true" {
  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -qx "fail_pipeline_on_first_exception=true" "${DOCKER_LOG}.create"
}

@test "execute_only_changed_files defaults to false and skips git" {
  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -qx "execute_only_changed_files=false" "${DOCKER_LOG}.create"
  grep -qx "updated_files=" "${DOCKER_LOG}.create"
}

@test "changed files are sent relative to the checkout (default branch)" {
  echo '{}' >schemas/ds/b.json
  git add -A && git commit -qm second
  export BUILDKITE_PLUGIN_BIGQUERY_EXECUTE_ONLY_CHANGED_FILES=true

  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -qx "execute_only_changed_files=true" "${DOCKER_LOG}.create"
  grep -qx "updated_files=schemas/ds/b.json" "${DOCKER_LOG}.create"
}

@test "feature branch is compared with the base branch, not just the last commit" {
  git update-ref refs/remotes/origin/main HEAD
  git checkout -q -b feature
  echo '{}' >schemas/ds/b.json && git add -A && git commit -qm one
  echo '{}' >schemas/ds/c.json && git add -A && git commit -qm two
  export BUILDKITE_BRANCH=feature
  export BUILDKITE_PLUGIN_BIGQUERY_EXECUTE_ONLY_CHANGED_FILES=true

  run "${HOOK}"
  [ "$status" -eq 0 ]
  # multi-line values print one path per line in the argument log
  grep -qx "updated_files=schemas/ds/b.json" "${DOCKER_LOG}.create"
  grep -qx "schemas/ds/c.json" "${DOCKER_LOG}.create"
}

@test "first commit processes all files" {
  export BUILDKITE_PLUGIN_BIGQUERY_EXECUTE_ONLY_CHANGED_FILES=true
  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -qx "execute_only_changed_files=false" "${DOCKER_LOG}.create"
}

@test "a git failure fails the step instead of silently deploying nothing" {
  echo '{}' >schemas/ds/b.json
  git add -A && git commit -qm second
  # A git that can list HEAD^ but cannot diff
  cat >"${STUB_BIN}/git" <<'STUB'
#!/bin/bash
case "$1" in
  diff-tree | diff) exit 128 ;;
  *) exec /usr/bin/env -i PATH="/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin" git "$@" ;;
esac
STUB
  chmod +x "${STUB_BIN}/git"
  export BUILDKITE_PLUGIN_BIGQUERY_EXECUTE_ONLY_CHANGED_FILES=true

  run "${HOOK}"
  [ "$status" -eq 1 ]
  [[ $output == *"could not list the files changed"* ]]
  [ ! -e "${DOCKER_LOG}.create" ]
}

@test "the docker pull retry count comes from this plugin's namespace" {
  cat >"${STUB_BIN}/docker" <<'STUB'
#!/bin/bash
echo "$1" >>"${DOCKER_LOG}"
[ "$1" = pull ] && exit 1
exit 0
STUB
  export BUILDKITE_PLUGIN_BIGQUERY_DOCKER_PULL_RETRIES=2
  run "${HOOK}"
  [ "$status" -ne 0 ]
  [ "$(grep -c '^pull$' "${DOCKER_LOG}")" -eq 2 ]
}

@test "without a service account the hook uses Application Default Credentials" {
  unset gcp_service_account
  run "${HOOK}"
  [ "$status" -eq 0 ]
  [[ $output == *"Application Default Credentials"* ]]
  ! grep -qx -- "credentials" "${DOCKER_LOG}.create"
  ! grep -q "google-adc.json" "${DOCKER_LOG}.create"
}

@test "GOOGLE_APPLICATION_CREDENTIALS file is mounted read-only when no key is set" {
  unset gcp_service_account
  echo '{"type": "external_account"}' >"${TEST_DIR}/adc.json"
  export GOOGLE_APPLICATION_CREDENTIALS="${TEST_DIR}/adc.json"
  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -qx "${TEST_DIR}/adc.json:/run/secrets/google-adc.json:ro" "${DOCKER_LOG}.create"
  grep -qx "GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/google-adc.json" "${DOCKER_LOG}.create"
}

@test "a missing GOOGLE_APPLICATION_CREDENTIALS file fails the step" {
  unset gcp_service_account
  export GOOGLE_APPLICATION_CREDENTIALS="${TEST_DIR}/does-not-exist.json"
  run "${HOOK}"
  [ "$status" -eq 1 ]
  [[ $output == *"does not exist"* ]]
}

@test "the service account key takes precedence over GOOGLE_APPLICATION_CREDENTIALS" {
  echo '{}' >"${TEST_DIR}/adc.json"
  export GOOGLE_APPLICATION_CREDENTIALS="${TEST_DIR}/adc.json"
  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -qx -- "credentials" "${DOCKER_LOG}.create"
  ! grep -q "google-adc.json" "${DOCKER_LOG}.create"
}

@test "annotations are off by default" {
  run "${HOOK}"
  [ "$status" -eq 0 ]
  [ ! -e "${DOCKER_LOG}.annotate" ]
  ! grep -q "annotation_file" "${DOCKER_LOG}.create"
}

@test "annotate copies the summary out of the container and annotates from the host" {
  export BUILDKITE_PLUGIN_BIGQUERY_ANNOTATE=true
  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -qx "annotation_file=/tmp/bigquery-annotation.md" "${DOCKER_LOG}.create"
  grep -qx -- "--style" "${DOCKER_LOG}.annotate"
  grep -qx "success" "${DOCKER_LOG}.annotate"
  grep -qx "bigquery" "${DOCKER_LOG}.annotate"
  grep -qx "STUB-ANNOTATION" "${DOCKER_LOG}.annotate.body"
}

@test "a failed deployment is annotated as an error and still fails the step" {
  export BUILDKITE_PLUGIN_BIGQUERY_ANNOTATE=true
  export BUILDKITE_PLUGIN_BIGQUERY_ANNOTATION_CONTEXT=my-ctx
  export STUB_START_RC=3
  run "${HOOK}"
  [ "$status" -eq 3 ]
  grep -qx "error" "${DOCKER_LOG}.annotate"
  grep -qx "my-ctx" "${DOCKER_LOG}.annotate"
}

@test "the container is removed after the run" {
  run "${HOOK}"
  [ "$status" -eq 0 ]
  tail -n 1 "${DOCKER_LOG}" | grep -qx "rm"
  ! grep -qx -- "--rm" "${DOCKER_LOG}.create"
}

@test "a missing summary is skipped without failing the deployment" {
  export BUILDKITE_PLUGIN_BIGQUERY_ANNOTATE=true
  export STUB_NO_ANNOTATION=1
  run "${HOOK}"
  [ "$status" -eq 0 ]
  [[ $output == *"No deployment summary was produced"* ]]
  [ ! -e "${DOCKER_LOG}.annotate" ]
}

@test "an annotate failure on the host does not change the result" {
  export BUILDKITE_PLUGIN_BIGQUERY_ANNOTATE=true
  printf '#!/bin/bash\nexit 1\n' >"${STUB_BIN}/buildkite-agent"
  run "${HOOK}"
  [ "$status" -eq 0 ]
  [[ $output == *"Could not create the annotation"* ]]
}

@test "include and exclude arrays are passed to the container, one pattern per line" {
  export BUILDKITE_PLUGIN_BIGQUERY_INCLUDE_0="sales/**"
  export BUILDKITE_PLUGIN_BIGQUERY_INCLUDE_1="ops/*.json"
  export BUILDKITE_PLUGIN_BIGQUERY_EXCLUDE_0="**/*.sql"
  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -qx "include_patterns=sales/\*\*" "${DOCKER_LOG}.create"
  grep -qx "ops/\*.json" "${DOCKER_LOG}.create"
  grep -qx 'exclude_patterns=\*\*/\*.sql' "${DOCKER_LOG}.create"
}

@test "without include or exclude the patterns are empty" {
  run "${HOOK}"
  [ "$status" -eq 0 ]
  grep -qx "include_patterns=" "${DOCKER_LOG}.create"
  grep -qx "exclude_patterns=" "${DOCKER_LOG}.create"
}
