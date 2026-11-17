#!/bin/sh
# Re-exec a skill entry point under WSL when this shell is Git Bash or MSYS.
#
# Git Bash often has python3 and python on PATH as Windows Store aliases.
# Those commands do not run Python. ApolloCrossDev's compiler is a Linux
# binary, so that shell is not a build host. WSL does not inherit
# APOLLOCROSSDEV from Windows; when the variable is set, it is forwarded
# after the same path conversion.
#
# No-op when MSYSTEM is unset (Linux, macOS, and a shell that is already
# WSL). Sourced by the skill entry points. Not an entry point itself.
# POSIX sh. No Claude-specific or Cursor-specific variables.

akb_to_wsl_path() {
    p=$1
    # Already a WSL mount. cygpath would turn /mnt/d/foo into a Windows path
    # and the following step would convert it again.
    case $p in
        /mnt/[A-Za-z]/*|/mnt/[A-Za-z])
            printf '%s' "$p"
            return
            ;;
    esac
    # Git Bash /tmp, /usr and similar are not WSL paths. cygpath -w maps them
    # onto a drive. Only absolute paths are converted: a flag, a slug or a URL
    # must be left as written. cygpath rewrites https:// into a broken path.
    case $p in
        [A-Za-z]:*|/*)
            # Only paths that exist in this shell. A WSL ext4 path such as
            # /home/ami/ApolloCrossDev is not a Git Bash path; cygpath -w would
            # invent one under Git's own root and WSL could not open the file.
            if [ -n "${MSYSTEM:-}" ] && command -v cygpath >/dev/null 2>&1 \
                && { [ -e "$p" ] || [ -d "$(dirname -- "$p")" ]; }; then
                win=$(cygpath -w -- "$p" 2>/dev/null || true)
                if [ -n "$win" ]; then
                    p=$win
                fi
            fi
            ;;
    esac
    case $p in
        [A-Za-z]:*)
            drive=$(printf '%s' "$p" | cut -c1 | tr '[:upper:]' '[:lower:]')
            rest=$(printf '%s\n' "$p" | cut -c3- | sed 's#\\#/#g')
            case $rest in
                /*) ;;
                *) rest=/$rest ;;
            esac
            printf '/mnt/%s%s' "$drive" "$rest"
            ;;
        /[A-Za-z]/*)
            drive=$(printf '%s' "$p" | cut -c2 | tr '[:upper:]' '[:lower:]')
            rest=$(printf '%s' "$p" | cut -c3-)
            printf '/mnt/%s%s' "$drive" "$rest"
            ;;
        *)
            printf '%s' "$p"
            ;;
    esac
}

akb_wsl_reexec() {
    if [ -z "${MSYSTEM:-}" ]; then
        return 0
    fi
    wslbin=""
    if command -v wsl.exe >/dev/null 2>&1; then
        wslbin=$(command -v wsl.exe)
    elif command -v wsl >/dev/null 2>&1; then
        wslbin=$(command -v wsl)
    fi
    if [ -z "$wslbin" ] || ! "$wslbin" -e python3 -c 'import sys' >/dev/null 2>&1; then
        echo "NOTE=MSYSTEM=${MSYSTEM} and WSL python3 is not usable. Staying in this shell." >&2
        echo "RECOVERY=Install a Python 3 that \`python3 -c \"import sys\"\` can run, or start WSL and retry. On Git Bash the python3 command is often a Windows Store alias, which does not run Python." >&2
        return 0
    fi
    script=$1
    _dir=$(mktemp -d "${TMPDIR:-/tmp}/akb-reexec.XXXXXX")
    _i=0
    _skip=1
    for _arg in "$@"; do
        if [ "$_skip" -eq 1 ]; then
            _skip=0
            continue
        fi
        printf '%s\n' "$(akb_to_wsl_path "$_arg")" > "$_dir/$_i"
        _i=$((_i + 1))
    done
    set --
    _j=0
    while [ "$_j" -lt "$_i" ]; do
        IFS= read -r _val < "$_dir/$_j"
        set -- "$@" "$_val"
        _j=$((_j + 1))
    done
    rm -rf "$_dir"
    wsl_script=$(akb_to_wsl_path "$script")
    echo "NOTE=re-executing under WSL because MSYSTEM=${MSYSTEM} has no reliable Python 3" >&2
    if [ -n "${APOLLOCROSSDEV:-}" ]; then
        _acd=$(akb_to_wsl_path "$APOLLOCROSSDEV")
        echo "NOTE=forwarding APOLLOCROSSDEV to WSL as ${_acd}" >&2
        MSYS_NO_PATHCONV=1 exec "$wslbin" -e env "APOLLOCROSSDEV=${_acd}" sh "$wsl_script" "$@"
    fi
    MSYS_NO_PATHCONV=1 exec "$wslbin" -e sh "$wsl_script" "$@"
    echo "PROBLEM=WSL re-exec failed for $wsl_script" >&2
    exit 1
}
