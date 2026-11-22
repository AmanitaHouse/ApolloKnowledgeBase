#!/usr/bin/env python3
"""Write the project files for the apollo-new-project skill.

The script creates files that are missing. It never overwrites an existing
file, never runs git, never changes remotes, and never installs software.
A guided AGENTS.md names a Make command only after the supplied Makefile
template has been classified as non-uploading.

The skill runs skills/apollo-new-project/scripts/write-project-files.sh.
This program is the shared implementation (Python standard library only).

Usage:
  python tools/write_project_files.py --project DIR --setup basic
  python tools/write_project_files.py --project DIR --setup guided \\
      --name NAME --what "one sentence" --kind tool \\
      --execution-mode os-friendly --languages C \\
      [--makefile-template PATH] [--claude | --no-claude] \\
      [--kb-url URL]

Guided --languages accepts C, C++, and assembler. Case and surrounding
whitespace do not matter. Combinations are separated by commas, plus
signs, or the words and, or, and and/or. A plus sign that belongs to C++
is not a separator, and a value is not C++ merely because it contains
those characters. Any other name, or an empty value, prints PROBLEM= and
writes no project file. Basic setup ignores --languages and records
"not set yet".

C++ is experimental and os-friendly only. A C++ os-takeover request
prints PROBLEM= and writes nothing. An os-friendly C++ request writes
main.cpp, leaves .c files on the template GCC line, and adds .cpp
discovery compiled with m68k-amigaos-g++. That does not verify
compilation, linkage, or hardware execution. C os-takeover and
assembler-only setup are unchanged.

Default --kb-url is the AmanitaHouse fork. Pass the Apollo Team URL only
when the developer asks for that repository. The URL is recorded in the
optional Claude Code settings; the git submodule itself is added by the
skill, not by this script.
"""
import argparse
import json
import os
import re
import sys

FORK_URL = "https://github.com/AmanitaHouse/ApolloKnowledgeBase"
UPSTREAM_URL = "https://github.com/ApolloTeam-dev/ApolloKnowledgeBase"
KINDS = {"game", "demo", "tool", "application", "library", "device", "datatype"}
MODES = {"os-friendly", "os-takeover"}
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import classify_build  # noqa: E402
import resolve_kb  # noqa: E402

PROJECT_RULE = """---
description: This project targets the Apollo V4. Read ApolloKnowledgeBase/AGENTS.md before changing platform code, and use the akb skills to set up, build, and record lessons.
alwaysApply: false
---

This repository is an Apollo V4 project.

- Read `ApolloKnowledgeBase/AGENTS.md` before writing or changing Apollo code. If that directory is empty, ask for `git submodule update --init ApolloKnowledgeBase` instead of guessing.
- Paths in that file are relative to `ApolloKnowledgeBase/`.
- Use `/apollo-build` before presenting code that must compile. Do not run `make` or `make debug` unless the developer asks: those upload to the V4.
- Use `/akb-lesson` when a milestone is done or an assumption was wrong. Do not publish or submit a lesson until the developer approves the exact text and names the destination.
"""


def fail(message):
    print(f"PROBLEM={message}")
    return 1


def slug_from_url(url):
    text = url.strip().rstrip("/")
    if text.endswith(".git"):
        text = text[:-4]
    parts = text.split("/")
    if len(parts) < 2:
        return None
    return parts[-2] + "/" + parts[-1]


def replace_after(text, prefix, value):
    idx = text.find(prefix)
    if idx < 0:
        raise ValueError(f"template is missing {prefix!r}")
    start = idx + len(prefix)
    if not text.startswith("<", start):
        raise ValueError(f"template has no placeholder after {prefix!r}")
    end = text.find(">", start)
    if end < 0:
        raise ValueError(f"unclosed placeholder after {prefix!r}")
    return text[:start] + value + text[end + 1:]


