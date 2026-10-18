#!/usr/bin/env bash
# Read released versions from a Keep a Changelog file.
#
#   changelog.sh latest [CHANGELOG.md]       print the newest released version (no "v")
#   changelog.sh notes VERSION [CHANGELOG.md] print the notes of that version's section
#
# "## [Unreleased]" is never a release. Exits 1 if nothing matches.
set -euo pipefail

command="${1:-}"
case "$command" in
latest)
	file="${2:-CHANGELOG.md}"
	# `q` stops sed at the first release; piping into `head` would SIGPIPE under pipefail
	version=$(sed -nE '/^## \[[0-9]+\.[0-9]+\.[0-9]+\]/{s/^## \[([0-9]+\.[0-9]+\.[0-9]+)\].*/\1/p;q;}' "$file")
	if [[ -z $version ]]; then
		echo "No released version found in $file" >&2
		exit 1
	fi
	echo "$version"
	;;
notes)
	version="${2:?usage: changelog.sh notes VERSION [FILE]}"
	file="${3:-CHANGELOG.md}"
	notes=$(awk -v v="$version" '
		$0 ~ "^## \\[" v "\\]" { found = 1; next }
		found && /^## \[/ { exit }
		found { print }
	' "$file")
	if [[ -z ${notes//[[:space:]]/} ]]; then
		echo "No notes found for $version in $file" >&2
		exit 1
	fi
	printf '%s\n' "$notes"
	;;
*)
	echo "usage: changelog.sh latest [FILE] | notes VERSION [FILE]" >&2
	exit 2
	;;
esac
