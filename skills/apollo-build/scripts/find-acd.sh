#!/bin/sh
# find-acd.sh - find ApolloCrossDev and check that it can build.
#
# Usage: sh find-acd.sh [--offline] [project folder]
# Prints KEY=value lines (ACD_ROOT, PREFIX, GCC, BUILT, TEMPLATE, MAKEFILE,
# BUILD, BUILD_DETAIL) and exits 0 when the GCC-6.50-Dev toolchain is
# complete; otherwise prints PROBLEM= lines and exits 1.
#
# When the project has a Makefile, BUILD= is the one verified non-uploading
# command (make compile, or make cleanbefore build). If that cannot be
# established, a NOTE= says why no Make command can be recommended. This
# script does not run make.
#
# Updates (skipped with --offline or without network), as UPDATE= lines:
#   UPDATE=checkout ...   the ApolloCrossDev checkout is behind GitHub:
#                         git pull (quick; LOCAL_CHANGES= warns first)
#   UPDATE=compiler ...   GCC-6.50-Dev was built before its install script
#                         or the patches last changed, in the local checkout
#                         (checked also with --offline) or on GitHub: reinstall
#   UPDATES=none          up to date
#
# Where it looks for ApolloCrossDev, in this order:
#   1. $APOLLOCROSSDEV
#   2. two folders above the project (the project is in ApolloCrossDev/Projects/)
#   3. $HOME/ApolloCrossDev

# Git Bash cannot run the Linux compiler. Re-exec in WSL when python3 works there.
_akb_tools=$(CDPATH= cd -- "$(dirname "$0")/../../../tools" 2>/dev/null && pwd || true)
if [ -n "$_akb_tools" ] && [ -f "$_akb_tools/wsl_reexec.sh" ]; then
    # shellcheck disable=SC1091
    . "$_akb_tools/wsl_reexec.sh"
    _akb_script=$(CDPATH= cd -- "$(dirname "$0")" && pwd)/$(basename "$0")
    akb_wsl_reexec "$_akb_script" "$@"
fi
unset _akb_tools _akb_script

offline=0
[ "$1" = "--offline" ] && { offline=1; shift; }
project=${1:-.}
problems=0
problem() { echo "PROBLEM=$1"; problems=1; }

find_classify_prog() {
    script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
    tools=$(CDPATH= cd -- "$script_dir/../../../tools" 2>/dev/null && pwd || true)
    if [ -n "$tools" ] && [ -f "$tools/classify_build.py" ]; then
        printf '%s\n' "$tools/classify_build.py"
        return 0
    fi
    dir=$(CDPATH= cd -- . && pwd)
    while [ "$dir" != "/" ]; do
        if [ -f "$dir/tools/classify_build.py" ]; then
            printf '%s\n' "$dir/tools/classify_build.py"
            return 0
        fi
        nxt=$(CDPATH= cd -- "$dir/.." && pwd)
        [ "$nxt" = "$dir" ] && break
        dir=$nxt
    done
    return 1
}

find_py() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[0] >= 3 else 1)' >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

# Classify the project Makefile. Never recommend a target that was not
# shown to be non-uploading, and never run make.
report_build() {
    file=$1
    prog=$(find_classify_prog) || {
        echo "NOTE=no Make command can be recommended automatically: classify_build.py is not available"
        return
    }
    py=$(find_py) || {
        echo "NOTE=no Make command can be recommended automatically: python3 is not available to classify the Makefile"
        return
    }
    output=$("$py" "$prog" --makefile "$file") || {
        echo "NOTE=no Make command can be recommended automatically: the Makefile could not be classified"
        return
    }
    status=$(printf '%s\n' "$output" | sed -n 's/^STATUS=//p' | head -n 1)
    build_cmd=$(printf '%s\n' "$output" | sed -n 's/^COMMAND=//p' | head -n 1)
    reason=$(printf '%s\n' "$output" | sed -n 's/^REASON=//p' | head -n 1)
    if [ "$status" = "verified-non-uploading" ] && [ -n "$build_cmd" ]; then
        echo "BUILD=$build_cmd"
        echo "BUILD_DETAIL=$reason"
    else
        echo "NOTE=${reason:-no Make command can be recommended automatically: the Makefile could not be classified}"
    fi
}

if [ -n "$APOLLOCROSSDEV" ] && [ ! -d "$APOLLOCROSSDEV/Compilers" ]; then
    problem "APOLLOCROSSDEV=$APOLLOCROSSDEV has no Compilers folder; the Makefile uses it, so fix or unset it"
fi

root=""
for c in "$APOLLOCROSSDEV" "$project/../.." "$HOME/ApolloCrossDev"; do
    [ -n "$c" ] && [ -d "$c/Compilers" ] && { root=$(cd "$c" && pwd); break; }
done
if [ -z "$root" ]; then
    problem "ApolloCrossDev not found. Install it (github.com/WDrijver/ApolloCrossDev) and set APOLLOCROSSDEV to its folder."
    exit 1
fi
echo "ACD_ROOT=$root"
[ -n "$APOLLOCROSSDEV" ] || echo "NOTE=APOLLOCROSSDEV is not set; projects outside $root/Projects need it (export APOLLOCROSSDEV=$root)"

