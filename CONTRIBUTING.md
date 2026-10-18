# Contributing

When contributing to this repository, please first discuss the change you wish to make via issue before making a change. 

Please note we have a [code of conduct](CODE_OF_CONDUCT.md), please follow it in all your interactions with the project.

## Pull Request Process

1. Ensure the CI pipeline and all checks are passing.
2. Update documentation with details of changes.
3. Add an entry to the [change log](CHANGELOG.md).
4. You may merge the Pull Request in once it has approvals of two other developers. If you do not have permission to do
    that, you may request the second reviewer to merge it for you.
## Releasing

Users pin a release tag, for example `wayfair-incubator/bigquery#v3.0.0`. A release is cut by a pull request:

1. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` (follow
   [Semantic Versioning](https://semver.org/): breaking changes bump the major version) and add a fresh empty
   `## [Unreleased]` above it.
2. In `README.md`, update the plugin version in the usage examples to `vX.Y.Z`.
3. Get the pull request approved and merge it.

The [Release workflow](.github/workflows/release.yml) then tags the merge commit `vX.Y.Z` and creates a GitHub
release whose notes are that changelog section. It does nothing if the release already exists, and fails if the
README does not mention the new version. No tokens or secrets are needed. Do not create tags by hand.
