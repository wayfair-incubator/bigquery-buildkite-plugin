# #!/usr/bin/env bats
#
# load "$BATS_PATH/load.bash"
#
# # Uncomment to enable stub debugging
# # export GIT_STUB_DEBUG=/dev/tty
#
# @test "Dummy output outputs as expected" {
#   # Note there is no export BUILDKITE_PULL_REQUEST, or PULL_REQUEST_RPO
#   run $PWD/hooks/command
#
#   assert_success
#   assert_output --partial "this is the command hook!"
# }