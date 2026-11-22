#!/usr/bin/env python3
"""Run the shared skill entry points. This does not load Cursor or Claude Code.

Structural failures exit 1. A missing shell or a missing ApolloCrossDev
install is RESULT ... NOT VERIFIED and does not fail the run. NOT VERIFIED
is not a successful compile and not a loaded plugin session.

The entry points are the POSIX sh scripts in skills/*/scripts/. They call
the single Python implementation in tools/.
"""
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
akb_wsl_reexec /bin/true other
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
        elif repo != "AmanitaHouse/ApolloKnowledgeBase":
            fail(f"default submodule slug must be the fork, got {repo}")
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


def main():
    print("SUITE shared-skill-workflows")
    print("NOTE=this runs the shared sh entry points and tools/resolve_kb.py. It does not load Cursor or Claude Code.")
    check_entry_points()
    check_wsl_reexec_helper()
    check_resolve()
    check_scaffold()
    check_find_acd_absent()
    check_lesson_gate()
    check_build_commands()
    check_toolchain()
    print(f"{len(errors)} structural problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