def fill_agents(template, name, what, kind, mode, languages, areas, build_body, basic, language_block=""):
    text = re.sub(r"<!--.*?-->\n?", "", template, flags=re.S)
    text = replace_after(text, "# AGENTS.md: ", name)
    text = replace_after(text, "- **What it is:** ", what)
    text = replace_after(text, "- **Kind:** ", kind)
    text = replace_after(text, "- **Target core:** ", "the latest core release")
    text = replace_after(
        text, "- **Target model:** ", "any V4 model"
    )
    text = replace_after(
        text,
        "- **Target OS:** ",
        "ApolloOS R10, AmigaOS 3.9 and AmigaOS 3.2",
    )
    text = replace_after(text, "- **Execution mode:** ", mode)
    text = replace_after(text, "- **Languages:** ", languages)
    if basic:
        needle = f"- **Languages:** {languages}\n"
        insert = (
            needle
            + "\nFields marked `not set yet`: ask the developer before relying "
            + "on them, and fill them in.\n"
        )
        if needle not in text:
            raise ValueError("could not place the not-set-yet note")
        text = text.replace(needle, insert, 1)
    elif language_block:
        needle = f"- **Languages:** {languages}\n"
        if needle not in text:
            raise ValueError("could not place the language support notes")
        text = text.replace(
            needle,
            needle + "\n" + language_block.strip("\n") + "\n",
            1,
        )
    area_block = "\n".join(f"- `ApolloKnowledgeBase/{item}`" for item in areas)
    text = re.sub(
        r"## Relevant knowledge base areas\n(?:.*\n)*?(?=## Build and test\n)",
        "## Relevant knowledge base areas\n\n" + area_block + "\n\n",
        text,
        count=1,
    )
    text = re.sub(
        r"```sh\n.*?\n```",
        "```sh\n" + build_body.rstrip("\n") + "\n```",
        text,
        count=1,
        flags=re.S,
    )
    text = text.replace("- <rule>\n", "- None yet.\n", 1)
    if "<" in text or ">" in text:
        raise ValueError("generated AGENTS.md still contains a placeholder")
    return text


SAFE_COMMANDS = ("make compile", "make cleanbefore build")
NO_TEMPLATE_BUILD = (
    "# No Makefile template was supplied.\n"
    "# This file names no build command."
)


def agents_build_body(verdict):
    if verdict.command in SAFE_COMMANDS:
        return (
            verdict.command + "\n"
            "# This command was classified as non-uploading from the Makefile that will be written.\n"
            "# Do not run any other make goal unless the developer asks."
        )
    reason = " ".join(verdict.reason.replace("<", "").replace(">", "").split())
    return (
        "# No Make target was classified as non-uploading.\n"
        "# " + reason + "\n"
        "# This file names no build command."
    )


# A sentinel that cannot appear in a language name. It protects the plus
# signs inside C++ from the combination separator.
_CXX_MARK = "\x00cxx\x00"
_LANGUAGE_ORDER = ("C", "C++", "assembler")
_ACCEPTED_LANGUAGES = "C, C++, and assembler"
_LANGUAGE_SEPARATORS = (
    "separated by commas, plus signs, or the words and, or, and and/or"
)


def _canonical_language(token):
    if token == _CXX_MARK:
        return "C++"
    folded = token.lower().replace(_CXX_MARK, "c++")
    if folded == "c":
        return "C"
    if folded == "c++":
        return "C++"
    if folded == "assembler":
        return "assembler"
    return None


def parse_guided_languages(spec):
    """Return (canonical text, None) or (None, PROBLEM text).

    Canonical text is a subset of "C, C++, assembler" in that order.
    """
    if spec.strip() == "":
        return None, (
            "guided setup needs --languages with one or more of "
            + _ACCEPTED_LANGUAGES
            + " (for example: C). The value was empty."
        )
    protected = re.sub(r"(?i)c\+\+", _CXX_MARK, spec.strip())
    parts = re.split(
        r"\s*(?:,|(?:\band/or\b)|(?:\band\b)|(?:\bor\b)|\+)\s*",
        protected,
        flags=re.IGNORECASE,
    )
    chosen = []
    unknown = []
    for part in parts:
        token = part.strip()
        if token == "":
            return None, (
                "guided setup language has an empty entry. Pass one or more of "
                + _ACCEPTED_LANGUAGES
                + ", "
                + _LANGUAGE_SEPARATORS
                + " (for example: C, assembler)."
            )
        name = _canonical_language(token)
        if name is None:
            unknown.append(token.replace(_CXX_MARK, "C++"))
        elif name not in chosen:
            chosen.append(name)
    if unknown:
        shown = ", ".join(repr(token) for token in unknown)
        return None, (
            "guided setup does not recognize "
            + shown
            + ". Pass one or more of "
            + _ACCEPTED_LANGUAGES
            + ", "
            + _LANGUAGE_SEPARATORS
            + ". A value is not C++ merely because it contains C++."
        )
    ordered = [name for name in _LANGUAGE_ORDER if name in chosen]
    return ", ".join(ordered), None


def project_wildcard(text, suffix):
    """True when an active line wildcards the project's own *.<suffix> sources.

    ApolloLib-only wildcards are not the project's source list. The
    installed ApolloCrossDev v1.0 template and the documented v1.2 template
    collect project *.c and *.s this way, and neither collects *.cpp.
    """
    needle = "*." + suffix
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "wildcard" not in stripped or needle not in stripped:
            continue
        if "$(APOLLOLIB)" in stripped and "SOURCEDIR" not in stripped:
            continue
        return True
    return False


