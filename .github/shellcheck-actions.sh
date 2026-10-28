#!/usr/bin/env bash
# https://github.com/snapcrafters/ci/blob/main/.github/shellcheck-actions.sh
set -euo pipefail
info() { echo -e "\e[92m[+] $*\e[0m"; }
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

SHELLCHECK_OPTS=(
    "-s" "bash"
    "-e" "2296"
    "-e" "2157"
    "-e" "2129"
    "-e" "2154"
)

# Composite actions keep their steps under .runs.steps and workflows under
# .jobs.<id>.steps. Each run block is checked on its own since steps run as
# separate scripts. Every file is checked before the script exits.
shopt -s nullglob
failed=0
scripts=$(mktemp)
trap 'rm -f "$scripts"' EXIT
for f in "$DIR"/../*/action.yaml "$DIR"/workflows/*.yaml; do
    info "Linting scripts in $f"
    if ! yq --nul-output '(.runs.steps[]?, .jobs[]?.steps[]?) | select(has("run")) | .run' "$f" > "$scripts"; then
        failed=1
        continue
    fi
    while IFS= read -r -d '' script; do
        if ! shellcheck "${SHELLCHECK_OPTS[@]}" - <<< "$script"; then
            failed=1
        fi
    done < "$scripts"
done

exit "$failed"
