#!/usr/bin/env python3
"""Run the shared skill entry points. This does not load Cursor or Claude Code.

Structural failures exit 1. A missing shell or a missing ApolloCrossDev
install is RESULT ... NOT VERIFIED and does not fail the run. NOT VERIFIED
is not a successful compile and not a loaded plugin session.

The default invocation is fixture-based. It classifies Makefiles and runs
the shared entry points without Make and without the compiler. Pass
--run-toolchain for the authorised real-toolchain probe that may run a
verified non-uploading Make target and a compiler smoke test.

The entry points are the POSIX sh scripts in skills/*/scripts/. They call
the single Python implementation in tools/.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import classify_build  # noqa: E402
import resolve_kb  # noqa: E402

errors = []


def fail(message):
    errors.append(message)
    print(f"FAIL {message}")


def shell_path():
    return shutil.which("sh") or shutil.which("bash")


def posix_script(path):
    """Return a path a POSIX shell can execute.

    A Windows checkout may store the script with CR LF. The committed file
    is LF; this copy is only for the test process. find-acd.sh does not
    locate the repository from its own path, so a temporary copy is safe.
    The skill wrappers do locate the repository from their path and are
    executed in place.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    if b"\r" not in data:
        return path, False
    handle = tempfile.NamedTemporaryFile("wb", suffix=".sh", delete=False)
    handle.write(data.replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
    handle.close()
    os.chmod(handle.name, 0o755)
    return handle.name, True


def run_entry(script_rel, args, env=None):
    """Run a skill entry point that must stay inside the repository tree."""
    shell = shell_path()
    if not shell:
        print(f"RESULT {script_rel} NOT VERIFIED")
        print("REASON=sh is not on PATH, so the skill entry point was not executed")
        return None
    path = os.path.join(ROOT, script_rel)
    script, temporary = posix_script(path)
    try:
        return subprocess.run(
            [shell, script, *args],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
    finally:
        if temporary:
            os.remove(script)


def run_py(args, env=None):
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def check_entry_points():
    before = len(errors)
    pairs = {
        "skills/apollo-new-project/scripts/write-project-files.sh": "tools/write_project_files.py",
        "skills/akb-lesson/scripts/submit-gate.sh": "tools/submit_gate.py",
    }
    for rel, impl in pairs.items():
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            fail(f"missing skill entry point {rel}")
            continue
        text = open(path, encoding="utf-8").read()
        if not text.startswith("#!"):
            fail(f"{rel} has no shebang")
        if impl not in text:
            fail(f"{rel} does not call {impl}")
        if "akb_wsl_reexec" not in text or "tools/wsl_reexec.sh" not in text:
            fail(f"{rel} does not re-exec under WSL when Git Bash has no Python 3")
        if "CLAUDE_" in text or "CURSOR_" in text:
            fail(f"{rel} uses an editor-specific variable")
    find_acd = open(
        os.path.join(ROOT, "skills", "apollo-build", "scripts", "find-acd.sh"),
        encoding="utf-8",
    ).read()
    if "akb_wsl_reexec" not in find_acd or "tools/wsl_reexec.sh" not in find_acd:
        fail("find-acd.sh does not re-exec under WSL from Git Bash")
    for rel in (
        "skills/apollo-new-project/scripts/write-project-files.py",
        "skills/akb-lesson/scripts/submit_gate.py",
    ):
        if os.path.exists(os.path.join(ROOT, rel)):
            fail(f"{rel} duplicates a program that belongs in tools/")
    new_project = open(os.path.join(ROOT, "skills", "apollo-new-project", "SKILL.md"), encoding="utf-8").read()
    lesson = open(os.path.join(ROOT, "skills", "akb-lesson", "SKILL.md"), encoding="utf-8").read()
    build = open(os.path.join(ROOT, "skills", "apollo-build", "SKILL.md"), encoding="utf-8").read()
    if "scripts/write-project-files.sh" not in new_project:
        fail("apollo-new-project does not name scripts/write-project-files.sh")
    if "write-project-files.py" in new_project:
        fail("apollo-new-project still points at a Python file in scripts/")
    if "scripts/submit-gate.sh" not in lesson:
        fail("akb-lesson does not name scripts/submit-gate.sh")
    if "submit_gate.py" in lesson:
        fail("akb-lesson still points at a Python file in scripts/")
    if "gh pr create --repo ApolloTeam-dev/ApolloKnowledgeBase" in lesson:
        fail("akb-lesson still hardcodes the Apollo Team pull-request target")
    for needle in ("SUBMIT=yes", "destination", "git switch --detach", "Do not assume"):
        if needle not in lesson:
            fail(f"akb-lesson is missing the safeguard {needle!r}")
    if "installed Cursor plugin" in build:
        fail("apollo-build still describes the knowledge bundle as Cursor-only")
    # Ban only the unsupported corrected-form claim. Mentioning ([76,sp]) as
    # an unverified example remains allowed.
    if "add.l d2,([76,sp])" in build:
        fail(
            "apollo-build revives the unsupported claim that "
            "add.l d2,([76,sp]) is the pull request #28 corrected form; "
            "toolchain/pitfalls/gcc-double-indirect-stack-slot.md records "
            "add.l d2,([56,sp]) as the bug and move.l (76,sp),a0 under "
            "-fno-double-indirect as the measured workaround"
        )
    if "([56,sp])" not in build or "move.l (76,sp),a0" not in build:
        fail(
            "apollo-build no longer cites the stack-slot pitfall's documented "
            "bug operand and -fno-double-indirect workaround assembly"
        )
    if len(errors) == before:
        print("STATIC shared skill entry points: PASS")


def check_wsl_reexec_helper():
    """Path conversion and the no-op when this shell is not Git Bash.

    The Git Bash hop itself is exercised on a Windows machine. CI is Linux,
    so this test only checks the converter and that an ordinary shell does
    not re-exec.
    """
    before = len(errors)
    shell = shell_path()
    if not os.path.isfile(os.path.join(ROOT, "tools", "wsl_reexec.sh")):
        fail("missing tools/wsl_reexec.sh")
        return
    if not shell:
        print("RESULT wsl-path-helper NOT VERIFIED")
        print("REASON=sh is not on PATH, so tools/wsl_reexec.sh was not executed")
        return
    script = r"""
set -eu
. tools/wsl_reexec.sh
akb_to_wsl_path '/d/Development/per/ApolloKnowledgeBase'
printf '\n'
akb_to_wsl_path 'D:\Development\per\ApolloKnowledgeBase'
printf '\n'
akb_to_wsl_path 'D:/Development/per/ApolloKnowledgeBase'
printf '\n'
akb_to_wsl_path '/mnt/d/already'
printf '\n'
akb_to_wsl_path --setup
printf '\n'
akb_to_wsl_path 'os-friendly'
printf '\n'
set -- keep-me
akb_wsl_reexec /bin/true othe
printf '%s\n' "$1"
"""
    result = subprocess.run(
        [shell, "-c", script],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    expected = (
        "/mnt/d/Development/per/ApolloKnowledgeBase\n"
        "/mnt/d/Development/per/ApolloKnowledgeBase\n"
        "/mnt/d/Development/per/ApolloKnowledgeBase\n"
        "/mnt/d/already\n"
        "--setup\n"
        "os-friendly\n"
        "keep-me\n"
    )
    if result.returncode != 0 or result.stdout != expected:
        fail(
            "wsl path helper returned "
            f"{result.returncode}:\n{result.stdout!r}\nexpected:\n{expected!r}"
        )
    elif len(errors) == before:
        print("WORKFLOW WSL path conversion and no re-exec outside Git Bash: PASS")


def check_resolve():
    before = len(errors)
    bundle = ROOT
    project = tempfile.mkdtemp(prefix="akb-resolve-")
    claude_bundle = tempfile.mkdtemp(prefix="akb-claude-bundle-")
    claude_project = tempfile.mkdtemp(prefix="akb-claude-proj-")
    try:
        absent = resolve_kb.resolve(project, bundle)
        if not absent["ok"] or absent["source"] != "plugin" or os.path.abspath(absent["root"]) != bundle:
            fail(f"project without a submodule should use the plugin bundle, got {absent}")
        empty = os.path.join(project, "ApolloKnowledgeBase")
        os.makedirs(empty)
        with open(os.path.join(project, ".gitmodules"), "w", encoding="utf-8") as fh:
            fh.write('[submodule "ApolloKnowledgeBase"]\n\tpath = ApolloKnowledgeBase\n')
        broken = resolve_kb.resolve(project, bundle)
        if broken["ok"] or broken["source"] is not None or not broken["problems"] or not broken["recovery"]:
            fail(f"uninitialized submodule must not fall back to the plugin, got {broken}")
        os.makedirs(os.path.join(empty, "skills"))
        with open(os.path.join(empty, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write("# AGENTS.md: fixture\n")
        pinned = resolve_kb.resolve(project, bundle)
        if not pinned["ok"] or pinned["source"] != "submodule" or os.path.abspath(pinned["root"]) != os.path.abspath(empty):
            fail(f"initialized submodule must win, got {pinned}")
        os.makedirs(os.path.join(claude_bundle, "skills"))
        os.makedirs(os.path.join(claude_bundle, ".claude-plugin"))
        with open(os.path.join(claude_bundle, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write("# AGENTS.md: claude bundle\n")
        with open(os.path.join(claude_bundle, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as fh:
            fh.write('{"name": "akb"}\n')
        claude = resolve_kb.resolve(claude_project, claude_bundle)
        if (
            not claude["ok"]
            or claude["source"] != "plugin"
            or os.path.abspath(claude["root"]) != os.path.abspath(claude_bundle)
            or os.path.exists(os.path.join(claude_bundle, ".cursor-plugin"))
        ):
            fail(f"a Claude plugin tree without .cursor-plugin must resolve, got {claude}")
        nowhere = tempfile.mkdtemp(prefix="akb-nobundle-")
        try:
            orphan = tempfile.mkdtemp(prefix="akb-emptyproj-")
            try:
                missing = resolve_kb.resolve(orphan, nowhere)
            finally:
                shutil.rmtree(orphan, ignore_errors=True)
            if missing["ok"] or not missing["problems"] or not missing["recovery"]:
                fail(f"missing bundle must explain how to recover, got {missing}")
        finally:
            shutil.rmtree(nowhere, ignore_errors=True)
    finally:
        shutil.rmtree(project, ignore_errors=True)
        shutil.rmtree(claude_bundle, ignore_errors=True)
        shutil.rmtree(claude_project, ignore_errors=True)
    cli = run_py(["tools/resolve_kb.py", ROOT])
    if cli.returncode != 0 or "KB_SOURCE=plugin" not in cli.stdout or f"KB_ROOT={ROOT}" not in cli.stdout:
        fail(f"resolve_kb.py CLI on this checkout failed:\n{cli.stdout}")
    if len(errors) == before:
        print("WORKFLOW knowledge-root resolution: PASS")


def check_scaffold():
    before = len(errors)
    script = "skills/apollo-new-project/scripts/write-project-files.sh"
    basic = tempfile.mkdtemp(prefix="akb-basic-")
    try:
        first = run_entry(script, ["--project", basic, "--setup", "basic", "--no-claude"])
        if first is None:
            return
        if first.returncode != 0:
            fail(f"basic scaffold failed:\n{first.stdout}")
            return
        agents = os.path.join(basic, "AGENTS.md")
        rule = os.path.join(basic, ".cursor", "rules", "apollo-v4.mdc")
        with open(agents, encoding="utf-8") as fh:
            text = fh.read()
        if "not set yet" not in text or "<" in text or "ask the developer" not in text:
            fail("basic AGENTS.md is missing the unset fields or still has a placeholder")
        if not os.path.isfile(rule) or os.path.exists(os.path.join(basic, ".claude", "settings.json")):
            fail("basic --no-claude must write the Cursor rule and not Claude settings")
        if os.path.exists(os.path.join(basic, "main.c")) or os.path.exists(os.path.join(basic, "Makefile")):
            fail("basic setup must not write main.c or a Makefile")
        with open(agents, "w", encoding="utf-8") as fh:
            fh.write("KEEP\n")
        second = run_entry(script, ["--project", basic, "--setup", "basic", "--no-claude"])
        if second is None:
            return
        with open(agents, encoding="utf-8") as fh:
            kept = fh.read()
        if second.returncode != 0 or kept != "KEEP\n" or "SKIPPED=" not in second.stdout:
            fail("scaffold overwrote an existing AGENTS.md or did not skip it")
    finally:
        shutil.rmtree(basic, ignore_errors=True)

    guided = tempfile.mkdtemp(prefix="akb-guided-")
    try:
        template = os.path.join(guided, "template.mk")
        with open(template, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(
                "PROJECT_NAME = <project-name>\n"
                "C_COMPILER = $(PREFIX)/bin/m68k-amigaos-gcc\n"
                "# C_COMPILER = $(PREFIX)/bin/m68k-amigaos-g++\n"
                "# C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk39-include\n"
                "C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk32-include/Include_H\n"
            )
        result = run_entry(script, [
            "--project", guided, "--setup", "guided", "--name", "demo1",
            "--what", "A small test program", "--kind", "tool",
            "--execution-mode", "os-friendly", "--languages", "C",
            "--makefile-template", template,
            "--kb-url", "https://github.com/ApolloTeam-dev/ApolloKnowledgeBase",
        ])
        if result is None:
            return
        if result.returncode != 0:
            fail(f"guided scaffold failed:\n{result.stdout}")
        else:
            with open(os.path.join(guided, "main.c"), encoding="utf-8") as fh:
                main_c = fh.read()
            with open(os.path.join(guided, "Makefile"), encoding="utf-8") as fh:
                makefile = fh.read()
            with open(os.path.join(guided, ".claude", "settings.json"), encoding="utf-8") as fh:
                import json
                settings = json.load(fh)
            repo = settings["extraKnownMarketplaces"]["apolloknowledgebase"]["source"]["repo"]
            if "@" in main_c or "A small test program" not in main_c:
                fail("guided main.c was not filled in")
            if "PROJECT_NAME = demo1" not in makefile:
                fail("Makefile PROJECT_NAME was not set")
            if not re.search(r"(?m)^C_INCL_NDK = \$\(PREFIX\)/\$\(TARGET\)/ndk39-include$", makefile):
                fail("ndk39-include line was not activated")
            if re.search(r"(?m)^C_INCL_NDK = \$\(PREFIX\)/\$\(TARGET\)/ndk32-include", makefile):
                fail("ndk32-include line is still active")
            if repo != "ApolloTeam-dev/ApolloKnowledgeBase":
                fail(f"explicit upstream URL was not recorded, got {repo}")
            with open(os.path.join(guided, "AGENTS.md"), encoding="utf-8") as fh:
                if uncommented_make_commands(fh.read()):
                    fail("an incomplete Makefile template was documented as a safe make command")
            takeover = tempfile.mkdtemp(prefix="akb-takeover-")
            try:
                taken = run_entry(script, [
                    "--project", takeover, "--setup", "guided", "--name", "demo2",
                    "--what", "A takeover test", "--kind", "demo",
                    "--execution-mode", "os-takeover", "--languages", "C", "--no-claude",
                ])
                if taken is None:
                    return
                with open(os.path.join(takeover, "main.c"), encoding="utf-8") as fh:
                    body = fh.read()
                if taken.returncode != 0 or "ApolloTakeOver" not in body or "@" in body:
                    fail("os-takeover starter was not written from its asset")
                with open(os.path.join(takeover, "AGENTS.md"), encoding="utf-8") as fh:
                    agents = fh.read()
                if uncommented_make_commands(agents) or "make compile" in agents:
                    fail("guided setup without a Makefile template documented make compile")
            finally:
                shutil.rmtree(takeover, ignore_errors=True)
    finally:
        shutil.rmtree(guided, ignore_errors=True)

    pinned = tempfile.mkdtemp(prefix="akb-pinned-")
    try:
        sub = os.path.join(pinned, "ApolloKnowledgeBase")
        os.makedirs(os.path.join(sub, "skills"))
        os.makedirs(os.path.join(sub, "templates", "repo"))
        with open(os.path.join(sub, "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write("# AGENTS.md: pinned\n")
        with open(os.path.join(ROOT, "templates", "repo", "AGENTS.md"), encoding="utf-8") as fh:
            template = fh.read()
        with open(os.path.join(sub, "templates", "repo", "AGENTS.md"), "w", encoding="utf-8") as fh:
            fh.write(template + "\nSUBMODULE_TEMPLATE_MARKER\n")
        shutil.copy(
            os.path.join(ROOT, "templates", "repo", "CLAUDE.md"),
            os.path.join(sub, "templates", "repo", "CLAUDE.md"),
        )
        result = run_entry(script, ["--project", pinned, "--setup", "basic"])
        if result is None:
            return
        with open(os.path.join(pinned, "AGENTS.md"), encoding="utf-8") as fh:
            text = fh.read()
        with open(os.path.join(pinned, ".claude", "settings.json"), encoding="utf-8") as fh:
            import json
            settings = json.load(fh)
        repo = settings["extraKnownMarketplaces"]["apolloknowledgebase"]["source"]["repo"]
        if result.returncode != 0 or "KB_SOURCE=submodule" not in result.stdout:
            fail(f"scaffold did not prefer the submodule:\n{result.stdout}")
        elif "SUBMODULE_TEMPLATE_MARKER" not in text:
            fail("scaffold did not read the submodule template")
        elif repo != "ApolloTeam-dev/ApolloKnowledgeBase":
            fail(f"default submodule slug must be Apollo Team, got {repo}")
        bare = tempfile.mkdtemp(prefix="akb-uninit-")
        try:
            os.makedirs(os.path.join(bare, "ApolloKnowledgeBase"))
            blocked = run_entry(script, ["--project", bare, "--setup", "basic", "--no-claude"])
            if blocked is None:
                return
            if blocked.returncode == 0 or "PROBLEM=" not in blocked.stdout:
                fail("scaffold wrote files against an uninitialized submodule")
            if os.path.exists(os.path.join(bare, "AGENTS.md")):
                fail("uninitialized submodule still produced a project AGENTS.md")
        finally:
            shutil.rmtree(bare, ignore_errors=True)
    finally:
        shutil.rmtree(pinned, ignore_errors=True)
    if len(errors) == before:
        print("WORKFLOW project scaffolding: PASS")


def check_find_acd_absent():
    shell = shell_path()
    if not shell:
        print("RESULT find-acd-absent NOT VERIFIED")
        print("REASON=sh is not on PATH, so the ApolloCrossDev check could not be run")
        return
    home = tempfile.mkdtemp(prefix="akb-home-")
    project = os.path.join(tempfile.mkdtemp(prefix="akb-proj-"), "a", "b", "demo")
    os.makedirs(project)
    env = os.environ.copy()
    env["HOME"] = home
    env["APOLLOCROSSDEV"] = ""
    script, temporary = posix_script(os.path.join(ROOT, "skills", "apollo-build", "scripts", "find-acd.sh"))
    result = subprocess.run(
        [shell, script, "--offline", project],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if temporary:
        os.remove(script)
    if result.returncode == 0 or "PROBLEM=" not in result.stdout or "ApolloCrossDev not found" not in result.stdout:
        fail(f"find-acd.sh did not fail clearly when ApolloCrossDev was absent:\n{result.stdout}")
    else:
        print("WORKFLOW find-acd.sh reports a missing ApolloCrossDev and exits non-zero: PASS")
    shutil.rmtree(home, ignore_errors=True)
    shutil.rmtree(os.path.dirname(os.path.dirname(os.path.dirname(project))), ignore_errors=True)


def check_lesson_gate():
    before = len(errors)
    gate = "skills/akb-lesson/scripts/submit-gate.sh"
    folder = tempfile.mkdtemp(prefix="akb-lesson-")
    try:
        draft = os.path.join(folder, "lesson.md")
        approved = os.path.join(folder, "approved.md")
        with open(draft, "w", encoding="utf-8") as fh:
            fh.write("draft\n")
        with open(approved, "w", encoding="utf-8") as fh:
            fh.write("draft\n")
        good = run_entry(gate, ["--draft", draft, "--approved", approved, "--destination", "ExampleOwner/ExampleRepo"])
        if good is None:
            return
        if good.returncode != 0 or "SUBMIT=yes" not in good.stdout:
            fail(f"submit gate rejected a matching draft:\n{good.stdout}")
        with open(approved, "w", encoding="utf-8") as fh:
            fh.write("edited\n")
        bad = run_entry(gate, ["--draft", draft, "--approved", approved, "--destination", "ExampleOwner/ExampleRepo"])
        if bad is None:
            return
        if bad.returncode == 0 or "SUBMIT=no" not in bad.stdout:
            fail("submit gate allowed a draft that differs from the approved text")
        empty = run_entry(gate, ["--draft", draft, "--approved", draft, "--destination", ""])
        if empty is None:
            return
        if empty.returncode == 0:
            fail("submit gate allowed an empty destination")
        if len(errors) == before:
            print("WORKFLOW lesson submit gate: PASS")
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def uncommented_make_commands(text):
    commands = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "make" or stripped.startswith("make "):
            commands.append(stripped)
    return commands


def parse_kv(output):
    found = {}
    for line in output.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            found.setdefault(key, value)
    return found


def smoke_compile(info, project):
    """Compile the starter when the documented NDK is absent.

    Success here is not a guided-build pass. ndk-include is not the path in
    toolchain/target-os-headers.md.
    """
    prefix = info["PREFIX"]
    documented = [
        os.path.join(prefix, "m68k-amigaos", "ndk39-include"),
        os.path.join(prefix, "m68k-amigaos", "ndk32-include", "Include_H"),
    ]
    missing = [path for path in documented if not os.path.isdir(path)]
    fallback = os.path.join(prefix, "m68k-amigaos", "ndk-include")
    gcc = os.path.join(prefix, "bin", "m68k-amigaos-gcc")
    if not missing or not os.path.isdir(fallback) or not os.path.isfile(gcc):
        return
    main_c = os.path.join(project, "main.c")
    output = os.path.join(project, "akbprobe")
    command = [
        gcc, "-noixemul", "-O2", "-m68080", "-m68881", "-ffast-math", "-fomit-frame-pointer",
        "-I.",
        f"-I{os.path.join(prefix, 'm68k-amigaos', 'libnix', 'include')}",
        f"-I{os.path.join(prefix, 'm68k-amigaos', 'sys-include')}",
        f"-I{fallback}",
        main_c, "-o", output,
    ]
    print("RESULT compiler-smoke-command " + " ".join(command))
    print("NOTE=ndk-include is present on this checkout and is not the NDK path documented in toolchain/target-os-headers.md")
    result = subprocess.run(
        command, cwd=project, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    print(result.stdout.rstrip())
    if result.returncode == 0 and not re.search(r"warning:|error:", result.stdout or ""):
        print("RESULT compiler-smoke PASS")
    else:
        print("RESULT compiler-smoke FAIL")


def lines_of(text):
    return text.strip("\n") + "\n"


V12_COMPILE = lines_of("""
# ApolloCrossDev Makefile Template v1.2
PWD = $(shell pwd)
ACD_ROOT ?= $(or $(APOLLOCROSSDEV),$(PWD)/../..)
PREFIX = $(ACD_ROOT)/Compilers/GCC-6.50-Dev
ACP = $(ACD_ROOT)/Projects/ApolloExplorer/acp/acp
APOLLO_V4_HOST = "${AMIGAHOST}:Ram Disk/"
PROJECT_NAME = probe
PROJECT_DIR = $(PWD)
C_COMPILER = $(PREFIX)/bin/m68k-amigaos-gcc
S_COMPILER = $(PREFIX)/bin/vasmm68k_mot
O_LINKER = $(PREFIX)/bin/m68k-amigaos-gcc
C_SOURCEDIR = $(PROJECT_DIR)
S_SOURCEDIR = $(PROJECT_DIR)
C_OBJECTDIR = $(PROJECT_DIR)
S_OBJECTDIR = $(PROJECT_DIR)
C_FILES = $(wildcard $(C_SOURCEDIR)/*.c)
S_FILES = $(wildcard $(S_SOURCEDIR)/*.s)
O_FILES = $(patsubst $(C_SOURCEDIR)/%.c,$(C_OBJECTDIR)/%.o,$(C_FILES)) $(patsubst $(S_SOURCEDIR)/%.s,$(S_OBJECTDIR)/%.o,$(S_FILES))
EXE = $(PROJECT_DIR)/$(PROJECT_NAME)
all: init cleanbefore build upload_all cleanafter exit
compile: init cleanbefore build cleanafter exit
init:
	@clear 2>/dev/null || true
	@echo "start"
cleanbefore:
	@rm -f $(C_OBJECTDIR)/*.o $(EXE)
build: $(EXE)
	@echo "link done"
$(EXE): $(O_FILES)
	@$(O_LINKER) $(O_FILES) -o $(EXE) >>/dev/null
$(C_OBJECTDIR)/%.o: $(C_SOURCEDIR)/%.c
	@$(C_COMPILER) -c -o $@ $< >>/dev/null
$(S_OBJECTDIR)/%.o: $(S_SOURCEDIR)/%.s
	@$(S_COMPILER) -Fhunk -o $@ $< >>/dev/null
upload_all:
	@$(ACP) $(EXE) $(APOLLO_V4_HOST)
cleanafter:
	@rm -f $(C_OBJECTDIR)/*.o
exit:
	@echo "done"
""")

V10_CLEANBEFORE = lines_of("""
# ApolloCrossDev Makefile Template v1.0
PWD = $(shell pwd)
PREFIX = $(PWD)/../../Compilers/GCC-6.50
ACP = $(PWD)/../../Projects/ApolloExplorer/acp/acp
APOLLO_V4_HOST = "${AMIGAHOST}:Ram Disk/"
PROJECT_NAME = probe
PROJECT_DIR = $(PWD)
C_COMPILER = $(PREFIX)/bin/m68k-amigaos-gcc
S_COMPILER = $(PREFIX)/bin/vasmm68k_mot
O_LINKER = $(PREFIX)/bin/m68k-amigaos-gcc
C_SOURCEDIR = $(PROJECT_DIR)
S_SOURCEDIR = $(PROJECT_DIR)
C_OBJECTDIR = $(PROJECT_DIR)
S_OBJECTDIR = $(PROJECT_DIR)
C_FILES = $(wildcard $(C_SOURCEDIR)/*.c)
S_FILES = $(wildcard $(S_SOURCEDIR)/*.s)
O_FILES = $(patsubst $(C_SOURCEDIR)/%.c,$(C_OBJECTDIR)/%.o,$(C_FILES)) $(patsubst $(S_SOURCEDIR)/%.s,$(S_OBJECTDIR)/%.o,$(S_FILES))
EXE = $(PROJECT_DIR)/$(PROJECT_NAME)
all: init cleanbefore build upload cleanafter exit
init:
	clear
	@echo "start"
cleanbefore:
	@rm -f $(C_OBJECTDIR)/*.o $(EXE)
build: $(EXE)
	@echo "link done"
$(EXE): $(O_FILES)
	@$(O_LINKER) $(O_FILES) -o $(EXE) >>$(PROJECT_DIR)/$(PROJECT_NAME)-log.txt 2>>$(PROJECT_DIR)/$(PROJECT_NAME)-log.txt
$(C_OBJECTDIR)/%.o: $(C_SOURCEDIR)/%.c
	@$(C_COMPILER) -c -o $@ $< >>$(PROJECT_DIR)/$(PROJECT_NAME)-log.txt 2>>$(PROJECT_DIR)/$(PROJECT_NAME)-log.txt
$(S_OBJECTDIR)/%.o: $(S_SOURCEDIR)/%.s
	@$(S_COMPILER) -Fhunk -o $@ $< >>/dev/null 2>>$(PROJECT_DIR)/$(PROJECT_NAME)-log.txt
upload:
	@$(ACP) $(EXE) $(APOLLO_V4_HOST)
cleanafter:
	@rm -f $(C_OBJECTDIR)/*.o
exit:
	@echo "done"
""")


def expect_command(name, text, command):
    verdict = classify_build.classify_text(text, name + ".mk")
    if verdict.command != command or verdict.status != "verified-non-uploading":
        fail(f"{name} classified as {verdict.status} {verdict.command}: {verdict.reason}")
        return None
    return verdict


def expect_refused(name, text, status):
    verdict = classify_build.classify_text(text, name + ".mk")
    if verdict.command is not None or verdict.status != status:
        fail(f"{name} classified as {verdict.status} {verdict.command}: {verdict.reason}")
    if verdict.command is not None:
        fail(f"{name} advertised {verdict.command}")
    return verdict


def write_makefile(directory, text, name="Makefile"):
    path = os.path.join(directory, name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def guided_args(project, template=None):
    args = [
        "tools/write_project_files.py",
        "--project", project,
        "--setup", "guided",
        "--name", "probe1",
        "--what", "A classified probe",
        "--kind", "tool",
        "--execution-mode", "os-friendly",
        "--languages", "C",
        "--no-claude",
    ]
    if template:
        args.extend(["--makefile-template", template])
    return args


def check_build_commands():
    """Classify disposable Makefiles. This never runs make."""
    before = len(errors)
    script = open(
        os.path.join(ROOT, "skills", "apollo-build", "scripts", "find-acd.sh"),
        encoding="utf-8",
    ).read()
    if "classify_build.py" not in script:
        fail("find-acd.sh does not use tools/classify_build.py")
    if "build with: make cleanbefore build" in script:
        fail("find-acd.sh still recommends make cleanbefore build unconditionally")
    expect_command("v1.2 compile", V12_COMPILE, "make compile")
    expect_command("v1.0 cleanbefore", V10_CLEANBEFORE, "make cleanbefore build")
    expect_refused(
        "direct upload",
        "cleanbefore:\n\t@rm -f app\nbuild:\n\tacp app host\n",
        "upload-capable",
    )
    expect_refused(
        "upload dependency",
        "cleanbefore:\n\t@rm -f app\nbuild: ship\n\t@echo done\nship:\n\tacp app host\n",
        "upload-capable",
    )
    expect_refused(
        "variable upload",
        "ACP = /opt/ApolloExplorer/acp/acp\ncleanbefore:\n\t@rm -f app\nbuild:\n\t@$(ACP) app host\n",
        "upload-capable",
    )
    expect_refused(
        "recursive upload",
        "cleanbefore:\n\t@echo clean\nbuild:\n\t@$(MAKE) ship\nship:\n\tacp app host\n",
        "upload-capable",
    )
    expect_refused(
        "hidden recursive variable",
        "GO = $(MAKE) ship\nACP = /tools/acp\ncleanbefore:\n\t@echo clean\nbuild:\n\t@$(GO)\nship:\n\t@$(ACP) app host\n",
        "upload-capable",
    )
    expect_refused(
        "recursive other directory",
        "cleanbefore:\n\t@echo clean\nbuild:\n\t@$(MAKE) -C elsewhere\n",
        "unverified",
    )
    expect_refused(
        "recursive other makefile",
        "cleanbefore:\n\t@echo clean\nbuild:\n\t@$(MAKE) -f other.mk compile\n",
        "unverified",
    )
    expect_refused(
        "external shell script",
        "compile:\n\t@./upload.sh probe\n",
        "unverified",
    )
    expect_refused(
        "shell wrapper",
        "compile:\n\t@sh tools/upload.sh probe\n",
        "unverified",
    )
    expect_refused(
        "unfamiliar executable",
        "compile:\n\t@deploy-to-v4 probe\n",
        "unverified",
    )
    expect_refused(
        "command expansion",
        "compile:\n\t@$(UPLOAD_TOOL) probe\n",
        "unverified",
    )
    expect_refused("missing targets", "PROJECT_NAME = probe\n", "unverified")
    expect_refused(
        "duplicate rule",
        "compile:\n\t@echo one\ncompile:\n\t@echo two\n",
        "unverified",
    )
    expect_refused(
        "conditional",
        "ifeq (1,1)\ncompile:\n\t@echo ok\nendif\n",
        "unverified",
    )
    expect_refused(
        "unsupported function",
        "compile:\n\t@echo $(foreach x,a,b)\n",
        "unverified",
    )
    expect_refused(
        "template comment is not evidence",
        "# ApolloCrossDev Makefile Template v1.2\ncompile:\n\tacp app host\n",
        "upload-capable",
    )
    expect_refused(
        "echo recipe hides an upload dependency",
        "compile: build\nbuild: build_step\n\t@echo no acp here\nbuild_step:\n\tacp app host\n",
        "upload-capable",
    )
    folder = tempfile.mkdtemp(prefix="akb-classify-")
    try:
        parent = os.path.join(folder, "with-include.mk")
        with open(parent, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("include missing-rules.mk\ncompile:\n\t@echo ok\n")
        verdict = classify_build.classify_makefile(parent)
        if verdict.command is not None or verdict.status != "unverified":
            fail(f"missing include was classified as {verdict.status} {verdict.command}")
        extra = os.path.join(folder, "extra.mk")
        with open(extra, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("compile: upload\nupload:\n\tacp app host\n")
        main_mk = os.path.join(folder, "main.mk")
        with open(main_mk, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("include extra.mk\n")
        verdict = classify_build.classify_makefile(main_mk)
        if verdict.command is not None or verdict.status != "upload-capable":
            fail(f"included upload was classified as {verdict.status} {verdict.command}: {verdict.reason}")
    finally:
        shutil.rmtree(folder, ignore_errors=True)

    expect_refused(
        "build depends on named upload target",
        "cleanbefore:\n\t@rm -f app\nbuild: upload\n\t@echo linked\nupload:\n\tacp app host\n",
        "upload-capable",
    )

    project = tempfile.mkdtemp(prefix="akb-agents-")
    try:
        safe_template = write_makefile(project, V12_COMPILE, "v12.mk")
        unsafe_template = write_makefile(
            project,
            "cleanbefore:\n\t@rm -f probe1\nbuild:\n\tacp probe1 host\n",
            "unsafe.mk",
        )
        old_template = write_makefile(project, V10_CLEANBEFORE, "v10.mk")
        created = run_py(guided_args(project, safe_template))
        agents_path = os.path.join(project, "AGENTS.md")
        if created.returncode != 0 or not os.path.isfile(agents_path):
            fail(f"guided project with a v1.2 template was not created:\n{created.stdout}")
        else:
            with open(agents_path, encoding="utf-8") as fh:
                agents = fh.read()
            commands = uncommented_make_commands(agents)
            if commands != ["make compile"]:
                fail(f"v1.2 template documented {commands}")
            written = open(os.path.join(project, "Makefile"), encoding="utf-8").read()
            written_verdict = classify_build.classify_text(written, os.path.join(project, "Makefile"))
            if written_verdict.command != "make compile":
                fail(
                    "AGENTS.md documented make compile but the written Makefile "
                    f"classified as {written_verdict.status} {written_verdict.command}"
                )
            if "Makefile that will be written" not in agents:
                fail("AGENTS.md did not say the documented command came from the written Makefile")
            original = open(agents_path, "rb").read()
            again = run_py(guided_args(project, safe_template))
            if open(agents_path, "rb").read() != original:
                fail("a second guided run changed an existing AGENTS.md")
            if "NOTE=existing AGENTS.md was left unchanged" in again.stdout:
                fail("a matching template was reported as a build-command mismatch")
            mismatched = run_py(guided_args(project, unsafe_template))
            if open(agents_path, "rb").read() != original:
                fail("a mismatched template rewrote AGENTS.md")
            if "NOTE=existing AGENTS.md was left unchanged" not in mismatched.stdout:
                fail(f"a mismatched template did not report NOTE=:\n{mismatched.stdout}")
            if "make cleanbefore build" in mismatched.stdout and "BUILD=" in mismatched.stdout:
                fail("mismatch note advertised an unrequested build")
        bare = tempfile.mkdtemp(prefix="akb-notemplate-")
        try:
            bare_run = run_py(guided_args(bare))
            bare_agents = os.path.join(bare, "AGENTS.md")
            if bare_run.returncode != 0 or not os.path.isfile(bare_agents):
                fail(f"guided project without a template failed:\n{bare_run.stdout}")
            else:
                with open(bare_agents, encoding="utf-8") as fh:
                    text = fh.read()
                if uncommented_make_commands(text) or "make compile" in text:
                    fail("guided setup without a template documented a make command")
                if "No Makefile template was supplied." not in text:
                    fail("guided setup without a template did not explain the missing command")
        finally:
            shutil.rmtree(bare, ignore_errors=True)
        older = tempfile.mkdtemp(prefix="akb-v10-")
        try:
            older_run = run_py(guided_args(older, old_template))
            older_agents = os.path.join(older, "AGENTS.md")
            if older_run.returncode != 0 or not os.path.isfile(older_agents):
                fail(f"v1.0 guided project failed:\n{older_run.stdout}")
            else:
                with open(older_agents, encoding="utf-8") as fh:
                    commands = uncommented_make_commands(fh.read())
                if commands != ["make cleanbefore build"]:
                    fail(f"v1.0 template documented {commands}")
        finally:
            shutil.rmtree(older, ignore_errors=True)
        preserved = tempfile.mkdtemp(prefix="akb-preserve-")
        try:
            hand = os.path.join(preserved, "AGENTS.md")
            with open(hand, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("# keep\nmake compile\n")
            before_bytes = open(hand, "rb").read()
            kept = run_py(guided_args(preserved, old_template))
            if open(hand, "rb").read() != before_bytes:
                fail("an existing AGENTS.md was rewritten")
            if kept.returncode != 0 or "NOTE=existing AGENTS.md was left unchanged" not in kept.stdout:
                fail(f"existing make compile was not reported against a v1.0 template:\n{kept.stdout}")
        finally:
            shutil.rmtree(preserved, ignore_errors=True)
    finally:
        shutil.rmtree(project, ignore_errors=True)

    shell = shell_path()
    if not shell:
        print("RESULT find-acd-classify NOT VERIFIED")
        print("REASON=sh is not on PATH, so find-acd.sh was not executed")
    else:
        home = tempfile.mkdtemp(prefix="akb-acd-home-")
        acd = tempfile.mkdtemp(prefix="akb-acd-root-")
        safe_project = tempfile.mkdtemp(prefix="akb-acd-safe-")
        unsafe_project = tempfile.mkdtemp(prefix="akb-acd-unsafe-")
        try:
            os.makedirs(os.path.join(acd, "Compilers"))
            os.makedirs(os.path.join(acd, "Projects", "_makefiles"))
            with open(os.path.join(acd, "Projects", "_makefiles", "Makefile"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(V12_COMPILE)
            write_makefile(safe_project, V12_COMPILE)
            # Safe ApolloCrossDev template, unsafe project Makefile: the
            # project file must decide BUILD=, not the template alone.
            write_makefile(
                unsafe_project,
                "# ApolloCrossDev Makefile Template v1.2\n"
                "compile:\n"
                "\tacp probe host\n",
            )
            env = os.environ.copy()
            env["HOME"] = home
            env["APOLLOCROSSDEV"] = acd
            script_path, temporary = posix_script(
                os.path.join(ROOT, "skills", "apollo-build", "scripts", "find-acd.sh")
            )
            try:
                safe_run = subprocess.run(
                    [shell, script_path, "--offline", safe_project],
                    env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
                )
                unsafe_run = subprocess.run(
                    [shell, script_path, "--offline", unsafe_project],
                    env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
                )
            finally:
                if temporary:
                    os.remove(script_path)
            if "make" in safe_run.args:
                fail("find-acd.sh was invoked with make")
            safe_info = parse_kv(safe_run.stdout)
            if safe_info.get("BUILD") != "make compile":
                fail(f"find-acd.sh did not report the verified command:\n{safe_run.stdout}")
            if "build with: make cleanbefore build" in safe_run.stdout:
                fail("find-acd.sh used the unconditional fallback")
            unsafe_info = parse_kv(unsafe_run.stdout)
            if unsafe_info.get("TEMPLATE") != "v1.2":
                fail(
                    "find-acd.sh did not report the safe ApolloCrossDev template "
                    f"while testing an unsafe project Makefile:\n{unsafe_run.stdout}"
                )
            if unsafe_info.get("MAKEFILE") != "v1.2":
                fail(
                    "find-acd.sh did not report the project Makefile version "
                    f"while testing an unsafe project Makefile:\n{unsafe_run.stdout}"
                )
            if "BUILD" in unsafe_info:
                fail(
                    "find-acd.sh recommended a command from a safe template while "
                    f"the project Makefile uploads:\n{unsafe_run.stdout}"
                )
            if "no Make command can be recommended automatically" not in unsafe_run.stdout:
                fail(f"find-acd.sh did not explain the refused command:\n{unsafe_run.stdout}")
            if "acp" not in unsafe_run.stdout:
                fail(
                    "find-acd.sh refused the project Makefile without naming the "
                    f"upload command:\n{unsafe_run.stdout}"
                )
        finally:
            shutil.rmtree(home, ignore_errors=True)
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(safe_project, ignore_errors=True)
            shutil.rmtree(unsafe_project, ignore_errors=True)
    if len(errors) == before:
        print("WORKFLOW build-command classification: PASS")



def makefile_with_ndk(prefix_variant, ndk_line, template_version="v1.2", prefix_line=None):
    """Disposable ApolloCrossDev-shaped Makefile. Never executed by these tests."""
    if prefix_line is None:
        prefix_line = f"PREFIX = $(ACD_ROOT)/Compilers/{prefix_variant}"
    return lines_of(f"""
# ApolloCrossDev Makefile Template {template_version}
PWD = $(shell pwd)
ACD_ROOT ?= $(or $(APOLLOCROSSDEV),$(PWD)/../..)
{prefix_line}
TARGET = m68k-amigaos
ACP = $(ACD_ROOT)/Projects/ApolloExplorer/acp/acp
APOLLO_V4_HOST = "${{AMIGAHOST}}:Ram Disk/"
PROJECT_NAME = probe
PROJECT_DIR = $(PWD)
C_COMPILER = $(PREFIX)/bin/m68k-amigaos-gcc
S_COMPILER = $(PREFIX)/bin/vasmm68k_mot
O_LINKER = $(PREFIX)/bin/m68k-amigaos-gcc
C_SOURCEDIR = $(PROJECT_DIR)
S_SOURCEDIR = $(PROJECT_DIR)
C_OBJECTDIR = $(PROJECT_DIR)
S_OBJECTDIR = $(PROJECT_DIR)
C_FILES = $(wildcard $(C_SOURCEDIR)/*.c)
S_FILES = $(wildcard $(S_SOURCEDIR)/*.s)
O_FILES = $(patsubst $(C_SOURCEDIR)/%.c,$(C_OBJECTDIR)/%.o,$(C_FILES)) $(patsubst $(S_SOURCEDIR)/%.s,$(S_OBJECTDIR)/%.o,$(S_FILES))
EXE = $(PROJECT_DIR)/$(PROJECT_NAME)
{ndk_line}
C_INCL_ALL = -I. -I$(C_INCL_NDK)
C_FLAGS = $(C_INCL_ALL)
all: init cleanbefore build upload_all cleanafter exit
compile: init cleanbefore build cleanafter exit
init:
	@clear 2>/dev/null || true
	@echo "start"
cleanbefore:
	@rm -f $(C_OBJECTDIR)/*.o $(EXE)
build: $(EXE)
	@echo "link done"
$(EXE): $(O_FILES)
	@$(O_LINKER) $(O_FILES) -o $(EXE) >>/dev/null
$(C_OBJECTDIR)/%.o: $(C_SOURCEDIR)/%.c
	@$(C_COMPILER) $(C_FLAGS) -c -o $@ $< >>/dev/null
$(S_OBJECTDIR)/%.o: $(S_SOURCEDIR)/%.s
	@$(S_COMPILER) -Fhunk -o $@ $< >>/dev/null
upload_all:
	@$(ACP) $(EXE) $(APOLLO_V4_HOST)
cleanafter:
	@rm -f $(C_OBJECTDIR)/*.o
exit:
	@echo "done"
""")


def makefile_v10_relative(ndk_line="C_INCL_NDK  = $(PREFIX)/$(TARGET)/ndk32-include/Include_H\n"):
    """v1.0 relative PREFIX shape. Never executed by these tests."""
    return lines_of(f"""
# ApolloCrossDev Makefile Template v1.0
PWD = $(shell pwd)
PREFIX = $(PWD)/../../Compilers/GCC-6.50-Stable
TARGET = m68k-amigaos
PROJECT_NAME = probe
PROJECT_DIR = $(PWD)
C_COMPILER = $(PREFIX)/bin/m68k-amigaos-gcc
{ndk_line}
C_INCL_ALL = -I. -I$(C_INCL_NDK)
C_FLAGS = $(C_INCL_ALL)
compile: init cleanbefore build cleanafter exit
init:
	@echo start
cleanbefore:
	@rm -f *.o
build:
	@echo link
cleanafter:
	@echo clean
exit:
	@echo done
""")


def make_acd_tree(acd, variants_with_ndk):
    """Create Compilers/<variant>/m68k-amigaos trees. values are ndk dir names to create."""
    os.makedirs(os.path.join(acd, "Compilers"), exist_ok=True)
    os.makedirs(os.path.join(acd, "Projects", "_makefiles"), exist_ok=True)
    with open(os.path.join(acd, "Projects", "_makefiles", "Makefile"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(V12_COMPILE)
    for variant, ndk_names in variants_with_ndk.items():
        base = os.path.join(acd, "Compilers", variant, "m68k-amigaos")
        os.makedirs(base, exist_ok=True)
        for name in ndk_names:
            if name == "ndk32-include/Include_H":
                os.makedirs(os.path.join(base, "ndk32-include", "Include_H"), exist_ok=True)
            else:
                os.makedirs(os.path.join(base, name), exist_ok=True)


def run_find_acd(shell, script_path, project, acd, home):
    env = os.environ.copy()
    env["HOME"] = home
    env["APOLLOCROSSDEV"] = acd
    return subprocess.run(
        [shell, script_path, "--offline", project],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def ndk_problem_lines(output):
    return [line for line in output.splitlines() if line.startswith("PROBLEM=") and "NDK" in line]


def ndk_note_lines(output):
    return [
        line for line in output.splitlines()
        if line.startswith("NOTE=")
        and (
            "NDK" in line
            or "ndk-include" in line
            or "compiler PREFIX" in line
            or "compiler install" in line
            or "feed compilation flags" in line
        )
    ]


def check_ndk_diagnostics():
    """Documented NDK presence under the selected compiler. Never runs make."""
    before = len(errors)
    shell = shell_path()
    if not shell:
        print("RESULT find-acd-ndk NOT VERIFIED")
        print("REASON=sh is not on PATH, so find-acd.sh was not executed")
        return
    script_path, temporary = posix_script(
        os.path.join(ROOT, "skills", "apollo-build", "scripts", "find-acd.sh")
    )
    home = tempfile.mkdtemp(prefix="akb-ndk-home-")
    try:
        # 1. Both documented NDK directories present; active requirement is 3.2.
        acd = tempfile.mkdtemp(prefix="akb-ndk-both-")
        project = tempfile.mkdtemp(prefix="akb-ndk-proj-both-")
        try:
            make_acd_tree(acd, {
                "GCC-6.50-Dev": ["ndk39-include", "ndk32-include/Include_H"],
            })
            write_makefile(
                project,
                makefile_with_ndk(
                    "GCC-6.50-Dev",
                    "C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk32-include/Include_H\n",
                ),
            )
            result = run_find_acd(shell, script_path, project, acd, home)
            info = parse_kv(result.stdout)
            if info.get("NDK") != "3.2" or info.get("NDK_STATUS") != "present":
                fail(f"both-present: expected NDK 3.2 present:\n{result.stdout}")
            if ndk_problem_lines(result.stdout) or any(
                "absent" in line for line in ndk_note_lines(result.stdout)
            ):
                fail(f"both-present: unexpected missing-NDK diagnostics:\n{result.stdout}")
            if "ndk-include" in result.stdout and "substitute" in result.stdout:
                fail(f"both-present: suggested a substitute:\n{result.stdout}")
            expected_path = os.path.join(
                acd, "Compilers", "GCC-6.50-Dev", "m68k-amigaos", "ndk32-include", "Include_H"
            )
            if info.get("NDK_PATH") != expected_path:
                fail(f"both-present: wrong NDK_PATH {info.get('NDK_PATH')!r}, expected {expected_path!r}")
        finally:
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(project, ignore_errors=True)

        # 2. NDK 3.9 absent and is the active requirement.
        acd = tempfile.mkdtemp(prefix="akb-ndk-39miss-")
        project = tempfile.mkdtemp(prefix="akb-ndk-proj-39-")
        try:
            make_acd_tree(acd, {"GCC-6.50-Dev": ["ndk32-include/Include_H"]})
            write_makefile(
                project,
                makefile_with_ndk(
                    "GCC-6.50-Dev",
                    "C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk39-include\n",
                ),
            )
            result = run_find_acd(shell, script_path, project, acd, home)
            info = parse_kv(result.stdout)
            problems = ndk_problem_lines(result.stdout)
            path39 = os.path.join(acd, "Compilers", "GCC-6.50-Dev", "m68k-amigaos", "ndk39-include")
            if info.get("NDK") != "3.9" or info.get("NDK_STATUS") != "absent" or not problems:
                fail(f"ndk39-required-absent: expected PROBLEM:\n{result.stdout}")
            elif path39 not in problems[0]:
                fail(f"ndk39-required-absent: PROBLEM must name {path39}:\n{result.stdout}")
            if result.returncode == 0:
                fail("ndk39-required-absent: exit status must be non-zero")
            if "ndk32-include" in problems[0]:
                fail(f"ndk39-required-absent: PROBLEM blamed NDK 3.2:\n{result.stdout}")
        finally:
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(project, ignore_errors=True)

        # 3. NDK 3.2 absent and is the active requirement.
        acd = tempfile.mkdtemp(prefix="akb-ndk-32miss-")
        project = tempfile.mkdtemp(prefix="akb-ndk-proj-32-")
        try:
            make_acd_tree(acd, {"GCC-6.50-Dev": ["ndk39-include"]})
            write_makefile(
                project,
                makefile_with_ndk(
                    "GCC-6.50-Dev",
                    "C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk32-include/Include_H\n",
                ),
            )
            result = run_find_acd(shell, script_path, project, acd, home)
            info = parse_kv(result.stdout)
            problems = ndk_problem_lines(result.stdout)
            path32 = os.path.join(
                acd, "Compilers", "GCC-6.50-Dev", "m68k-amigaos", "ndk32-include", "Include_H"
            )
            if info.get("NDK") != "3.2" or info.get("NDK_STATUS") != "absent" or not problems:
                fail(f"ndk32-required-absent: expected PROBLEM:\n{result.stdout}")
            elif path32 not in problems[0]:
                fail(f"ndk32-required-absent: PROBLEM must name {path32}:\n{result.stdout}")
            if result.returncode == 0:
                fail("ndk32-required-absent: exit status must be non-zero")
        finally:
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(project, ignore_errors=True)

        # 4. Both documented dirs absent, but ndk-include exists: never a substitute.
        acd = tempfile.mkdtemp(prefix="akb-ndk-fallback-")
        project = tempfile.mkdtemp(prefix="akb-ndk-proj-fb-")
        try:
            make_acd_tree(acd, {"GCC-6.50-Dev": ["ndk-include"]})
            write_makefile(
                project,
                makefile_with_ndk(
                    "GCC-6.50-Dev",
                    "C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk32-include/Include_H\n",
                ),
            )
            result = run_find_acd(shell, script_path, project, acd, home)
            problems = ndk_problem_lines(result.stdout)
            if not problems:
                fail(f"ndk-include-only: expected PROBLEM for documented NDK:\n{result.stdout}")
            joined = "\n".join(problems)
            if "ndk32-include/Include_H" not in joined:
                fail(f"ndk-include-only: must name ndk32-include/Include_H:\n{result.stdout}")
            if "not a documented substitute" not in joined and "Do not substitute" not in joined:
                fail(f"ndk-include-only: must reject ndk-include as substitute:\n{result.stdout}")
            if any("use ndk-include" in line.lower() for line in result.stdout.splitlines()):
                fail(f"ndk-include-only: suggested using ndk-include:\n{result.stdout}")
            if parse_kv(result.stdout).get("NDK_STATUS") != "absent":
                fail(f"ndk-include-only: NDK_STATUS should be absent:\n{result.stdout}")
        finally:
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(project, ignore_errors=True)

        # 5. Required NDK under Dev, absent under selected Stable (v1.2 + APOLLOCROSSDEV).
        acd = tempfile.mkdtemp(prefix="akb-ndk-stable-")
        project = tempfile.mkdtemp(prefix="akb-ndk-proj-stable-")
        try:
            make_acd_tree(acd, {
                "GCC-6.50-Dev": ["ndk32-include/Include_H", "ndk39-include"],
                "GCC-6.50-Stable": ["ndk-include"],
            })
            write_makefile(
                project,
                makefile_with_ndk(
                    "GCC-6.50-Stable",
                    "C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk32-include/Include_H\n",
                ),
            )
            result = run_find_acd(shell, script_path, project, acd, home)
            info = parse_kv(result.stdout)
            problems = ndk_problem_lines(result.stdout)
            stable_root = os.path.join(acd, "Compilers", "GCC-6.50-Stable")
            path32 = os.path.join(stable_root, "m68k-amigaos", "ndk32-include", "Include_H")
            if info.get("NDK_COMPILER") != stable_root:
                fail(f"stable-selected: NDK_COMPILER must be Stable:\n{result.stdout}")
            if "GCC-6.50-Dev" in (info.get("NDK_COMPILER") or ""):
                fail(f"stable-selected: claimed Dev for NDK check:\n{result.stdout}")
            if not problems or path32 not in problems[0]:
                fail(f"stable-selected: expected PROBLEM for Stable path:\n{result.stdout}")
            if result.returncode == 0:
                fail("stable-selected: exit status must be non-zero")
        finally:
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(project, ignore_errors=True)

        # 6. Compiler selection cannot be determined.
        acd = tempfile.mkdtemp(prefix="akb-ndk-unkcomp-")
        project = tempfile.mkdtemp(prefix="akb-ndk-proj-unk-")
        try:
            make_acd_tree(acd, {"GCC-6.50-Dev": []})
            write_makefile(
                project,
                makefile_with_ndk(
                    "GCC-6.50-Dev",
                    "C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk32-include/Include_H\n",
                ).replace(
                    "PREFIX = $(ACD_ROOT)/Compilers/GCC-6.50-Dev",
                    "PREFIX = $(ACD_ROOT)/Compilers/$(COMPILER_VARIANT)",
                ),
            )
            result = run_find_acd(shell, script_path, project, acd, home)
            notes = ndk_note_lines(result.stdout)
            if not any("could not establish the effective compiler PREFIX" in line for line in notes):
                fail(f"unknown-compiler: expected uncertainty NOTE:\n{result.stdout}")
            if ndk_problem_lines(result.stdout):
                fail(f"unknown-compiler: must not invent an NDK PROBLEM:\n{result.stdout}")
            if "NDK_STATUS" in parse_kv(result.stdout):
                fail(f"unknown-compiler: must not claim NDK_STATUS:\n{result.stdout}")
        finally:
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(project, ignore_errors=True)

        # 7. NDK 3.2 absent but active configuration requires only NDK 3.9.
        acd = tempfile.mkdtemp(prefix="akb-ndk-only39-")
        project = tempfile.mkdtemp(prefix="akb-ndk-proj-only39-")
        try:
            make_acd_tree(acd, {"GCC-6.50-Dev": ["ndk39-include"]})
            write_makefile(
                project,
                makefile_with_ndk(
                    "GCC-6.50-Dev",
                    "# C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk32-include/Include_H\n"
                    "C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk39-include\n",
                ),
            )
            result = run_find_acd(shell, script_path, project, acd, home)
            info = parse_kv(result.stdout)
            if info.get("NDK") != "3.9" or info.get("NDK_STATUS") != "present":
                fail(f"only-39-required: expected NDK 3.9 present:\n{result.stdout}")
            if ndk_problem_lines(result.stdout):
                fail(f"only-39-required: missing unused NDK 3.2 must not be PROBLEM:\n{result.stdout}")
            if any("NDK 3.2" in line and "absent" in line for line in ndk_note_lines(result.stdout)):
                fail(f"only-39-required: must not NOTE absent unused NDK 3.2:\n{result.stdout}")
        finally:
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(project, ignore_errors=True)

        # 8. Existing build-command classification remains unchanged.
        acd = tempfile.mkdtemp(prefix="akb-ndk-build-")
        safe_project = tempfile.mkdtemp(prefix="akb-ndk-safe-")
        unsafe_project = tempfile.mkdtemp(prefix="akb-ndk-unsafe-")
        try:
            make_acd_tree(acd, {
                "GCC-6.50-Dev": ["ndk39-include", "ndk32-include/Include_H"],
            })
            write_makefile(safe_project, V12_COMPILE + "C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk32-include/Include_H\n")
            write_makefile(
                unsafe_project,
                "# ApolloCrossDev Makefile Template v1.2\n"
                "PREFIX = $(ACD_ROOT)/Compilers/GCC-6.50-Dev\n"
                "C_INCL_NDK = $(PREFIX)/m68k-amigaos/ndk32-include/Include_H\n"
                "compile:\n"
                "\tacp probe host\n",
            )
            safe_run = run_find_acd(shell, script_path, safe_project, acd, home)
            unsafe_run = run_find_acd(shell, script_path, unsafe_project, acd, home)
            if "make" in safe_run.args:
                fail("ndk-build-classify: find-acd.sh was invoked with make")
            if parse_kv(safe_run.stdout).get("BUILD") != "make compile":
                fail(f"ndk-build-classify: safe BUILD lost:\n{safe_run.stdout}")
            if "BUILD" in parse_kv(unsafe_run.stdout):
                fail(f"ndk-build-classify: unsafe Makefile gained BUILD=:\n{unsafe_run.stdout}")
            if "no Make command can be recommended automatically" not in unsafe_run.stdout:
                fail(f"ndk-build-classify: unsafe refusal missing:\n{unsafe_run.stdout}")
        finally:
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(safe_project, ignore_errors=True)
            shutil.rmtree(unsafe_project, ignore_errors=True)

        # 9. v1.0 project under ApolloCrossDev/Projects/: relative PREFIX -> Stable.
        acd = tempfile.mkdtemp(prefix="akb-ndk-v10in-")
        try:
            make_acd_tree(acd, {
                "GCC-6.50-Dev": ["ndk32-include/Include_H"],
                "GCC-6.50-Stable": [],
            })
            project = os.path.join(acd, "Projects", "probev10")
            os.makedirs(project)
            write_makefile(project, makefile_v10_relative())
            result = run_find_acd(shell, script_path, project, acd, home)
            info = parse_kv(result.stdout)
            stable_root = os.path.join(acd, "Compilers", "GCC-6.50-Stable")
            path32 = os.path.join(stable_root, "m68k-amigaos", "ndk32-include", "Include_H")
            if info.get("NDK_COMPILER") != stable_root:
                fail(f"v10-in-tree: NDK_COMPILER must be Stable under ACD:\n{result.stdout}")
            if info.get("NDK") != "3.2" or info.get("NDK_STATUS") != "absent":
                fail(f"v10-in-tree: expected absent NDK 3.2 under Stable:\n{result.stdout}")
            problems = ndk_problem_lines(result.stdout)
            if not problems or path32 not in problems[0]:
                fail(f"v10-in-tree: PROBLEM must name Stable ndk32 path:\n{result.stdout}")
            if result.returncode == 0:
                fail("v10-in-tree: exit status must be non-zero")
        finally:
            shutil.rmtree(acd, ignore_errors=True)

        # 10. v1.0 project outside ApolloCrossDev: do not invent ACD_ROOT/Compilers/Stable.
        acd = tempfile.mkdtemp(prefix="akb-ndk-v10out-")
        project = tempfile.mkdtemp(prefix="akb-ndk-proj-v10out-")
        try:
            make_acd_tree(acd, {"GCC-6.50-Stable": []})
            write_makefile(project, makefile_v10_relative())
            result = run_find_acd(shell, script_path, project, acd, home)
            notes = ndk_note_lines(result.stdout)
            if not any("could not establish the effective compiler PREFIX" in line for line in notes):
                fail(f"v10-out-of-tree: expected PREFIX uncertainty NOTE:\n{result.stdout}")
            if ndk_problem_lines(result.stdout):
                fail(f"v10-out-of-tree: must not PROBLEM using ACD_ROOT from the Stable label:\n{result.stdout}")
            if "NDK_COMPILER" in parse_kv(result.stdout):
                fail(f"v10-out-of-tree: must not claim NDK_COMPILER:\n{result.stdout}")
        finally:
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(project, ignore_errors=True)

        # 11. v1.2 with APOLLOCROSSDEV: ACD_ROOT-based PREFIX resolves.
        acd = tempfile.mkdtemp(prefix="akb-ndk-v12env-")
        project = tempfile.mkdtemp(prefix="akb-ndk-proj-v12env-")
        try:
            make_acd_tree(acd, {"GCC-6.50-Dev": []})
            write_makefile(
                project,
                makefile_with_ndk(
                    "GCC-6.50-Dev",
                    "C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk32-include/Include_H\n",
                ),
            )
            result = run_find_acd(shell, script_path, project, acd, home)
            info = parse_kv(result.stdout)
            dev_root = os.path.join(acd, "Compilers", "GCC-6.50-Dev")
            if info.get("NDK_COMPILER") != dev_root:
                fail(f"v12-apollocrossdev: NDK_COMPILER must resolve via APOLLOCROSSDEV:\n{result.stdout}")
            if info.get("NDK") != "3.2" or info.get("NDK_STATUS") != "absent":
                fail(f"v12-apollocrossdev: expected established absent NDK 3.2:\n{result.stdout}")
            if not ndk_problem_lines(result.stdout):
                fail(f"v12-apollocrossdev: expected PROBLEM:\n{result.stdout}")
        finally:
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(project, ignore_errors=True)

        # 12. C_INCL_NDK present but not wired into C_FLAGS: informational only.
        acd = tempfile.mkdtemp(prefix="akb-ndk-unwired-")
        project = tempfile.mkdtemp(prefix="akb-ndk-proj-unwired-")
        try:
            make_acd_tree(acd, {"GCC-6.50-Dev": []})
            text = makefile_with_ndk(
                "GCC-6.50-Dev",
                "C_INCL_NDK = $(PREFIX)/$(TARGET)/ndk32-include/Include_H\n",
            )
            text = text.replace(
                "C_INCL_ALL = -I. -I$(C_INCL_NDK)\nC_FLAGS = $(C_INCL_ALL)\n",
                "C_INCL_ALL = -I.\nC_FLAGS = -O2\n",
            )
            write_makefile(project, text)
            result = run_find_acd(shell, script_path, project, acd, home)
            if ndk_problem_lines(result.stdout):
                fail(f"unwired-ndk: must not PROBLEM when C_INCL_NDK is unused:\n{result.stdout}")
            if not any("not shown to feed compilation flags" in line for line in ndk_note_lines(result.stdout)):
                fail(f"unwired-ndk: expected wiring uncertainty NOTE:\n{result.stdout}")
            if parse_kv(result.stdout).get("NDK_STATUS") == "absent":
                fail(f"unwired-ndk: must not claim established NDK_STATUS=absent:\n{result.stdout}")
        finally:
            shutil.rmtree(acd, ignore_errors=True)
            shutil.rmtree(project, ignore_errors=True)
    finally:
        if temporary:
            os.remove(script_path)
        shutil.rmtree(home, ignore_errors=True)
    if len(errors) == before:
        print("WORKFLOW NDK availability diagnostics: PASS")


def check_toolchain():
    shell = shell_path()
    if not shell:
        print("RESULT guided-build NOT VERIFIED")
        print("REASON=sh is not on PATH")
        return
    script, temporary = posix_script(os.path.join(ROOT, "skills", "apollo-build", "scripts", "find-acd.sh"))
    probe = subprocess.run(
        [shell, script, "--offline", tempfile.gettempdir()],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if temporary:
        os.remove(script)
    print("RESULT find-acd-offline")
    print(probe.stdout.rstrip())
    info = parse_kv(probe.stdout)
    if probe.returncode != 0 or "ACD_ROOT" not in info:
        print("RESULT guided-build NOT VERIFIED")
        print("REASON=ApolloCrossDev is not installed in this environment, so no compile was claimed")
        return
    project = tempfile.mkdtemp(prefix="akb-build-")
    try:
        template = os.path.join(info["ACD_ROOT"], "Projects", "_makefiles", "Makefile")
        scaffold = run_entry("skills/apollo-new-project/scripts/write-project-files.sh", [
            "--project", project, "--setup", "guided", "--name", "akbprobe",
            "--what", "Toolchain probe", "--kind", "tool",
            "--execution-mode", "os-friendly", "--languages", "C",
            "--makefile-template", template, "--no-claude",
        ])
        if scaffold is None:
            print("RESULT guided-build NOT VERIFIED")
            print("REASON=the skill entry point could not be executed, so make was not run")
            return
        print(scaffold.stdout.rstrip())
        makefile_path = os.path.join(project, "Makefile")
        if scaffold.returncode != 0 or not os.path.isfile(makefile_path):
            print("RESULT guided-build NOT VERIFIED")
            print("REASON=the guided files were not created, so make was not run")
            return
        verdict = classify_build.classify_makefile(makefile_path)
        if verdict.command not in ("make compile", "make cleanbefore build"):
            print("RESULT guided-build NOT VERIFIED")
            print(
                "REASON=the Makefile has no verified non-uploading target, so make was not run: "
                + verdict.reason
            )
            return
        command = [
            "make",
            *verdict.command.split()[1:],
            f"PREFIX={info['PREFIX']}",
            f"APOLLOLIB={os.path.join(info['ACD_ROOT'], 'Projects', 'ApolloLib')}",
        ]
        env = os.environ.copy()
        env["APOLLOCROSSDEV"] = info["ACD_ROOT"]
        env.setdefault("TERM", "xterm")
        print("RESULT guided-build-command " + " ".join(command))
        built = subprocess.run(
            command,
            cwd=project,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        print(built.stdout.rstrip())
        noisy = re.search(r"warning:|error:|Error|undefined reference|No such file", built.stdout or "")
        exe = os.path.join(project, "akbprobe")
        kind = ""
        file_cmd = shutil.which("file")
        if file_cmd and os.path.isfile(exe):
            shown = subprocess.run(
                [file_cmd, exe], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
            )
            kind = shown.stdout.strip()
            print(kind)
        with open(makefile_path, encoding="utf-8", errors="replace") as fh:
            makefile = fh.read()
        missing_ndk = []
        for line in makefile.splitlines():
            stripped = line.strip()
            if not stripped.startswith("C_INCL_NDK"):
                continue
            match = re.search(r"\$\(TARGET\)/(\S+)", stripped)
            if not match:
                continue
            ndk_path = os.path.join(info["PREFIX"], "m68k-amigaos", *match.group(1).split("/"))
            if not os.path.isdir(ndk_path):
                missing_ndk.append(ndk_path)
        if missing_ndk:
            print("RESULT guided-build NOT VERIFIED")
            print(
                "REASON=the Makefile NDK directory is not in this ApolloCrossDev tree: "
                + "; ".join(missing_ndk)
                + ". toolchain/target-os-headers.md documents ndk39-include and "
                "ndk32-include/Include_H. Headers found through another default path "
                "are not that NDK."
            )
            smoke_compile(info, project)
        elif built.returncode == 0 and not noisy and os.path.isfile(exe) and "executable" in kind.lower():
            print("RESULT guided-build PASS")
        else:
            print("RESULT guided-build NOT VERIFIED")
            print("REASON=the guided Makefile did not finish with no errors and no warnings")
            smoke_compile(info, project)
    finally:
        shutil.rmtree(project, ignore_errors=True)


CPP_STARTER = (
    "NOTE=LANGUAGE C++: guided setup generates a C-style main.c starter, "
    "not a dedicated C++ starter. When compiled with g++, it may be treated as C++ source."
)
CPP_NO_COLLECT = (
    "NOTE=LANGUAGE C++: this Makefile template does not collect .cpp sources. "
    "Add .cpp files to the file lists as toolchain/project-makefile.md describes "
    "before claiming a C++ build."
)
CPP_COLLECTS = (
    "NOTE=LANGUAGE C++: this Makefile template collects .cpp sources. "
    "Guided setup still does not write a dedicated C++ starter."
)
CPP_SELECTED = (
    "NOTE=LANGUAGE C++: C_COMPILER was switched to the template m68k-amigaos-g++ line. "
    "That switch does not verify C++ project generation or compilation, and a "
    "non-uploading Make classification is not that verification."
)
CPP_NOT_VERIFIED = (
    "NOTE=LANGUAGE C++: C++ project generation and compilation are not verified. "
    "A non-uploading Make classification is not that verification."
)
CPP_NO_TEMPLATE_SOURCES = (
    "NOTE=LANGUAGE C++: no Makefile template was supplied, so .cpp sources are not collected. "
    "Add .cpp files to the file lists as toolchain/project-makefile.md describes "
    "before claiming a C++ build."
)
CPP_NO_TEMPLATE_COMPILER = (
    "NOTE=LANGUAGE C++: no Makefile template was supplied, so the m68k-amigaos-g++ "
    "line is absent and C_COMPILER was not switched."
)
ASM_STARTER = (
    "NOTE=LANGUAGE assembler: guided setup does not supply an assembler starter. "
    "main.c is the C starter, not an assembler program."
)
ASM_DISCOVERS = (
    "NOTE=LANGUAGE assembler: this Makefile template discovers .s files. "
    "No assembler source was written and S_FLAGS was not changed."
)
ASM_DOES_NOT = (
    "NOTE=LANGUAGE assembler: this Makefile template does not discover .s files. "
    "No .s discovery was added and S_FLAGS was not changed."
)
ASM_NO_TEMPLATE = (
    "NOTE=LANGUAGE assembler: no Makefile template was supplied, so .s discovery "
    "was not established. S_FLAGS was not changed."
)
GPP_LINE_ABSENT = (
    "NOTE=Makefile template has no commented m68k-amigaos-g++ line; "
    "C_COMPILER was left unchanged"
)
CXX_READY = [CPP_STARTER, CPP_NO_COLLECT, CPP_SELECTED]
ASM_READY = [ASM_STARTER, ASM_DISCOVERS]
CAVEAT_CXX = (
    "# A non-uploading Make classification does not verify "
    "C++ project generation or compilation. The only starter is main.c."
)
CAVEAT_ASM = (
    "# A non-uploading Make classification does not verify "
    "that an assembler program was generated. The only starter is main.c."
)
EMPTY_LANGUAGE = (
    "guided setup needs --languages with one or more of C, C++, and assembler "
    "(for example: C). The value was empty."
)
EMPTY_ENTRY = (
    "guided setup language has an empty entry. Pass one or more of "
    "C, C++, and assembler, separated by commas, plus signs, or the words "
    "and, or, and and/or (for example: C, assembler)."
)


def reject_language(token):
    return (
        "guided setup does not recognize "
        + repr(token)
        + ". Pass one or more of C, C++, and assembler, separated by commas, "
        "plus signs, or the words and, or, and and/or. "
        "A value is not C++ merely because it contains C++."
    )


def with_gpp_line(text):
    old = "C_COMPILER = $(PREFIX)/bin/m68k-amigaos-gcc\n"
    if text.count(old) != 1:
        raise AssertionError("fixture does not have one gcc C_COMPILER line")
    return text.replace(
        old,
        old + "# C_COMPILER = $(PREFIX)/bin/m68k-amigaos-g++\n",
        1,
    )


V10_SHAPE = lines_of("""
# ApolloCrossDev Makefile Template v1.0
PROJECT_NAME = probe
C_COMPILER	= $(PREFIX)/bin/m68k-amigaos-gcc
# C_COMPILER	= $(PREFIX)/bin/m68k-amigaos-g++
C_FILES = $(wildcard $(C_SOURCEDIR)/*.c)
S_FILES = $(wildcard $(S_SOURCEDIR)/*.s)
O_FILES = $(patsubst $(C_SOURCEDIR)/%.c,$(C_OBJECTDIR)/%.o,$(C_FILES)) $(patsubst $(S_SOURCEDIR)/%.s,$(S_OBJECTDIR)/%.o,$(S_FILES))
""")

V12_SHAPE = lines_of("""
# ApolloCrossDev Makefile Template v1.2
PROJECT_NAME = probe
C_COMPILER = $(PREFIX)/bin/m68k-amigaos-gcc
# C_COMPILER = $(PREFIX)/bin/m68k-amigaos-g++
C_FILES = $(wildcard $(C_SOURCEDIR)/*.c)
S_FILES = $(wildcard $(S_SOURCEDIR)/*.s)
LIB_C_FILES = $(if $(APOLLOLIB),$(wildcard $(APOLLOLIB)/*.c))
LIB_S_FILES = $(if $(APOLLOLIB),$(wildcard $(APOLLOLIB)/*.s))
APP_O_FILES = $(patsubst $(C_SOURCEDIR)/%.c,$(C_OBJECTDIR)/%.o,$(C_FILES)) $(patsubst $(S_SOURCEDIR)/%.s,$(S_OBJECTDIR)/%.o,$(S_FILES))
""")

NO_S_SHAPE = lines_of("""
# ApolloCrossDev Makefile Template v1.2
PROJECT_NAME = probe
C_COMPILER = $(PREFIX)/bin/m68k-amigaos-gcc
# C_COMPILER = $(PREFIX)/bin/m68k-amigaos-g++
C_FILES = $(wildcard $(C_SOURCEDIR)/*.c)
LIB_S_FILES = $(if $(APOLLOLIB),$(wildcard $(APOLLOLIB)/*.s))
""")

CPP_COLLECT_SHAPE = lines_of("""
# ApolloCrossDev Makefile Template v1.2
PROJECT_NAME = probe
C_COMPILER = $(PREFIX)/bin/m68k-amigaos-gcc
# C_COMPILER = $(PREFIX)/bin/m68k-amigaos-g++
C_FILES = $(wildcard $(C_SOURCEDIR)/*.c)
CPP_FILES = $(wildcard $(C_SOURCEDIR)/*.cpp)
S_FILES = $(wildcard $(S_SOURCEDIR)/*.s)
""")

CXX_BLOCK = "\n".join([
    "Guided setup language support:",
    "",
    "- The Languages line records the request. It does not mean a C++ program was generated.",
    "- Guided setup generates a C-style `main.c` starter, not a dedicated C++ starter. When compiled with `g++`, it may be treated as C++ source.",
    "- This Makefile template does not collect `.cpp` sources. Before a C++ build can be claimed, add `.cpp` files to the file lists as `ApolloKnowledgeBase/toolchain/project-makefile.md` describes.",
    "- `C_COMPILER` uses the template `m68k-amigaos-g++` line. That switch does not verify C++ project generation or compilation. A non-uploading Make classification is not that verification.",
])

ASM_BLOCK = "\n".join([
    "Guided setup language support:",
    "",
    "- The Languages line records the request. It does not mean an assembler program was generated.",
    "- Guided setup does not supply an assembler starter. `main.c` is the C starter, not an assembler program.",
    "- This Makefile template discovers `.s` files. No assembler source was written and `S_FLAGS` was not changed.",
])

ASM_MISSING_BLOCK = "\n".join([
    "Guided setup language support:",
    "",
    "- The Languages line records the request. It does not mean an assembler program was generated.",
    "- Guided setup does not supply an assembler starter. `main.c` is the C starter, not an assembler program.",
    "- This Makefile template does not discover `.s` files. No `.s` discovery was added and `S_FLAGS` was not changed.",
])


def language_note_lines(output):
    return [line for line in output.splitlines() if line.startswith("NOTE=LANGUAGE")]


def language_section(text):
    marker = "Guided setup language support:\n"
    start = text.find(marker)
    if start < 0:
        return ""
    rest = text[start:]
    end = rest.find("\n## ")
    if end < 0:
        return rest.rstrip("\n")
    return rest[:end].rstrip("\n")


def source_paths(project):
    found = []
    for dirpath, _, files in os.walk(project):
        for name in files:
            if os.path.splitext(name)[1].lower() in {".c", ".cpp", ".cc", ".s", ".asm"}:
                found.append(os.path.relpath(os.path.join(dirpath, name), project).replace("\\", "/"))
    return sorted(found)


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def run_language(languages, template=None, include_languages=True, prep=None, template_path=None):
    root = tempfile.mkdtemp(prefix="akb-lang-")
    project = os.path.join(root, "proj")
    os.makedirs(project)
    if prep:
        prep(project)
    args = [
        "tools/write_project_files.py",
        "--project", project,
        "--setup", "guided",
        "--name", "probe1",
        "--what", "A language probe",
        "--kind", "tool",
        "--execution-mode", "os-friendly",
        "--no-claude",
    ]
    if include_languages:
        args.extend(["--languages", languages])
    if template is not None:
        path = os.path.join(root, "template.mk")
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(template)
        args.extend(["--makefile-template", path])
    elif template_path is not None:
        args.extend(["--makefile-template", template_path])
    result = run_py(args)
    return root, project, result


def assert_problem(label, languages, problem, prep=None, template_path=None):
    root, project, result = run_language(
        languages, prep=prep, template_path=template_path,
    )
    try:
        expected = "PROBLEM=" + problem
        if result.returncode == 0 or result.stdout.strip() != expected:
            fail(
                f"{label} rejection was {result.returncode}:\n{result.stdout!r}\n"
                f"expected:\n{expected!r}"
            )
        if "CREATED=" in result.stdout or "SUMMARY" in result.stdout:
            fail(f"{label} continued after PROBLEM=:\n{result.stdout}")
        if prep is None and os.listdir(project):
            fail(f"{label} wrote {os.listdir(project)} before rejection")
        return project
    finally:
        shutil.rmtree(root, ignore_errors=True)


def assert_c_starter(label, project, template):
    sources = source_paths(project)
    if sources != ["main.c"]:
        fail(f"{label} sources were {sources}")
        return False
    main_c = read_text(os.path.join(project, "main.c"))
    if "int main(void)" not in main_c or "@" in main_c:
        fail(f"{label} main.c is not the C starter")
        return False
    makefile = read_text(os.path.join(project, "Makefile"))
    if "S_FLAGS" in makefile and "S_FLAGS" not in template:
        fail(f"{label} invented S_FLAGS")
        return False
    for name in ("C_FILES", "S_FILES", "LIB_C_FILES", "LIB_S_FILES", "CPP_FILES", "O_LINKER"):
        before = [line for line in template.splitlines() if name in line]
        after = [line for line in makefile.splitlines() if name in line]
        if before != after:
            fail(f"{label} changed {name}:\n{before!r}\n{after!r}")
            return False
    if "PROJECT_NAME = probe1" not in makefile:
        fail(f"{label} did not set PROJECT_NAME")
        return False
    return True


def assert_agents_language(label, project, canonical, section, caveat, command):
    text = read_text(os.path.join(project, "AGENTS.md"))
    if f"- **Languages:** {canonical}" not in text:
        fail(f"{label} Languages line is not {canonical!r}")
        return False
    if language_section(text) != section:
        fail(f"{label} guidance:\n{language_section(text)!r}\nexpected:\n{section!r}")
        return False
    if caveat not in text:
        fail(f"{label} build section omitted the language caveat")
        return False
    if "C++ compilation verified" in text or "assembler program was generated." in text and "does not verify" not in text:
        fail(f"{label} presented the language as verified")
        return False
    commands = uncommented_make_commands(text)
    if commands != command:
        fail(f"{label} documented {commands}, expected {command}")
        return False
    return True


def check_language_selection():
    """Guided language diagnostics. This never runs make."""
    before = len(errors)
    v12_lang = with_gpp_line(V12_COMPILE)
    v10_lang = with_gpp_line(V10_CLEANBEFORE)
    expect_command("v1.2 compile", V12_COMPILE, "make compile")
    expect_command("v1.0 cleanbefore", V10_CLEANBEFORE, "make cleanbefore build")
    expect_command("v1.2 language fixture", v12_lang, "make compile")
    expect_command("v1.0 language fixture", v10_lang, "make cleanbefore build")

    def finish(root):
        shutil.rmtree(root, ignore_errors=True)

    # 1. Default C, including the omitted --languages default.
    for label, include in (("default-c", False), ("explicit-c", True)):
        root, project, result = run_language("C", v12_lang, include_languages=include)
        try:
            if result.returncode != 0:
                fail(f"{label} failed:\n{result.stdout}")
                continue
            if language_note_lines(result.stdout):
                fail(f"{label} printed language warnings:\n{result.stdout}")
            if "NOTE=LANGUAGE" in result.stdout or GPP_LINE_ABSENT in result.stdout:
                fail(f"{label} warned about C++:\n{result.stdout}")
            agents = read_text(os.path.join(project, "AGENTS.md"))
            if language_section(agents) or "does not verify" in agents:
                fail(f"{label} added C++ or assembler guidance")
            if uncommented_make_commands(agents) != ["make compile"]:
                fail(f"{label} changed the safe command")
            makefile = read_text(os.path.join(project, "Makefile"))
            renamed = v12_lang.replace("PROJECT_NAME = probe\n", "PROJECT_NAME = probe1\n", 1)
            if makefile != renamed:
                fail(f"{label} changed more than PROJECT_NAME")
            if not assert_c_starter(label, project, v12_lang):
                continue
            verdict = classify_build.classify_text(makefile, "Makefile")
            if verdict.command != "make compile" or verdict.status != "verified-non-uploading":
                fail(f"{label} reclassified the safe target as {verdict.status} {verdict.command}")
        finally:
            finish(root)

    # 2. C++ only, on a template that can select g++ and does not collect .cpp.
    root, project, result = run_language("  c++  ", v12_lang)
    try:
        if result.returncode != 0:
            fail(f"cxx-only failed:\n{result.stdout}")
        elif language_note_lines(result.stdout) != CXX_READY:
            fail(f"cxx-only notes:\n{language_note_lines(result.stdout)!r}")
        elif GPP_LINE_ABSENT in result.stdout:
            fail("cxx-only reported a missing g++ line that was present")
        else:
            assert_c_starter("cxx-only", project, v12_lang)
            assert_agents_language("cxx-only", project, "C++", CXX_BLOCK, CAVEAT_CXX, ["make compile"])
            makefile = read_text(os.path.join(project, "Makefile"))
            if "\nC_COMPILER = $(PREFIX)/bin/m68k-amigaos-g++\n" not in "\n" + makefile:
                fail("cxx-only did not activate m68k-amigaos-g++")
            if "\n# C_COMPILER = $(PREFIX)/bin/m68k-amigaos-gcc\n" not in "\n" + makefile:
                fail("cxx-only left m68k-amigaos-gcc active")
            verdict = classify_build.classify_text(makefile, "Makefile")
            if verdict.command != "make compile" or verdict.status != "verified-non-uploading":
                fail(f"cxx-only safe command changed to {verdict.status} {verdict.command}")
            if "verified C++" in result.stdout or "verified C++" in read_text(os.path.join(project, "AGENTS.md")):
                fail("cxx-only marked C++ verified")
    finally:
        finish(root)

    # Compiler-selection line absent: reported separately, and C++ stays unverified.
    root, project, result = run_language("C++", V12_COMPILE)
    try:
        if result.returncode != 0:
            fail(f"cxx-no-g++-line failed:\n{result.stdout}")
        else:
            expected = [CPP_STARTER, CPP_NO_COLLECT, CPP_NOT_VERIFIED]
            if language_note_lines(result.stdout) != expected:
                fail(f"cxx-no-g++-line notes:\n{language_note_lines(result.stdout)!r}")
            if GPP_LINE_ABSENT not in result.stdout:
                fail(f"cxx-no-g++-line did not report the missing compiler line:\n{result.stdout}")
            if CPP_SELECTED in result.stdout:
                fail("cxx-no-g++-line claimed g++ was selected")
            makefile = read_text(os.path.join(project, "Makefile"))
            if makefile != V12_COMPILE.replace("PROJECT_NAME = probe\n", "PROJECT_NAME = probe1\n", 1):
                fail("cxx-no-g++-line changed C_COMPILER or another line")
            agents = read_text(os.path.join(project, "AGENTS.md"))
            if "no commented `m68k-amigaos-g++` line" not in agents:
                fail("cxx-no-g++-line guidance did not report the missing line separately")
            if "C++ project generation and compilation are not verified." not in agents:
                fail("cxx-no-g++-line guidance treated the safe target as C++ verification")
    finally:
        finish(root)

    # No template: the missing compiler line is its own note, and main.c is still C.
    root, project, result = run_language("C++")
    try:
        if result.returncode != 0:
            fail(f"cxx-no-template failed:\n{result.stdout}")
        else:
            expected = [CPP_STARTER, CPP_NO_TEMPLATE_SOURCES, CPP_NO_TEMPLATE_COMPILER, CPP_NOT_VERIFIED]
            if language_note_lines(result.stdout) != expected:
                fail(f"cxx-no-template notes:\n{language_note_lines(result.stdout)!r}")
            if os.path.exists(os.path.join(project, "Makefile")):
                fail("cxx-no-template wrote a Makefile")
            agents = read_text(os.path.join(project, "AGENTS.md"))
            if uncommented_make_commands(agents) or "make compile" in agents:
                fail("cxx-no-template documented a make command")
            if "m68k-amigaos-g++` line is absent" not in agents:
                fail("cxx-no-template did not report the absent compiler line")
            if source_paths(project) != ["main.c"]:
                fail(f"cxx-no-template sources were {source_paths(project)}")
    finally:
        finish(root)

    # 3. C and C++. Canonical spelling, same C++ limits, C starter kept.
    root, project, result = run_language("c And   C++", v12_lang)
    try:
        if result.returncode != 0:
            fail(f"c-and-cxx failed:\n{result.stdout}")
        elif language_note_lines(result.stdout) != CXX_READY:
            fail(f"c-and-cxx notes:\n{language_note_lines(result.stdout)!r}")
        else:
            assert_agents_language(
                "c-and-cxx", project, "C, C++", CXX_BLOCK, CAVEAT_CXX, ["make compile"],
            )
            assert_c_starter("c-and-cxx", project, v12_lang)
            if ASM_STARTER in result.stdout:
                fail("c-and-cxx invented an assembler warning")
    finally:
        finish(root)

    # 4. Assembler only. .s discovery is reported; main.c is not the assembler program.
    root, project, result = run_language("  Assembler  ", v12_lang)
    try:
        if result.returncode != 0:
            fail(f"asm-only failed:\n{result.stdout}")
        elif language_note_lines(result.stdout) != ASM_READY:
            fail(f"asm-only notes:\n{language_note_lines(result.stdout)!r}")
        else:
            assert_agents_language(
                "asm-only", project, "assembler", ASM_BLOCK, CAVEAT_ASM, ["make compile"],
            )
            makefile = read_text(os.path.join(project, "Makefile"))
            renamed = v12_lang.replace("PROJECT_NAME = probe\n", "PROJECT_NAME = probe1\n", 1)
            if makefile != renamed:
                fail("asm-only changed the compiler, S_FLAGS, or source lists")
            if "\n# C_COMPILER = $(PREFIX)/bin/m68k-amigaos-g++\n" not in "\n" + makefile:
                fail("asm-only selected g++")
            assert_c_starter("asm-only", project, v12_lang)
            if CPP_STARTER in result.stdout:
                fail("asm-only invented a C++ warning")
    finally:
        finish(root)

    # 5. C and assembler.
    root, project, result = run_language("c,   assembler", v12_lang)
    try:
        if result.returncode != 0:
            fail(f"c-and-asm failed:\n{result.stdout}")
        elif language_note_lines(result.stdout) != ASM_READY:
            fail(f"c-and-asm notes:\n{language_note_lines(result.stdout)!r}")
        else:
            assert_agents_language(
                "c-and-asm", project, "C, assembler", ASM_BLOCK, CAVEAT_ASM, ["make compile"],
            )
            assert_c_starter("c-and-asm", project, v12_lang)
    finally:
        finish(root)

    # C++ and assembler together keep both diagnostics.
    both_notes = CXX_READY + ASM_READY
    both_caveat = (
        "# A non-uploading Make classification does not verify "
        "C++ project generation or compilation, or that an assembler program was generated. "
        "The only starter is main.c."
    )
    root, project, result = run_language("assembler and/or C++", v12_lang)
    try:
        if result.returncode != 0:
            fail(f"cxx-and-asm failed:\n{result.stdout}")
        elif language_note_lines(result.stdout) != both_notes:
            fail(f"cxx-and-asm notes:\n{language_note_lines(result.stdout)!r}")
        else:
            agents = read_text(os.path.join(project, "AGENTS.md"))
            if "- **Languages:** C++, assembler" not in agents:
                fail("cxx-and-asm did not canonicalize language order")
            if both_caveat not in agents:
                fail("cxx-and-asm caveat was missing or overstated")
            if "not a dedicated C++ starter" not in agents or "not an assembler program" not in agents:
                fail("cxx-and-asm guidance presented main.c as the requested language")
            if "When compiled with `g++`, it may be treated as C++ source." not in agents:
                fail("cxx-and-asm guidance omitted the g++ language treatment note")
            assert_c_starter("cxx-and-asm", project, v12_lang)
    finally:
        finish(root)

    # 6. Invalid names, including strings that merely contain C++.
    invalid = {
        "pascal": "pascal",
        "assembly": "assembly",
        "asm": "asm",
        "68080 assembly": "68080 assembly",
        "cpp": "cpp",
        "C++extra": "C++extra",
        "myC++": "myC++",
        "use C++ please": "use C++ please",
        "not C++": "not C++",
    }
    for label, token in invalid.items():
        assert_problem("invalid-" + label, token, reject_language(token), template_path=os.path.join("missing-template.mk"))

    # 7. Empty language selection.
    for label, value in (("empty", ""), ("blank", "   "), ("empty-entry", "C,")):
        problem = EMPTY_LANGUAGE if value.strip() == "" else EMPTY_ENTRY
        assert_problem(label, value, problem)

    # 8. Existing AGENTS.md and sources stay byte-for-byte unchanged.
    seeded = {
        "AGENTS.md": b"KEEP AGENTS\n",
        "main.c": b"KEEP MAIN\n",
        "Makefile": b"KEEP MAKE\nS_FLAGS = untouched\n",
        "already.cpp": b"KEEP CPP\n",
        "start.s": b"KEEP ASM\n",
    }

    def plant(project):
        for name, data in seeded.items():
            with open(os.path.join(project, name), "wb") as fh:
                fh.write(data)

    root, project, result = run_language("C, C++, assembler", v12_lang, prep=plant)
    try:
        if result.returncode != 0:
            fail(f"existing-files failed:\n{result.stdout}")
        else:
            for name, data in seeded.items():
                with open(os.path.join(project, name), "rb") as fh:
                    got = fh.read()
                if got != data:
                    fail(f"existing-files changed {name}: {got!r}")
            if source_paths(project) != ["already.cpp", "main.c", "start.s"]:
                fail(f"existing-files sources became {source_paths(project)}")
            if language_note_lines(result.stdout) != both_notes:
                fail(f"existing-files notes:\n{language_note_lines(result.stdout)!r}")
            if "KEEP AGENTS" not in read_text(os.path.join(project, "AGENTS.md")):
                fail("existing-files rewrote AGENTS.md")
    finally:
        finish(root)

    root, project, result = run_language("pascal", prep=plant)
    try:
        if result.returncode == 0:
            fail("invalid language rewrote an existing project")
        else:
            for name, data in seeded.items():
                with open(os.path.join(project, name), "rb") as fh:
                    if fh.read() != data:
                        fail(f"invalid language changed existing {name}")
            if sorted(os.listdir(project)) != sorted(seeded):
                fail(f"invalid language added files: {os.listdir(project)}")
    finally:
        finish(root)

    # 9. v1.0 and v1.2 shapes: g++ selection, .s discovery, no .cpp collection.
    for label, template, command in (
        ("v12-classified", v12_lang, "make compile"),
        ("v10-classified", v10_lang, "make cleanbefore build"),
    ):
        root, project, result = run_language("C++", template)
        try:
            if result.returncode != 0:
                fail(f"{label} C++ failed:\n{result.stdout}")
                continue
            if language_note_lines(result.stdout) != CXX_READY:
                fail(f"{label} C++ notes:\n{language_note_lines(result.stdout)!r}")
            agents = read_text(os.path.join(project, "AGENTS.md"))
            if uncommented_make_commands(agents) != [command]:
                fail(f"{label} documented {uncommented_make_commands(agents)}")
            if CAVEAT_CXX not in agents:
                fail(f"{label} treated {command} as C++ verification")
            written = read_text(os.path.join(project, "Makefile"))
            verdict = classify_build.classify_text(written, "Makefile")
            if verdict.command != command or verdict.status != "verified-non-uploading":
                fail(f"{label} written Makefile classified as {verdict.status} {verdict.command}")
        finally:
            finish(root)
        root, project, result = run_language("assembler", template)
        try:
            if result.returncode != 0:
                fail(f"{label} assembler failed:\n{result.stdout}")
            elif language_note_lines(result.stdout) != ASM_READY:
                fail(f"{label} assembler notes:\n{language_note_lines(result.stdout)!r}")
        finally:
            finish(root)

    for label, template, active, commented in (
        (
            "v10-shape",
            V10_SHAPE,
            "C_COMPILER\t= $(PREFIX)/bin/m68k-amigaos-g++",
            "# C_COMPILER\t= $(PREFIX)/bin/m68k-amigaos-gcc",
        ),
        (
            "v12-shape",
            V12_SHAPE,
            "C_COMPILER = $(PREFIX)/bin/m68k-amigaos-g++",
            "# C_COMPILER = $(PREFIX)/bin/m68k-amigaos-gcc",
        ),
    ):
        root, project, result = run_language("C++", template)
        try:
            if result.returncode != 0:
                fail(f"{label} failed:\n{result.stdout}")
                continue
            if language_note_lines(result.stdout) != CXX_READY:
                fail(f"{label} notes:\n{language_note_lines(result.stdout)!r}")
            makefile = read_text(os.path.join(project, "Makefile"))
            if active not in makefile.splitlines() or commented not in makefile.splitlines():
                fail(f"{label} did not switch the compiler lines:\n{makefile}")
            if "wildcard $(C_SOURCEDIR)/*.cpp" in makefile or "wildcard $(APOLLOLIB)/*.cpp" in makefile:
                fail(f"{label} invented .cpp collection")
            assert_c_starter(label, project, template)
        finally:
            finish(root)

    root, project, result = run_language("assembler", NO_S_SHAPE)
    try:
        if result.returncode != 0:
            fail(f"no-s-discovery failed:\n{result.stdout}")
        elif language_note_lines(result.stdout) != [ASM_STARTER, ASM_DOES_NOT]:
            fail(f"no-s-discovery notes:\n{language_note_lines(result.stdout)!r}")
        else:
            agents = read_text(os.path.join(project, "AGENTS.md"))
            if language_section(agents) != ASM_MISSING_BLOCK:
                fail(f"no-s-discovery guidance:\n{language_section(agents)!r}")
            if "S_FLAGS" in read_text(os.path.join(project, "Makefile")):
                fail("no-s-discovery invented S_FLAGS")
    finally:
        finish(root)

    root, project, result = run_language("C++", CPP_COLLECT_SHAPE)
    try:
        if result.returncode != 0:
            fail(f"cpp-collect failed:\n{result.stdout}")
        elif language_note_lines(result.stdout) != [CPP_STARTER, CPP_COLLECTS, CPP_SELECTED]:
            fail(f"cpp-collect notes:\n{language_note_lines(result.stdout)!r}")
        elif source_paths(project) != ["main.c"]:
            fail("cpp-collect wrote a C++ starter")
    finally:
        finish(root)

    # 10. Safe build-command classification is unchanged after the language runs.
    expect_command("v1.2 compile after languages", V12_COMPILE, "make compile")
    expect_command("v1.0 cleanbefore after languages", V10_CLEANBEFORE, "make cleanbefore build")
    refused = classify_build.classify_text(
        "cleanbefore:\n\t@rm -f app\nbuild:\n\tacp app host\n",
        "upload.mk",
    )
    if refused.command is not None or refused.status != "upload-capable":
        fail(f"upload refusal changed to {refused.status} {refused.command}")

    # Basic setup keeps "not set yet" and does not take a language.
    for label, value in (("basic-empty", ""), ("basic-blank", "   "), ("basic-pascal", "pascal"), ("basic-cxx", "C++")):
        folder = tempfile.mkdtemp(prefix="akb-lang-basic-")
        try:
            basic = run_py([
                "tools/write_project_files.py",
                "--project", folder,
                "--setup", "basic",
                "--no-claude",
                "--languages", value,
            ])
            if basic.returncode != 0:
                fail(f"{label} failed:\n{basic.stdout}")
                continue
            text = read_text(os.path.join(folder, "AGENTS.md"))
            if "- **Languages:** not set yet" not in text or "ask the developer" not in text:
                fail(f"{label} did not keep the unset language field")
            if os.path.exists(os.path.join(folder, "main.c")) or os.path.exists(os.path.join(folder, "Makefile")):
                fail(f"{label} wrote a starter or Makefile")
            if "NOTE=LANGUAGE" in basic.stdout or "PROBLEM=" in basic.stdout:
                fail(f"{label} applied guided language rules:\n{basic.stdout}")
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    if len(errors) == before:
        print("WORKFLOW guided language selection: PASS")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-toolchain",
        action="store_true",
        help=(
            "run the authorised ApolloCrossDev probe that may invoke a "
            "verified non-uploading Make target and a compiler smoke test"
        ),
    )
    args = parser.parse_args(argv)
    print("SUITE shared-skill-workflows")
    print("NOTE=this runs the shared sh entry points and tools/resolve_kb.py. It does not load Cursor or Claude Code.")
    if args.run_toolchain:
        print("NOTE=--run-toolchain is set: a verified non-uploading Make target may run")
    else:
        print("NOTE=default mode is fixture-only; pass --run-toolchain for a real Make or compiler probe")
    check_entry_points()
    check_wsl_reexec_helper()
    check_resolve()
    check_scaffold()
    check_find_acd_absent()
    check_lesson_gate()
    check_build_commands()
    check_language_selection()
    check_ndk_diagnostics()
    if args.run_toolchain:
        check_toolchain()
    else:
        print("RESULT guided-build SKIPPED")
        print("REASON=pass --run-toolchain to authorise a real Make or compiler probe")
    print(f"{len(errors)} structural problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
