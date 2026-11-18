#!/bin/sh
# POSIX entry point for the apollo-new-project skill.
# Implementation: tools/write_project_files.py (Python standard library only).
# No Claude-specific or Cursor-specific variables. CONTRIBUTING.md section 12.
set -eu
search() {
    dir=$1
    while [ "$dir" != "/" ]; do
        if [ -f "$dir/tools/write_project_files.py" ] && [ -f "$dir/tools/resolve_kb.py" ]; then
            printf '%s\n' "$dir"
            return 0
        fi
        nxt=$(CDPATH= cd -- "$dir/.." && pwd)
        [ "$nxt" = "$dir" ] && return 1
        dir=$nxt
    done
    return 1
}
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
root=$(search "$here" || true)
if [ -z "$root" ]; then
    cwd=$(CDPATH= cd -- . && pwd)
    root=$(search "$cwd" || true)
fi
if [ -z "$root" ]; then
    echo "PROBLEM=cannot find the knowledge base root that contains tools/write_project_files.py"
    exit 1
fi

# Git Bash: python3 is often a Windows Store alias. Re-exec in WSL.
# shellcheck disable=SC1091
. "$root/tools/wsl_reexec.sh"
akb_wsl_reexec "$here/write-project-files.sh" "$@"

py=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[0] >= 3 else 1)' >/dev/null 2>&1; then
        py=$candidate
        break
    fi
done
if [ -z "$py" ]; then
    echo "PROBLEM=python3 is not on PATH (this entry point is POSIX sh; the implementation uses the Python standard library)"
    echo "RECOVERY=Install Python 3 so that python3 -c \"import sys\" runs, or run this script from WSL: wsl -e sh <this-script>"
    if [ -n "${MSYSTEM:-}" ]; then
        echo "RECOVERY=This shell is Git Bash or MSYS (MSYSTEM=${MSYSTEM}). command -v python3 often finds a Windows Store alias that does not run Python, and WSL python3 was not usable."
    fi
    exit 1
fi
exec "$py" "$root/tools/write_project_files.py" "$@"
