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
    script=$(yq '.runs.steps[].run' "$f" 2>/dev/null | grep -v -P "^null$")
    if [[ "$script" == *"toJSON(matrix['platform'])"* ]]; then
        echo "[SKIP] Skipping shellcheck for GitHub Actions expressions in $f"
    else
        shellcheck "${SHELLCHECK_OPTS[@]}" - <<< "$script"
    fi
done
