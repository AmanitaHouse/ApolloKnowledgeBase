#!/bin/sh
# find-acd.sh - find ApolloCrossDev and check that it can build.
#
# Usage: sh find-acd.sh [--offline] [project folder]
# Prints KEY=value lines (ACD_ROOT, PREFIX, GCC, BUILT, TEMPLATE, MAKEFILE,
# BUILD, BUILD_DETAIL, PROJECT_PREFIX, COMPILER_STATUS, NDK, NDK_PATH,
# NDK_COMPILER, NDK_STATUS) and exits 0 when the GCC-6.50-Dev toolchain is
# complete and no confirmed compiler-path or NDK PROBLEM remains; otherwise
# prints PROBLEM= lines and exits 1.
#
# When the project has a Makefile, BUILD= is the one verified non-uploading
# command (make compile, or make cleanbefore build). That is upload safety
# only. PROJECT_PREFIX / COMPILER_STATUS say whether the Makefile's PREFIX
# resolves for this project location. If that cannot be established, a
# PROBLEM= blocks compilation even when BUILD= is present. A NOTE= says why
# no Make command can be recommended when classification fails. This script
# does not run make. A BUILD= line does not clear a compiler-path or NDK
# PROBLEM=.
#
# Documented NDK headers (toolchain/target-os-headers.md), under PREFIX:
#   NDK 3.9  m68k-amigaos/ndk39-include
#   NDK 3.2  m68k-amigaos/ndk32-include/Include_H
# m68k-amigaos/ndk-include is not a documented substitute.
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

find_tools_prog() {
    name=$1
    script_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
    tools=$(CDPATH= cd -- "$script_dir/../../../tools" 2>/dev/null && pwd || true)
    if [ -n "$tools" ] && [ -f "$tools/$name" ]; then
        printf '%s\n' "$tools/$name"
        return 0
    fi
    dir=$(CDPATH= cd -- . && pwd)
    while [ "$dir" != "/" ]; do
        if [ -f "$dir/tools/$name" ]; then
            printf '%s\n' "$dir/tools/$name"
            return 0
        fi
        nxt=$(CDPATH= cd -- "$dir/.." && pwd)
        [ "$nxt" = "$dir" ] && break
        dir=$nxt
    done
    return 1
}

find_classify_prog() {
    find_tools_prog classify_build.py
}

find_resolve_compiler_prog() {
    find_tools_prog resolve_compiler.py
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

# Effective project compiler PREFIX for this Makefile and location.
# Upload-safety BUILD= stays separate. Emits PROJECT_PREFIX, COMPILER_STATUS,
# and PROBLEM= when the path cannot be used.
report_project_compiler() {
    file=$1
    project=$2
    acd_root=$3
    prog=$(find_resolve_compiler_prog) || {
        echo "NOTE=could not check project compiler PREFIX: resolve_compiler.py is not available"
        return
    }
    py=$(find_py) || {
        echo "NOTE=could not check project compiler PREFIX: python3 is not available"
        return
    }
    output=$("$py" "$prog" --makefile "$file" --project "$project" --acd-root "$acd_root" --emit) || true
    printf '%s\n' "$output"
    if printf '%s\n' "$output" | grep -q '^PROBLEM='; then
        problems=1
    fi
    return 0
}

# Version-specific APOLLOCROSSDEV guidance from the project Makefile, or the
# ApolloCrossDev template when the project has none yet.
report_apollocrossdev_note() {
    project=$1
    acd_root=$2
    [ -n "$APOLLOCROSSDEV" ] && return 0
    file=""
    if [ -f "$project/Makefile" ]; then
        file=$project/Makefile
    elif [ -f "$acd_root/Projects/_makefiles/Makefile" ]; then
        file=$acd_root/Projects/_makefiles/Makefile
    else
        return 0
    fi
    prefix_line=$(
        sed 's/\r$//' "$file" \
            | sed -n '/^[[:space:]]*#/d; /^[[:space:]]*PREFIX[[:space:]]*=/p' \
            | tail -n 1
    )
    case $prefix_line in
        *'$(ACD_ROOT)/Compilers/'*)
            if ! ndk_acd_root_resolves "$project" "$acd_root"; then
                echo "NOTE=APOLLOCROSSDEV is not set; this v1.2 Makefile needs it for an out-of-tree project (export APOLLOCROSSDEV=$acd_root)"
            fi
            ;;
        *'$(PWD)/../../Compilers/'*)
            parent=$(CDPATH= cd -- "$project/../.." 2>/dev/null && pwd || true)
            if [ -z "$parent" ] || [ "$parent" != "$acd_root" ]; then
                echo "NOTE=template v1.0 PREFIX=\$(PWD)/../../Compilers/... does not resolve for this project location. Setting APOLLOCROSSDEV does not fix a v1.0 Makefile. Place the project under $acd_root/Projects/<name>, or update ApolloCrossDev for a v1.2+ template that uses ACD_ROOT."
            fi
            ;;
    esac
}


