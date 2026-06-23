#!/usr/bin/env bash
# https://github.com/snapcrafters/ci/blob/main/.github/shellcheck-actions.sh
set -euo pipefail
info() { echo -e "\e[92m[+] $@\e[0m"; }
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

SHELLCHECK_OPTS=(
    "-s" "bash"
    "-e" "2296"
    "-e" "2157"
    "-e" "2129"
    "-e" "2154"
)

for f in "$DIR"/../**/*.yaml; do
    info "Linting scripts in $f"
    # Filter out scripts that don't have any shell scripts in them
    scripts=$(yq '.runs.steps[].run' "$f" | (grep -v -P "^null$" || true))
    if [[ -n "$scripts" ]]; then
        echo "$scripts" | shellcheck "${SHELLCHECK_OPTS[@]}" -
    fi
done