def language_caveat(selected, situation=None):
    """Comment appended to a guided build section for C++ or assembler."""
    cxx = "C++" in selected
    asm = "assembler" in selected
    if not cxx and not asm:
        return None
    if not cxx:
        return (
            "# A non-uploading Make classification does not verify "
            "that an assembler program was generated. The only starter is main.c."
        )
    situation = situation or {}
    claim = "C++ compilation, linkage, or hardware execution"
    if asm:
        claim += ", or that an assembler program was generated"
    lines = [
        "# A non-uploading Make classification does not verify " + claim + "."
    ]
    starter = situation.get("starter", "write")
    makefile = situation.get("makefile", "absent")
    configured = situation.get("configured", False)
    fully = starter == "write" and configured and makefile == "write"
    if fully:
        lines.append("# The starter is main.cpp.")
    elif starter == "keep":
        lines.append("# An existing main.cpp was left unchanged.")
    elif starter == "conflict":
        lines.append("# main.cpp was not written because main.c already exists.")
    if makefile == "preserved":
        lines.append(
            "# An existing Makefile was left unchanged, so .cpp discovery was not added."
        )
    elif makefile == "absent":
        lines.append(
            "# No Makefile template was supplied, so .cpp discovery was not configured."
        )
    elif not fully:
        lines.append(
            "# .cpp discovery was not fully configured in the generated Makefile."
        )
    if asm:
        lines.append("# No assembler starter was written.")
    lines.append(
        "# Generating files does not show that ndk39-include or "
        "ndk32-include/Include_H is installed."
    )
    return "\n".join(lines)


def _cxx_status_notes(situation):
    """Stdout lines for an os-friendly C++ request. situation describes what will be written."""
    situation = situation or {}
    starter = situation.get("starter", "write")
    makefile = situation.get("makefile", "absent")
    configured = situation.get("configured", False)
    notes = []
    if starter == "write":
        notes.append(
            "NOTE=LANGUAGE C++: guided setup wrote main.cpp for this os-friendly project "
            "and did not write main.c."
        )
    elif starter == "keep":
        notes.append(
            "NOTE=LANGUAGE C++: an existing main.cpp was left unchanged. "
            "A second entry point was not written."
        )
    else:
        notes.append(
            "NOTE=LANGUAGE C++: main.c already exists, so main.cpp was not written. "
            "Those names would both produce main.o. C++ setup is incomplete."
        )
    if makefile == "write" and configured:
        notes.append(
            "NOTE=LANGUAGE C++: the generated Makefile discovers project .cpp files and "
            "compiles them with m68k-amigaos-g++. .c files stay on the template GCC "
            "C_COMPILER line. ApolloLib C compilation is unchanged. Assembler rules and "
            "S_FLAGS are unchanged."
        )
    elif makefile == "preserved":
        notes.append(
            "NOTE=LANGUAGE C++: an existing Makefile was left unchanged, so .cpp discovery "
            "was not added. This is not a configured C++ project."
        )
    elif makefile == "absent":
        notes.append(
            "NOTE=LANGUAGE C++: no Makefile template was supplied, so .cpp discovery was "
            "not configured and no Make command is named."
        )
    elif makefile == "write":
        gaps = []
        if situation.get("discovery") not in {"added", "already"}:
            gaps.append("discover project .cpp files")
        if situation.get("rule") not in {"added", "already"}:
            gaps.append("compile them with m68k-amigaos-g++")
        if situation.get("link") not in {"added", "already"}:
            gaps.append("add them to the link prerequisites")
        if not gaps:
            gaps.append("finish the .cpp rules")
        notes.append(
            "NOTE=LANGUAGE C++: the generated Makefile did not "
            + ", ".join(gaps)
            + ". C++ setup is incomplete."
        )
    notes.append(
        "NOTE=LANGUAGE C++: C++ compilation, linkage, and hardware execution are not "
        "verified. A non-uploading Make classification is not that verification."
    )
    notes.append(
        "NOTE=LANGUAGE C++: generating these files does not show that the documented NDK "
        "directories ndk39-include and ndk32-include/Include_H are installed."
    )
    for stem in situation.get("collisions") or []:
        if stem == "main" and starter == "conflict":
            continue
        notes.append(
            "NOTE=CONFLICT basename "
            + stem
            + ": "
            + stem
            + ".c and "
            + stem
            + ".cpp would produce the same object file."
        )
    return notes