# True when ACD_ROOT in a v1.2-style Makefile can be taken as $acd_root:
# APOLLOCROSSDEV resolves to it, or the project sits two levels below it.
ndk_acd_root_resolves() {
    project=$1
    acd_root=$2
    if [ -n "$APOLLOCROSSDEV" ]; then
        ap=$(CDPATH= cd -- "$APOLLOCROSSDEV" 2>/dev/null && pwd || true)
        [ -n "$ap" ] && [ "$ap" = "$acd_root" ] && return 0
    fi
    parent=$(CDPATH= cd -- "$project/../.." 2>/dev/null && pwd || true)
    [ -n "$parent" ] && [ "$parent" = "$acd_root" ] && return 0
    return 1
}

# Effective compiler install directory, or empty when uncertain.
# Recognises only documented PREFIX shapes; never invents a path from the
# Dev/Stable/Base label alone.
ndk_compiler_root_from_makefile() {
    file=$1
    project=$2
    acd_root=$3
    prefix_line=$(
        sed 's/\r$//' "$file" \
            | sed -n '/^[[:space:]]*#/d; /^[[:space:]]*PREFIX[[:space:]]*=/p' \
            | tail -n 1
    )
    [ -n "$prefix_line" ] || return 0

    variant=""
    case $prefix_line in
        *Compilers/GCC-6.50-Dev*) variant=GCC-6.50-Dev ;;
        *Compilers/GCC-6.50-Stable*) variant=GCC-6.50-Stable ;;
        *Compilers/GCC-6.50-Base*) variant=GCC-6.50-Base ;;
    esac
    [ -n "$variant" ] || return 0

    # v1.2: PREFIX = $(ACD_ROOT)/Compilers/GCC-6.50-...
    case $prefix_line in
        *'$(ACD_ROOT)/Compilers/'*)
            if ndk_acd_root_resolves "$project" "$acd_root"; then
                printf '%s\n' "$acd_root/Compilers/$variant"
            fi
            return 0
            ;;
    esac

    # v1.0: PREFIX = $(PWD)/../../Compilers/GCC-6.50-...
    # Effective only when the project is two levels below the ApolloCrossDev root.
    case $prefix_line in
        *'$(PWD)/../../Compilers/'*)
            parent=$(CDPATH= cd -- "$project/../.." 2>/dev/null && pwd || true)
            if [ -n "$parent" ] && [ "$parent" = "$acd_root" ]; then
                printf '%s\n' "$acd_root/Compilers/$variant"
            fi
            return 0
            ;;
    esac

    return 0
}

# Last uncommented C_INCL_NDK= that names a documented NDK path fragment.
ndk_required_from_makefile() {
    file=$1
    line=$(
        sed 's/\r$//' "$file" \
            | sed -n '/^[[:space:]]*#/d; /^[[:space:]]*C_INCL_NDK[[:space:]]*=/p' \
            | tail -n 1
    )
    case $line in
        *ndk39-include*) printf '%s\n' "3.9" ;;
        *ndk32-include*) printf '%s\n' "3.2" ;;
    esac
}

# Documented template wiring: C_INCL_NDK reaches the compiler through
# C_INCL_ALL and C_FLAGS (ApolloCrossDev v1.0/v1.2), or directly via C_FLAGS.
ndk_incl_feeds_flags() {
    file=$1
    active=$(sed 's/\r$//' "$file" | sed -n '/^[[:space:]]*#/d; p')
    printf '%s\n' "$active" | grep -E '^[[:space:]]*C_FLAGS[[:space:]]*=' | grep -Fq '$(C_INCL_NDK)' && return 0
    printf '%s\n' "$active" | grep -E '^[[:space:]]*C_INCL_ALL[[:space:]]*=' | grep -Fq '$(C_INCL_NDK)' || return 1
    printf '%s\n' "$active" | grep -E '^[[:space:]]*C_FLAGS[[:space:]]*=' | grep -Fq '$(C_INCL_ALL)' || return 1
    return 0
}

# AGENTS.md Target OS only when the value is concrete (no placeholder).
# AmigaOS 3.9 wins as soon as it is listed; otherwise 3.2 / ApolloOS R10 -> 3.2.
ndk_required_from_agents() {
    file=$1
    [ -f "$file" ] || return 0
    line=$(sed 's/\r$//' "$file" | sed -n 's/^[-*][[:space:]]*\*\*Target OS:\*\*[[:space:]]*//p' | head -n 1)
    [ -n "$line" ] || return 0
    case $line in
        *'<'*|*not\ set*|*Not\ set*) return 0 ;;
    esac
    has39=0
    has32=0
    case $line in
        *3.9*) has39=1 ;;
    esac
    case $line in
        *3.2*|*[Aa]pollo[Oo][Ss]*|*R10*) has32=1 ;;
    esac
    if [ $has39 = 1 ]; then
        printf '%s\n' "3.9"
    elif [ $has32 = 1 ]; then
        printf '%s\n' "3.2"
    fi
}

