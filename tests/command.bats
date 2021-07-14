#!/usr/bin/env bats

load "$BATS_PATH/load.bash"

source ".env"

# Uncomment to enable stub debugging
export GIT_STUB_DEBUG=/dev/tty

setup() {
  export BUILDKITE_PLUGIN_BIGQUERY_DEBUG_MODE="true"
  export BUILDKITE_REPO="shared/repo"
  stub buildkite-agent ${UPLOAD_ARGS}
}

teardown() {
    unstub docker
    TMPDIR=$TMPDIR_BACKUP
    unset BUILDKITE_PLUGIN_BIGQUERY_DEBUG_MODE
    unset BUILDKITE_REPO
}

@test "Fails when project key not set" {
    unset BUILDKITE_PLUGIN_BIGQUERY_GCP_PROJECT

    stub docker
    run $PWD/hooks/command
    assert_failure
    assert_output --partial "ERROR: bigquery project key not set"
}

@test "Fails when dataset key not set" {
    export BUILDKITE_PLUGIN_BIGQUERY_GCP_PROJECT="gcp-project"
    unset BUILDKITE_PLUGIN_BIGQUERY_DATASET_SCHEMA_DIRECTORY

    stub docker
    run $PWD/hooks/command
    assert_failure
    assert_output --partial "ERROR: dataset schema not set"
}

@test "Fails when gcp service account key not set" {
    export BUILDKITE_PLUGIN_BIGQUERY_GCP_PROJECT="gcp-project"
    export BUILDKITE_PLUGIN_BIGQUERY_DATASET_SCHEMA_DIRECTORY="dataset"
    unset BUILDKITE_PLUGIN_BIGQUERY_GCP_SERVICE_ACCOUNT

    stub docker
    run $PWD/hooks/command
    assert_failure
    assert_output --partial "ERROR: gcp service account not set"
}

@test "Logs start of run" {
    export BUILDKITE_PLUGIN_BIGQUERY_GCP_PROJECT="gcp-project"
    export BUILDKITE_PLUGIN_BIGQUERY_DATASET_SCHEMA_DIRECTORY="dataset"
    export gcp_service_account="credentials"

    stub docker

    run $PWD/hooks/command
    assert_success
    assert_output --partial "--- :hammer_and_wrench: Pulling docker image"
}