def language_notes(selected, template_text, situation=None):
    """Stdout diagnostics. Empty for C, including C combined with nothing else."""
    notes = []
    if "C++" in selected:
        notes.extend(_cxx_status_notes(situation))
    if "assembler" in selected:
        cpp_starter = situation and situation.get("starter") in {"write", "keep"}
        if cpp_starter:
            notes.append(
                "NOTE=LANGUAGE assembler: guided setup does not supply an assembler starter. "
                "main.cpp is the C++ starter, not an assembler program."
            )
        elif situation and situation.get("starter") == "conflict":
            notes.append(
                "NOTE=LANGUAGE assembler: guided setup does not supply an assembler starter. "
                "main.cpp was not written. main.c is not an assembler program."
            )
        else:
            notes.append(
                "NOTE=LANGUAGE assembler: guided setup does not supply an assembler starter. "
                "main.c is the C starter, not an assembler program."
            )
        if template_text is None:
            notes.append(
                "NOTE=LANGUAGE assembler: no Makefile template was supplied, so .s discovery was not established. "
                "S_FLAGS was not changed."
            )
        elif project_wildcard(template_text, "s"):
            notes.append(
                "NOTE=LANGUAGE assembler: this Makefile template discovers .s files. "
                "No assembler source was written and S_FLAGS was not changed."
            )
        else:
            notes.append(
                "NOTE=LANGUAGE assembler: this Makefile template does not discover .s files. "
                "No .s discovery was added and S_FLAGS was not changed."
            )
    return notes


def _markdown_sentence(note):
    """Turn a stdout language note into an AGENTS.md bullet sentence."""
    text = note.split(": ", 1)[1]
    protected = (
        ("main.cpp", "`main.cpp`"),
        ("main.c", "`main.c`"),
        (".cpp files", "`.cpp` files"),
        (".cpp discovery", "`.cpp` discovery"),
        (".c files", "`.c` files"),
        (".s files", "`.s` files"),
        (".s discovery", "`.s` discovery"),
    )
    held = []
    for index, (plain, marked) in enumerate(protected):
        token = f"\ue010{index}\ue011"
        text = text.replace(plain, token)
        held.append((token, marked))
    for plain, marked in (
        ("ndk32-include/Include_H", "`ndk32-include/Include_H`"),
        ("ndk39-include", "`ndk39-include`"),
        ("m68k-amigaos-g++", "`m68k-amigaos-g++`"),
        ("CXX_COMPILER", "`CXX_COMPILER`"),
        ("C_COMPILER", "`C_COMPILER`"),
        ("S_FLAGS", "`S_FLAGS`"),
    ):
        text = text.replace(plain, marked)
    for token, marked in held:
        text = text.replace(token, marked)
    if text:
        text = text[0].upper() + text[1:]
    return text


def agents_language_block(selected, template_text, situation=None):
    """Guidance written into a new AGENTS.md. Empty when the request is C only."""
    if "C++" not in selected and "assembler" not in selected:
        return ""
    if "C++" not in selected:
        bullets = [
            "The Languages line records the request. It does not mean an assembler program was generated."
        ]
        bullets.append(
            "Guided setup does not supply an assembler starter. `main.c` is the C starter, not an assembler program."
        )
        if template_text is None:
            bullets.append(
                "No Makefile template was supplied, so `.s` discovery was not established. `S_FLAGS` was not changed."
            )
        elif project_wildcard(template_text, "s"):
            bullets.append(
                "This Makefile template discovers `.s` files. No assembler source was written and `S_FLAGS` was not changed."
            )
        else:
            bullets.append(
                "This Makefile template does not discover `.s` files. No `.s` discovery was added and `S_FLAGS` was not changed."
            )
        return "Guided setup language support:\n\n" + "\n".join("- " + item for item in bullets)
    if "assembler" in selected:
        intro = (
            "The Languages line records the request. It does not mean C++ compilation, "
            "linkage, or an assembler program was verified."
        )
    else:
        intro = (
            "The Languages line records the request. It does not mean C++ compilation "
            "or linkage was verified."
        )
    bullets = [intro]
    for note in language_notes(selected, template_text, situation):
        if note.startswith("NOTE=LANGUAGE assembler: this Makefile") or note.startswith(
            "NOTE=LANGUAGE assembler: no Makefile"
        ):
            bullets.append(_markdown_sentence(note))
            continue
        if note.startswith("NOTE=LANGUAGE assembler:"):
            bullets.append(_markdown_sentence(note))
            continue
        if note.startswith("NOTE=LANGUAGE C++:"):
            bullets.append(_markdown_sentence(note))
            continue
        if note.startswith("NOTE=CONFLICT "):
            bullets.append(note[len("NOTE=CONFLICT "):])
    return "Guided setup language support:\n\n" + "\n".join("- " + item for item in bullets)


def documented_make_commands(text):
    commands = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "make" or stripped.startswith("make "):
            commands.append(stripped)
    return commands


def report_agents_mismatch(agents_path, verdict):
    with open(agents_path, encoding="utf-8") as fh:
        documented = documented_make_commands(fh.read())
    expected = [verdict.command] if verdict.command in SAFE_COMMANDS else []
    if documented == expected:
        return
    shown = ", ".join(documented) if documented else "none"
    classified = verdict.command if verdict.command in SAFE_COMMANDS else "no verified non-uploading command"
    reason = " ".join(verdict.reason.replace("<", "").replace(">", "").split())
    print(
        "NOTE=existing AGENTS.md was left unchanged and its build command does not match "
        f"the supplied Makefile template: documented {shown}; template classification: {classified}. "
        f"{reason} Update the Build and test section only after reviewing that classification."
    )


