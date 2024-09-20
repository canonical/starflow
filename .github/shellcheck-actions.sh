#!/usr/bin/env bash
# https://github.com/snapcrafters/ci/blob/main/.github/shellcheck-actions.sh
set -euo pipefail
info() { echo -e "\e[92m[+] $@\e[0m"; }
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

for f in "$DIR"/../**/*.yaml; do
    info "Linting scripts in $f"
    yq '.runs.steps[].run' "$f" | grep -v -P "^null$" | shellcheck -
done
