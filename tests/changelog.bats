#!/usr/bin/env bats

# Tests for .github/scripts/changelog.sh, which the release workflow relies on.

setup() {
  SCRIPT="${BATS_TEST_DIRNAME}/../.github/scripts/changelog.sh"
  TEST_DIR="$(mktemp -d)"
  cat >"${TEST_DIR}/CHANGELOG.md" <<'MD'
# Changelog

## [Unreleased]

### Added

- Something new

## [3.0.0] - 2026-11-01

### Changed

- Big change

## [2.0.0] - 2025-11-02

- Old change
MD
}

teardown() {
  rm -rf "${TEST_DIR}"
}

@test "latest ignores Unreleased and returns the newest version" {
  run "${SCRIPT}" latest "${TEST_DIR}/CHANGELOG.md"
  [ "$status" -eq 0 ]
  [ "$output" = "3.0.0" ]
}

@test "notes returns only the requested section" {
  run "${SCRIPT}" notes 3.0.0 "${TEST_DIR}/CHANGELOG.md"
  [ "$status" -eq 0 ]
  [[ $output == *"Big change"* ]]
  [[ $output != *"Old change"* ]]
  [[ $output != *"Something new"* ]]
}

@test "notes of the last section run to the end of the file" {
  run "${SCRIPT}" notes 2.0.0 "${TEST_DIR}/CHANGELOG.md"
  [ "$status" -eq 0 ]
  [[ $output == *"Old change"* ]]
}

@test "notes fails for an unknown version" {
  run "${SCRIPT}" notes 9.9.9 "${TEST_DIR}/CHANGELOG.md"
  [ "$status" -eq 1 ]
}

@test "latest fails when only Unreleased exists" {
  printf '# Changelog\n\n## [Unreleased]\n\n- x\n' >"${TEST_DIR}/only.md"
  run "${SCRIPT}" latest "${TEST_DIR}/only.md"
  [ "$status" -eq 1 ]
}

@test "the real changelog has a release the workflow can find" {
  run "${SCRIPT}" latest "${BATS_TEST_DIRNAME}/../CHANGELOG.md"
  [ "$status" -eq 0 ]
  run "${SCRIPT}" notes "${output}" "${BATS_TEST_DIRNAME}/../CHANGELOG.md"
  [ "$status" -eq 0 ]
}