def areas_for(setup, mode):
    if setup == "basic":
        return ["toolchain/"]
    rows = ["toolchain/", "toolchain/apollolib/"]
    if mode == "os-takeover":
        rows.extend(["os/os-takeover.md", "core/"])
    else:
        rows.append("os/")
    return rows


def _gpp_assignment(lines):
    """Return (rhs, how) for a G++ path the template itself names.

    Supported ApolloCrossDev v1.0 and v1.2 templates comment a
    m68k-amigaos-g++ C_COMPILER line beside the active GCC line. An
    already-active CXX_COMPILER that names m68k-amigaos-g++ also counts.
    A GCC assignment alone is not enough: this does not invent a G++ path
    by renaming gcc to g++.
    """
    comment = None
    active_cxx = None
    for line in lines:
        stripped = line.strip()
        commented = re.match(r"#\s*C_COMPILER\s*=\s*(.+)$", stripped)
        if commented and "m68k-amigaos-g++" in commented.group(1):
            comment = commented.group(1).strip()
        cxx = re.match(r"CXX_COMPILER\s*=\s*(.+)$", stripped)
        if cxx and not stripped.startswith("#") and "m68k-amigaos-g++" in cxx.group(1):
            active_cxx = cxx.group(1).strip()
    if comment:
        return comment, "comment"
    if active_cxx:
        return active_cxx, "cxx"
    return None, "missing"


CPP_COMPILER_PROBLEM = (
    "C++ Guided setup needs a Makefile template that names m68k-amigaos-g++. "
    "No identifiable G++ assignment was found, so CXX_COMPILER cannot be "
    "established. Guided setup did not write project files. "
    "It does not invent a G++ path from a GCC assignment. "
    "C-only Guided setup is unchanged."
)


def require_cpp_compiler(template_path):
    """Refuse an os-friendly C++ request when G++ is not named by the template."""
    if not template_path:
        return CPP_COMPILER_PROBLEM
    if not os.path.isfile(template_path):
        return f"Makefile template is missing: {template_path}"
    with open(template_path, encoding="utf-8") as fh:
        text = fh.read()
    _, how = _gpp_assignment(text.splitlines())
    if how == "missing":
        return CPP_COMPILER_PROBLEM
    return None


def _existing_cpp_list_name(lines):
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "wildcard" not in stripped or "*.cpp" not in stripped:
            continue
        if "$(APOLLOLIB)" in stripped and "SOURCEDIR" not in stripped:
            continue
        match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*=", stripped)
        if match:
            return match.group(1)
    return None


def _insert_cpp_files(lines):
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.match(r"C_FILES\s*=", stripped):
            lines.insert(index + 1, "CPP_FILES = $(wildcard $(C_SOURCEDIR)/*.cpp)")
            return True
    return False


def _append_cpp_objects(lines, list_name):
    needle = (
        "$(patsubst $(C_SOURCEDIR)/%.cpp,$(C_OBJECTDIR)/%.o,$(" + list_name + "))"
    )
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "patsubst" not in line:
            continue
        if "$(C_SOURCEDIR)/%.c" not in line:
            continue
        if "$(C_SOURCEDIR)/%.cpp" in line:
            return "already"
        lines[index] = line + " " + needle
        return "added"
    return "missing"


def _ensure_cxx_variable(lines, rhs):
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if re.match(r"CXX_COMPILER\s*=", stripped):
            return
    anchor = None
    for index, line in enumerate(lines):
        if re.match(r"#?\s*C_COMPILER\s*=", line.strip()):
            anchor = index
    row = "CXX_COMPILER = " + rhs
    if anchor is None:
        lines.insert(0, row)
    else:
        lines.insert(anchor + 1, row)


_C_RULE = re.compile(r"^\$\(C_OBJECTDIR\)/%\.o\s*:\s*\$\(C_SOURCEDIR\)/%\.c\s*$")
_CPP_RULE = re.compile(r"^\$\(C_OBJECTDIR\)/%\.o\s*:\s*\$\(C_SOURCEDIR\)/%\.cpp\s*$")


def _insert_cpp_rule(lines):
    for line in lines:
        if _CPP_RULE.match(line.strip()):
            return "already"
    for index, line in enumerate(lines):
        if not _C_RULE.match(line.strip()):
            continue
        recipe = []
        cursor = index + 1
        while cursor < len(lines) and lines[cursor].startswith("\t"):
            recipe.append(lines[cursor])
            cursor += 1
        if not recipe:
            return "missing"
        rewritten = []
        replaced = False
        for step in recipe:
            updated = step
            if "$(C_COMPILER)" in step:
                updated = step.replace("$(C_COMPILER)", "$(CXX_COMPILER)")
                replaced = True
            elif "m68k-amigaos-gcc" in step and "m68k-amigaos-g++" not in step:
                updated = step.replace("m68k-amigaos-gcc", "$(CXX_COMPILER)", 1)
                replaced = True
            rewritten.append(updated)
        if not replaced:
            return "missing"
        header = re.sub(r"%\.c\s*$", "%.cpp", line.strip())
        lines[cursor:cursor] = [header] + rewritten
        return "added"
    return "missing"