ndk_path_for() {
    compiler_root=$1
    version=$2
    case $version in
        3.9) printf '%s\n' "$compiler_root/m68k-amigaos/ndk39-include" ;;
        3.2) printf '%s\n' "$compiler_root/m68k-amigaos/ndk32-include/Include_H" ;;
    esac
}

ndk_note_absent_under() {
    compiler_root=$1
    path39=$(ndk_path_for "$compiler_root" "3.9")
    path32=$(ndk_path_for "$compiler_root" "3.2")
    absent_note=0
    if [ ! -d "$path39" ]; then
        echo "NOTE=documented NDK 3.9 directory is absent at $path39 (checked under $compiler_root); its use by the active build configuration was not established"
        absent_note=1
    fi
    if [ ! -d "$path32" ]; then
        echo "NOTE=documented NDK 3.2 directory is absent at $path32 (checked under $compiler_root); its use by the active build configuration was not established"
        absent_note=1
    fi
    if [ $absent_note = 1 ] && [ -d "$compiler_root/m68k-amigaos/ndk-include" ]; then
        echo "NOTE=m68k-amigaos/ndk-include exists under $compiler_root and is not a documented NDK substitute (toolchain/target-os-headers.md)"
    fi
}

# Report documented NDK presence. PROBLEM only when the effective compile
# PREFIX and an active wired C_INCL_NDK requirement are both established.
# Never treat ndk-include as OK.
report_ndk() {
    project=$1
    acd_root=$2
    makefile=$project/Makefile
    agents=$project/AGENTS.md
    compiler_root=""
    required=""
    required_how=""
    has_makefile=0
    [ -f "$makefile" ] && has_makefile=1

    if [ $has_makefile = 1 ]; then
        compiler_root=$(ndk_compiler_root_from_makefile "$makefile" "$project" "$acd_root")
        required=$(ndk_required_from_makefile "$makefile")
        if [ -n "$required" ]; then
            if ndk_incl_feeds_flags "$makefile"; then
                required_how="active C_INCL_NDK wired through C_INCL_ALL/C_FLAGS in the project Makefile"
            else
                echo "NOTE=project Makefile has C_INCL_NDK for documented NDK $required, but it is not shown to feed compilation flags through C_INCL_ALL and C_FLAGS (the ApolloCrossDev template shape). Not treating that NDK as an established build requirement. Do not substitute m68k-amigaos/ndk-include."
                required=""
                required_how=""
            fi
        fi
    else
        required=$(ndk_required_from_agents "$agents")
        [ -n "$required" ] && required_how="Target OS in AGENTS.md"
        # Skill default for a Makefile-free build is GCC-6.50-Dev under ACD_ROOT.
        compiler_root=$acd_root/Compilers/GCC-6.50-Dev
    fi

    if [ -z "$compiler_root" ]; then
        if [ -n "$required" ]; then
            echo "NOTE=project requires documented NDK $required ($required_how), but could not establish the effective compiler PREFIX location from the Makefile (recognised shapes: \$(ACD_ROOT)/Compilers/GCC-6.50-Dev|Stable|Base with a resolvable ACD_ROOT, or \$(PWD)/../../Compilers/... when the project is two levels under ApolloCrossDev). Do not infer the path from the Dev/Stable/Base label alone, and do not substitute m68k-amigaos/ndk-include."
        else
            echo "NOTE=could not establish the effective compiler PREFIX location for NDK headers from the project Makefile. Recognised shapes are \$(ACD_ROOT)/Compilers/GCC-6.50-Dev|Stable|Base when ACD_ROOT resolves, or \$(PWD)/../../Compilers/... when the project is two levels under ApolloCrossDev. Documented paths are m68k-amigaos/ndk39-include (NDK 3.9) and m68k-amigaos/ndk32-include/Include_H (NDK 3.2). Do not substitute m68k-amigaos/ndk-include."
        fi
        return
    fi

    if [ -z "$required" ]; then
        ndk_note_absent_under "$compiler_root"
        return
    fi

    path=$(ndk_path_for "$compiler_root" "$required")
    echo "NDK=$required"
    echo "NDK_PATH=$path"
    echo "NDK_COMPILER=$compiler_root"
    if [ -d "$path" ]; then
        echo "NDK_STATUS=present"
        return
    fi
    echo "NDK_STATUS=absent"
    msg="documented NDK $required directory is absent at $path (required by $required_how; checked under $compiler_root)"
    if [ -d "$compiler_root/m68k-amigaos/ndk-include" ]; then
        msg="$msg. m68k-amigaos/ndk-include is present there and is not a documented substitute"
    else
        msg="$msg. Do not substitute m68k-amigaos/ndk-include"
    fi
    problem "$msg"
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
report_apollocrossdev_note "$project" "$root"

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
    report_project_compiler "$project/Makefile" "$project" "$root"
fi

report_ndk "$project" "$root"

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
