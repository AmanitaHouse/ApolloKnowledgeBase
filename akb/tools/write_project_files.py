#!/usr/bin/env python3
"""Write the project files for the apollo-new-project skill.

The script creates files that are missing. It never overwrites an existing
file, never runs git, never changes remotes, and never installs software.

The skill runs skills/apollo-new-project/scripts/write-project-files.sh.
This program is the shared implementation (Python standard library only).

Usage:
  python tools/write_project_files.py --project DIR --setup basic
  python tools/write_project_files.py --project DIR --setup guided \\
      --name NAME --what "one sentence" --kind tool \\
      --execution-mode os-friendly --languages C \\
      [--makefile-template PATH] [--claude | --no-claude] \\
      [--kb-url URL]

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


def fill_agents(template, name, what, kind, mode, languages, areas, build_body, basic):
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


def areas_for(setup, mode):
    if setup == "basic":
        return ["toolchain/"]
    rows = ["toolchain/", "toolchain/apollolib/"]
    if mode == "os-takeover":
        rows.extend(["os/os-takeover.md", "core/"])
    else:
        rows.append("os/")
    return rows


def adjust_makefile(text, project_name, languages):
    notes = []
    lines = text.splitlines(keepends=True)
    name_done = False
    ndk39 = None
    active_ndk = []
    gcc_line = None
    gpp_line = None
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
        if re.match(r"C_COMPILER\s*=", stripped) and "g++" not in line:
            gcc_line = i
        if re.match(r"#\s*C_COMPILER\s*=", stripped) and "g++" in line:
            gpp_line = i
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
    wants_cxx = "C++" in languages or "c++" in languages
    if wants_cxx:
        if gpp_line is None or gcc_line is None:
            notes.append(
                "NOTE=Makefile template has no commented m68k-amigaos-g++ line; C_COMPILER was left unchanged"
            )
        else:
            raw = lines[gpp_line]
            newline = "\n" if raw.endswith("\n") else ""
            body = raw[:-1] if raw.endswith("\n") else raw
            lines[gpp_line] = re.sub(r"^#\s?", "", body, count=1) + newline
            raw = lines[gcc_line]
            newline = "\n" if raw.endswith("\n") else ""
            body = raw[:-1] if raw.endswith("\n") else raw
            if not body.lstrip().startswith("#"):
                lines[gcc_line] = "# " + body + newline
    return "".join(lines), notes


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

    if args.setup == "guided":
        if not args.what or not args.kind or not args.execution_mode:
            return fail("guided setup needs --what, --kind, and --execution-mode")
        if args.kind not in KINDS:
            return fail(f"kind must be one of: {', '.join(sorted(KINDS))}")
        if args.execution_mode not in MODES:
            return fail("execution mode must be os-friendly or os-takeover")
        what, kind, mode, languages = args.what, args.kind, args.execution_mode, args.languages
        build_body = (
            "make compile\n"
            "# make uploads to the V4 at $AMIGAHOST. Run it only when the developer asks."
        )
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
        agents = fill_agents(
            template, name, what, kind, mode, languages,
            areas_for(args.setup, args.execution_mode), build_body, basic,
        )
    except ValueError as exc:
        return fail(str(exc))

    created, skipped = [], []
    write_new(os.path.join(project, "AGENTS.md"), agents, created, skipped)
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
        asset_main = os.path.join(
            ROOT,
            "skills",
            "apollo-new-project",
            "assets",
            "main-os-takeover.c" if args.execution_mode == "os-takeover" else "main-os-friendly.c",
        )
        gitignore = os.path.join(
            ROOT, "skills", "apollo-new-project", "assets", "gitignore"
        )
        with open(asset_main, encoding="utf-8") as fh:
            main_c = fh.read()
        targets = (
            "the latest core release, any V4 model, "
            "ApolloOS R10, AmigaOS 3.9 and AmigaOS 3.2"
        )
        main_c = (
            main_c.replace("@PROJECT@", name)
            .replace("@WHAT@", what)
            .replace("@TARGETS@", targets)
        )
        if "@" in main_c:
            return fail("starting program still contains an @placeholder@")
        write_new(os.path.join(project, "main.c"), main_c, created, skipped)
        with open(gitignore, encoding="utf-8") as fh:
            ignore = fh.read()
        if not ignore.endswith("\n"):
            ignore += "\n"
        write_new(os.path.join(project, ".gitignore"), ignore, created, skipped)
        if args.makefile_template:
            if not os.path.isfile(args.makefile_template):
                return fail(f"Makefile template is missing: {args.makefile_template}")
            with open(args.makefile_template, encoding="utf-8") as fh:
                makefile = fh.read()
            makefile, notes = adjust_makefile(makefile, name, languages)
            for note in notes:
                print(note)
            write_new(os.path.join(project, "Makefile"), makefile, created, skipped)
        else:
            print("SKIPPED=Makefile reason=no-template")

    print(f"SUMMARY created={len(created)} skipped={len(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