def add_cpp_rules(text):
    """Add project .cpp discovery without changing the C or assembler rules.

    .c files stay on C_COMPILER. ApolloLib rules are not matched, because
    they use $(APOLLOLIB) rather than $(C_SOURCEDIR). O_LINKER is untouched.
    """
    info = {
        "configured": False,
        "discovery": "missing",
        "link": "missing",
        "rule": "missing",
        "compiler": "missing",
        "notes": [],
    }
    keep_newline = text.endswith("\n")
    lines = text.splitlines()
    rhs, how = _gpp_assignment(lines)
    info["compiler"] = how
    if how == "missing":
        info["notes"].append(
            "NOTE=Makefile template does not name m68k-amigaos-g++; "
            "a G++ compile rule was not added."
        )
    list_name = _existing_cpp_list_name(lines)
    if list_name:
        info["discovery"] = "already"
    elif _insert_cpp_files(lines):
        info["discovery"] = "added"
        list_name = "CPP_FILES"
    else:
        info["notes"].append(
            "NOTE=Makefile template has no C_FILES assignment; "
            "project .cpp files were not added to a source list."
        )
    if list_name:
        info["link"] = _append_cpp_objects(lines, list_name)
        if info["link"] == "missing":
            info["notes"].append(
                "NOTE=Makefile template has no project .c object list; "
                ".cpp objects were not added to the link prerequisites."
            )
    if how != "missing":
        info["rule"] = _insert_cpp_rule(lines)
        if info["rule"] == "added":
            _ensure_cxx_variable(lines, rhs)
        elif info["rule"] == "missing":
            info["notes"].append(
                "NOTE=Makefile template has no project .c compile rule to copy; "
                "a .cpp rule that uses m68k-amigaos-g++ was not added."
            )
    info["configured"] = (
        info["discovery"] in {"added", "already"}
        and info["link"] in {"added", "already"}
        and info["rule"] in {"added", "already"}
    )
    rewritten = "\n".join(lines)
    if keep_newline and not rewritten.endswith("\n"):
        rewritten += "\n"
    return rewritten, info


def adjust_makefile(text, project_name, selected):
    notes = []
    lines = text.splitlines(keepends=True)
    name_done = False
    ndk39 = None
    active_ndk = []
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not name_done and re.match(r"PROJECT_NAME\s*=", stripped):
            newline = "\n" if line.endswith("\n") else ""
            lines[i] = f"PROJECT_NAME = {project_name}{newline}"
            name_done = True
        if "C_INCL_NDK" in line and not stripped.startswith("#") and "C_INCL_NDK" in stripped:
            # commented lines are handled below; this catches the active assignment
            pass
        if re.match(r"#\s*C_INCL_NDK\b", stripped) or re.match(r"C_INCL_NDK\b", stripped):
            if "ndk39-include" in line:
                ndk39 = i
            if re.match(r"C_INCL_NDK\b", stripped):
                active_ndk.append(i)
    if not name_done:
        notes.append("NOTE=Makefile template has no PROJECT_NAME assignment")
    if ndk39 is None:
        notes.append(
            "NOTE=Makefile template has no ndk39-include line; C_INCL_NDK was left unchanged"
        )
    else:
        raw = lines[ndk39]
        newline = "\n" if raw.endswith("\n") else ""
        body = raw[:-1] if raw.endswith("\n") else raw
        body = re.sub(r"^#\s?", "", body, count=1)
        lines[ndk39] = body + newline
        for i in active_ndk:
            if i == ndk39:
                continue
            raw = lines[i]
            newline = "\n" if raw.endswith("\n") else ""
            body = raw[:-1] if raw.endswith("\n") else raw
            if not body.lstrip().startswith("#"):
                lines[i] = "# " + body + newline
    joined = "".join(lines)
    if "C++" not in selected:
        return joined, notes, None
    rewritten, info = add_cpp_rules(joined)
    return rewritten, notes, info


def _source_names(project, suffix):
    found = []
    for name in os.listdir(project):
        path = os.path.join(project, name)
        if os.path.isfile(path) and name.endswith(suffix):
            found.append(name)
    return found