prefix="$root/Compilers/GCC-6.50-Dev"
echo "PREFIX=$prefix"
for b in m68k-amigaos-gcc m68k-amigaos-g++ vasmm68k_mot; do
    [ -x "$prefix/bin/$b" ] || problem "$prefix/bin/$b is missing: the GCC-6.50-Dev install is incomplete (see Compilers/GCC-6.50-Dev/_logs/*_err.log)"
done
[ -x "$prefix/bin/m68k-amigaos-gcc" ] && echo "GCC=$("$prefix/bin/m68k-amigaos-gcc" --version | head -n 1)"

# when the compiler was built (UTC), from the gcc binary's file time.
# GNU stat is tried first. Its -f flag prints a filesystem report and
# fails, and a command substitution would keep that report along with the
# epoch, so the timestamp would be empty and UPDATE=compiler would not run.
built=""
if [ -f "$prefix/bin/m68k-amigaos-gcc" ]; then
    t=$(stat -c %Y "$prefix/bin/m68k-amigaos-gcc" 2>/dev/null || stat -f %m "$prefix/bin/m68k-amigaos-gcc" 2>/dev/null)
    built=$(date -u -d "@$t" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -r "$t" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null)
    [ -n "$built" ] && echo "BUILT=$built"
fi

template="$root/Projects/_makefiles/Makefile"
if [ -f "$template" ]; then
    echo "TEMPLATE=$(sed -n 's/^# ApolloCrossDev Makefile Template //p' "$template" | head -n 1)"
else
    problem "$template is missing"
fi

if [ -f "$project/Makefile" ]; then
    echo "MAKEFILE=$(sed -n 's/^# ApolloCrossDev Makefile Template //p' "$project/Makefile" | head -n 1)"
    report_build "$project/Makefile"
fi

case $(uname) in Darwin) script=GCC-6.50-Dev-MacOS.sh ;; *) script=GCC-6.50-Dev-Linux.sh ;; esac
updates=0
compiler_old=0

# compiler older than the install script or patches in the local checkout:
# needs no network, and catches a git pull without a reinstall
if [ -n "$built" ] && git -C "$root" rev-parse HEAD >/dev/null 2>&1; then
    for path in "$script" Compilers/_archives/patches; do
        when=$(TZ=UTC git -C "$root" log -1 --format=%cd --date=format-local:%Y-%m-%dT%H:%M:%SZ -- "$path" 2>/dev/null)
        what=$(git -C "$root" log -1 --format=%s -- "$path" 2>/dev/null)
        if [ -n "$when" ] && [ "$when" \> "$built" ]; then
            echo "UPDATE=compiler: built $built, $path changed $when in the local checkout ($what); reinstall with: cd $root && ./$script (about 30 minutes)"
            updates=1
            compiler_old=1
            break
        fi
    done
fi

# PR #26 and PR #28 live in these patch files. A binary older than the
# checkout is already reported above. A checkout that does not contain the
# files cannot show that the binary was built with them, even when the
# binary is newer than this checkout.
if [ ! -f "$root/Compilers/_archives/patches/m68k-btst-mem-offset-fix.patch" ] \
    || [ ! -f "$root/Compilers/_archives/patches/reload-ind-equiv-offset-fix.patch" ]; then
    echo "NOTE=this ApolloCrossDev checkout has no m68k-btst-mem-offset-fix.patch (pull request #26) or no reload-ind-equiv-offset-fix.patch (pull request #28), so the installed GCC-6.50-Dev binary is not shown to include those fixes. A checkout that has the files is still not a rebuilt compiler."
fi

# updates on GitHub
if [ $offline = 0 ]; then
    if git -C "$root" rev-parse HEAD >/dev/null 2>&1; then
        here=$(git -C "$root" rev-parse HEAD)
        there=$(git -C "$root" ls-remote origin refs/heads/main 2>/dev/null | cut -f1)
        if [ -z "$there" ]; then
            echo "NOTE=could not reach GitHub to check for ApolloCrossDev updates"
        elif [ "$here" != "$there" ] && ! git -C "$root" merge-base --is-ancestor "$there" "$here" 2>/dev/null; then
            echo "UPDATE=checkout: local ${here%"${here#???????}"}, GitHub ${there%"${there#???????}"}; update with: git -C $root pull"
            updates=1
            changed=$(git -C "$root" status --porcelain --untracked-files=no | wc -l | tr -d ' ')
            [ "$changed" != 0 ] && echo "LOCAL_CHANGES=$changed tracked files changed in $root; commit or stash them before git pull"
        fi
    fi
    if [ -n "$built" ] && [ $compiler_old = 0 ]; then
        for path in "$script" Compilers/_archives/patches; do
            json=$(curl -s -m 8 "https://api.github.com/repos/WDrijver/ApolloCrossDev/commits?path=$path&per_page=1" 2>/dev/null)
            when=$(printf '%s' "$json" | sed -n 's/.*"date": *"\([^"]*\)".*/\1/p' | head -n 1)
            what=$(printf '%s' "$json" | sed -n 's/.*"message": *"\([^"\\]*\).*/\1/p' | head -n 1)
            if [ -z "$when" ]; then
                echo "NOTE=could not check $path on GitHub"
            elif [ "$when" \> "$built" ]; then
                echo "UPDATE=compiler: built $built, $path changed $when ($what); reinstall with: cd $root && ./$script (about 30 minutes)"
                updates=1
                break
            fi
        done
    fi
fi
[ $updates = 0 ] && [ $offline = 0 ] && echo "UPDATES=none"

exit $problems
