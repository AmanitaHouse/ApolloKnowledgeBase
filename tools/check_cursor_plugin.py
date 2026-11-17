#!/usr/bin/env python3
"""Static checks for the Cursor plugin manifests and the project rule.

This does not load Cursor, does not run the skills, and does not compile.
Workflow execution is tools/check_shared_workflows.py. A passing run here
is not evidence that a skill ran inside Cursor.
"""
import json
import os
import re
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

FORK_REPO = "https://github.com/AmanitaHouse/ApolloKnowledgeBase"
NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
MARKET_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

errors = []


def fail(message):
    errors.append(message)
    print(f"FAIL {message}")


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def frontmatter_block(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None
    return yaml.safe_load(match.group(1))


def check_manifests():
    plugin_path = os.path.join(ROOT, ".cursor-plugin", "plugin.json")
    market_path = os.path.join(ROOT, ".cursor-plugin", "marketplace.json")
    try:
        plugin = load_json(plugin_path)
        market = load_json(market_path)
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"manifest JSON: {exc}")
        return
    if plugin.get("name") != "akb" or not NAME_RE.fullmatch(plugin.get("name", "")):
        fail("plugin.json name must be akb")
    if not SEMVER_RE.fullmatch(str(plugin.get("version", ""))):
        fail("plugin.json version must be semantic")
    if not plugin.get("description"):
        fail("plugin.json description is empty")
    if plugin.get("repository") != FORK_REPO:
        fail(f"plugin.json repository must be {FORK_REPO}")
    author = plugin.get("author") or {}
    if author.get("name") != "Apollo Team":
        fail("plugin.json author.name must stay Apollo Team")
    if "license" in plugin:
        fail("plugin.json must not claim a license; this repository has no LICENSE file")
    if not MARKET_RE.fullmatch(str(market.get("name", ""))):
        fail("marketplace name must be kebab-case")
    owner = market.get("owner") or {}
    if owner.get("name") != "Apollo Team":
        fail("marketplace owner.name must stay Apollo Team")
    plugins = market.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        fail("marketplace must list exactly the akb plugin")
        return
    entry = plugins[0]
    if entry.get("name") != "akb":
        fail("marketplace plugin name must be akb")
    source = entry.get("source")
    if not isinstance(source, str) or source in ("",) or ".." in source.replace("\\", "/").split("/"):
        fail(f"marketplace source is not a safe relative path: {source!r}")
        return
    plugin_dir = os.path.abspath(os.path.join(ROOT, source))
    manifest = os.path.join(plugin_dir, ".cursor-plugin", "plugin.json")
    if os.path.normpath(plugin_dir) != os.path.normpath(ROOT) or not os.path.isfile(manifest):
        fail("marketplace source must resolve to this repository's .cursor-plugin/plugin.json")
    if entry.get("repository") not in (None, FORK_REPO):
        fail("marketplace repository must be the AmanitaHouse fork")
    if os.path.getsize(market_path) > 10 * 1024 * 1024:
        fail("marketplace.json exceeds 10 MB")
    if not errors:
        print("STATIC Cursor plugin and marketplace manifests: PASS")


def check_rule_and_files():
    if os.path.isdir(os.path.join(ROOT, "commands")):
        fail("commands/ would clash with the skill names; do not add it")
    if os.path.isfile(os.path.join(ROOT, "mcp.json")) or os.path.isdir(os.path.join(ROOT, "hooks")):
        fail("the plugin must not ship an MCP server or hooks")
    rule = os.path.join(ROOT, "rules", "apollo-v4.mdc")
    parsed = frontmatter_block(rule) if os.path.isfile(rule) else None
    if not isinstance(parsed, dict):
        fail("rules/apollo-v4.mdc has no YAML frontmatter")
    else:
        if not parsed.get("description"):
            fail("plugin rule needs a description")
        if parsed.get("alwaysApply") is not False:
            fail("plugin rule must set alwaysApply to false so unrelated projects are left alone")
        if "globs" in parsed:
            fail("plugin rule must not set globs; it is selected from its description")
    for rel in (
        "docs/cursor-plugin.md",
        "rules/apollo-v4.mdc",
        "tools/resolve_kb.py",
        "tools/write_project_files.py",
        "tools/submit_gate.py",
        "tools/wsl_reexec.sh",
        "skills/apollo-new-project/SKILL.md",
        "skills/apollo-build/SKILL.md",
        "skills/akb-lesson/SKILL.md",
        "skills/apollo-new-project/scripts/write-project-files.sh",
        "skills/apollo-build/scripts/find-acd.sh",
        "skills/akb-lesson/scripts/submit-gate.sh",
    ):
        if not os.path.exists(os.path.join(ROOT, rel)):
            fail(f"missing referenced file {rel}")
    for rel in (
        "skills/apollo-new-project/scripts/write-project-files.py",
        "skills/akb-lesson/scripts/submit_gate.py",
    ):
        if os.path.exists(os.path.join(ROOT, rel)):
            fail(f"{rel} duplicates a program that belongs in tools/; keep the sh entry point")


def main():
    print("SUITE cursor-plugin-static")
    print("NOTE=manifest and rule checks only. This does not load the Cursor IDE and is not evidence that a skill ran.")
    check_manifests()
    before = len(errors)
    check_rule_and_files()
    if len(errors) == before:
        print("STATIC Cursor rule and skill entry points: PASS")
    print("LIVE Cursor plugin discovery: NOT VERIFIED")
    print("REASON=no Cursor plugin-host session was driven. Interactive Customize loading was not run.")
    print(f"{len(errors)} structural problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