def cpp_starter_decision(project):
    """Decide whether an os-friendly C++ run may write main.cpp.

    Returns (action, collisions). action is write, keep, or conflict.
    collisions lists basenames that already have both a .c and a .cpp file,
    plus main when an existing main.c blocks the starter.
    """
    c_stems = {os.path.splitext(name)[0] for name in _source_names(project, ".c")}
    cpp_names = _source_names(project, ".cpp")
    cpp_stems = {os.path.splitext(name)[0] for name in cpp_names}
    existing = sorted(c_stems & cpp_stems)
    if "main.cpp" in cpp_names:
        return "keep", existing
    if "main" in c_stems:
        return "conflict", sorted(set(existing) | {"main"})
    return "write", existing


def write_new(path, data, created, skipped):
    if os.path.exists(path):
        skipped.append(path)
        print(f"SKIPPED={path} reason=exists")
        return
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(data)
    created.append(path)
    print(f"CREATED={path}")


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--setup", required=True, choices=("basic", "guided"))
    parser.add_argument("--name", default="")
    parser.add_argument("--what", default="")
    parser.add_argument("--kind", default="")
    parser.add_argument("--execution-mode", default="", choices=("", "os-friendly", "os-takeover"))
    parser.add_argument("--languages", default="C")
    parser.add_argument("--makefile-template", default="")
    parser.add_argument("--kb-url", default=FORK_URL)
    parser.add_argument("--claude", dest="claude", action="store_true")
    parser.add_argument("--no-claude", dest="claude", action="store_false")
    parser.set_defaults(claude=True)
    args = parser.parse_args(argv)

    project = os.path.abspath(args.project)
    if not os.path.isdir(project):
        return fail(f"project directory does not exist: {project}")
    name = args.name or os.path.basename(project.rstrip(os.sep))
    if not NAME_RE.fullmatch(name):
        return fail(f"project name must be letters, digits, '-' or '_': {name!r}")

    selected = frozenset()
    if args.setup == "guided":
        if not args.what or not args.kind or not args.execution_mode:
            return fail("guided setup needs --what, --kind, and --execution-mode")
        if args.kind not in KINDS:
            return fail(f"kind must be one of: {', '.join(sorted(KINDS))}")
        if args.execution_mode not in MODES:
            return fail("execution mode must be os-friendly or os-takeover")
        languages, language_problem = parse_guided_languages(args.languages)
        if language_problem:
            return fail(language_problem)
        selected = frozenset(languages.split(", "))
        if "C++" in selected and args.execution_mode == "os-takeover":
            return fail(
                "C++ os-takeover scaffolding is not supported yet. "
                "Guided setup did not write project files. "
                "The experimental C++ starter is os-friendly only. "
                "C os-takeover is unchanged."
            )
        if "C++" in selected and args.execution_mode == "os-friendly":
            compiler_problem = require_cpp_compiler(args.makefile_template)
            if compiler_problem:
                return fail(compiler_problem)
        what, kind, mode = args.what, args.kind, args.execution_mode
        basic = False
    else:
        what = kind = mode = languages = "not set yet"
        build_body = (
            "Not set up yet: use the apollo-build skill when the project gets a Makefile."
        )
        basic = True

    kb_url = args.kb_url.strip()
    if kb_url not in (FORK_URL, UPSTREAM_URL) and slug_from_url(kb_url) is None:
        return fail(f"kb-url is not a repository URL: {kb_url}")
    slug = slug_from_url(kb_url)
    if slug is None:
        return fail(f"kb-url is not a repository URL: {kb_url}")

    makefile_text = None
    makefile_notes = []
    build_verdict = None
    cpp_info = None
    situation = None
    if args.setup == "guided":
        if "C++" in selected and args.execution_mode == "os-friendly":
            action, collisions = cpp_starter_decision(project)
            makefile_state = "absent"
            if args.makefile_template:
                makefile_path = os.path.join(project, "Makefile")
                makefile_state = "preserved" if os.path.exists(makefile_path) else "write"
            situation = {
                "starter": action,
                "makefile": makefile_state,
                "configured": False,
                "collisions": collisions,
            }
        if args.makefile_template:
            if not os.path.isfile(args.makefile_template):
                return fail(f"Makefile template is missing: {args.makefile_template}")
            with open(args.makefile_template, encoding="utf-8") as fh:
                makefile_text = fh.read()
            makefile_text, makefile_notes, cpp_info = adjust_makefile(
                makefile_text, name, selected,
            )
            # Classify the Makefile text that will be written, not the raw
            # template path alone. AGENTS.md must match that content.
            # A non-uploading classification is not C++ or assembler verification.
            build_verdict = classify_build.classify_text(
                makefile_text, args.makefile_template,
            )
            if situation and situation["makefile"] == "preserved":
                build_body = (
                    "# An existing Makefile was left unchanged.\n"
                    "# .cpp discovery was not added. This file names no build command."
                )
                build_verdict = None
            elif situation and situation["makefile"] == "write":
                if cpp_info:
                    situation["configured"] = bool(cpp_info["configured"])
                    situation["discovery"] = cpp_info["discovery"]
                    situation["link"] = cpp_info["link"]
                    situation["rule"] = cpp_info["rule"]
                    situation["compiler"] = cpp_info["compiler"]
                build_body = agents_build_body(build_verdict)
            else:
                build_body = agents_build_body(build_verdict)
        else:
            build_body = NO_TEMPLATE_BUILD
        caveat = language_caveat(selected, situation)
        if caveat:
            build_body += "\n" + caveat

    found = resolve_kb.resolve(project, ROOT)
    resolve_kb.emit(found)
    if not found["ok"]:
        return 1
    kb = found["root"]
    template_path = os.path.join(kb, "templates", "repo", "AGENTS.md")
    claude_path = os.path.join(kb, "templates", "repo", "CLAUDE.md")
    if not os.path.isfile(template_path):
        return fail(f"AGENTS.md template is missing: {template_path}")
    with open(template_path, encoding="utf-8") as fh:
        template = fh.read()
    try:
        language_block = ""
        if args.setup == "guided":
            language_block = agents_language_block(selected, makefile_text, situation)
        agents = fill_agents(
            template, name, what, kind, mode, languages,
            areas_for(args.setup, args.execution_mode), build_body, basic,
            language_block,
        )
    except ValueError as exc:
        return fail(str(exc))

    created, skipped = [], []
    agents_path = os.path.join(project, "AGENTS.md")
    agents_existed = os.path.exists(agents_path)
    write_new(agents_path, agents, created, skipped)
    if agents_existed and build_verdict is not None:
        report_agents_mismatch(agents_path, build_verdict)
    write_new(
        os.path.join(project, ".cursor", "rules", "apollo-v4.mdc"),
        PROJECT_RULE,
        created,
        skipped,
    )
    if args.claude:
        if not os.path.isfile(claude_path):
            return fail(f"CLAUDE.md template is missing: {claude_path}")
        with open(claude_path, encoding="utf-8") as fh:
            claude = fh.read()
        write_new(os.path.join(project, "CLAUDE.md"), claude, created, skipped)
        settings = {
            "extraKnownMarketplaces": {
                "apolloknowledgebase": {
                    "source": {"source": "github", "repo": slug}
                }
            },
            "enabledPlugins": {"akb@apolloknowledgebase": True},
        }
        write_new(
            os.path.join(project, ".claude", "settings.json"),
            json.dumps(settings, indent=2) + "\n",
            created,
            skipped,
        )
    else:
        print("NOTE=Claude Code files were not requested. Cursor does not need them.")

    if args.setup == "guided":
        gitignore = os.path.join(
            ROOT, "skills", "apollo-new-project", "assets", "gitignore"
        )
        targets = (
            "the latest core release, any V4 model, "
            "ApolloOS R10, AmigaOS 3.9 and AmigaOS 3.2"
        )
        cpp_friendly = "C++" in selected and args.execution_mode == "os-friendly"
        if cpp_friendly:
            if situation["starter"] in {"write", "keep"}:
                asset_main = os.path.join(
                    ROOT,
                    "skills",
                    "apollo-new-project",
                    "assets",
                    "main-os-friendly.cpp",
                )
                with open(asset_main, encoding="utf-8") as fh:
                    starter = fh.read()
                starter = (
                    starter.replace("@PROJECT@", name)
                    .replace("@WHAT@", what)
                    .replace("@TARGETS@", targets)
                )
                if "@" in starter:
                    return fail("starting program still contains an @placeholder@")
                write_new(os.path.join(project, "main.cpp"), starter, created, skipped)
        else:
            asset_name = (
                "main-os-takeover.c"
                if args.execution_mode == "os-takeover"
                else "main-os-friendly.c"
            )
            asset_main = os.path.join(
                ROOT, "skills", "apollo-new-project", "assets", asset_name
            )
            with open(asset_main, encoding="utf-8") as fh:
                starter = fh.read()
            starter = (
                starter.replace("@PROJECT@", name)
                .replace("@WHAT@", what)
                .replace("@TARGETS@", targets)
            )
            if "@" in starter:
                return fail("starting program still contains an @placeholder@")
            write_new(os.path.join(project, "main.c"), starter, created, skipped)
        with open(gitignore, encoding="utf-8") as fh:
            ignore = fh.read()
        if not ignore.endswith("\n"):
            ignore += "\n"
        write_new(os.path.join(project, ".gitignore"), ignore, created, skipped)
        if makefile_text is not None:
            for note in makefile_notes:
                print(note)
            if cpp_info and situation and situation["makefile"] == "write":
                for note in cpp_info["notes"]:
                    print(note)
            write_new(os.path.join(project, "Makefile"), makefile_text, created, skipped)
        else:
            print("SKIPPED=Makefile reason=no-template")
        for note in language_notes(selected, makefile_text, situation):
            print(note)

    print(f"SUMMARY created={len(created)} skipped={len(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
