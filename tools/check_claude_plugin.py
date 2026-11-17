#!/usr/bin/env python3
"""Static checks for the Claude Code plugin, plus a live validate when the CLI exists.

Manifest success is not a loaded plugin. When `claude` is absent this prints
LIVE ... NOT VERIFIED and still exits 0. A live validate that runs and fails
exits 1. This does not start an interactive `claude --plugin-dir` session.
"""
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UPSTREAM_REPO = "https://github.com/ApolloTeam-dev/ApolloKnowledgeBase"

errors = []


def fail(message):
    errors.append(message)
    print(f"FAIL {message}")


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check_manifests():
    try:
        plugin = load_json(os.path.join(ROOT, ".claude-plugin", "plugin.json"))
        market = load_json(os.path.join(ROOT, ".claude-plugin", "marketplace.json"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Claude plugin JSON: {exc}")
        return
    if plugin.get("name") != "akb":
        fail("Claude plugin name must stay akb")
    author = plugin.get("author") or {}
    if author.get("name") != "Apollo Team":
        fail("Claude plugin author must stay Apollo Team")
    if author.get("url") != "https://github.com/ApolloTeam-dev":
        fail("Claude plugin author.url must stay https://github.com/ApolloTeam-dev")
    if plugin.get("repository") != UPSTREAM_REPO:
        fail(f"Claude plugin repository must stay {UPSTREAM_REPO}")
    if market.get("name") != "apolloknowledgebase":
        fail("Claude marketplace name must stay apolloknowledgebase")
    owner = market.get("owner") or {}
    if owner.get("name") != "Apollo Team":
        fail("Claude marketplace owner.name must stay Apollo Team")
    plugins = market.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        fail("Claude marketplace must list exactly one plugin")
        return
    entry = plugins[0]
    if entry.get("name") != "akb":
        fail("Claude marketplace must still publish akb")
    if entry.get("source") not in ("./", ".", ""):
        fail("Claude marketplace source must still be the repository root")
    print("NOTE=marketplace name apolloknowledgebase is shared with Apollo Team. This check does not install both marketplaces.")
    if not errors:
        print("STATIC Claude plugin manifests: PASS")


def check_live():
    claude = shutil.which("claude")
    if not claude:
        print("LIVE claude plugin validate: NOT VERIFIED")
        print("LIVE claude --plugin-dir discovery: NOT VERIFIED")
        print("REASON=claude is not on PATH, so validate --strict and plugin-dir loading were not run")
        return
    try:
        help_run = subprocess.run(
            [claude, "plugin", "validate", "--help"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("LIVE claude plugin validate: NOT VERIFIED")
        print(f"REASON=claude plugin validate --help did not finish: {exc}")
        return
    help_text = help_run.stdout or ""
    command = [claude, "plugin", "validate", "."]
    if "--strict" in help_text:
        command.append("--strict")
    else:
        print("LIVE claude plugin validate --strict: NOT VERIFIED")
        print("REASON=this claude build does not list --strict; validate was run without it")
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=90,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        fail(f"claude plugin validate did not finish: {exc}")
        return
    print(result.stdout.rstrip())
    if result.returncode != 0:
        fail("claude plugin validate failed")
    else:
        print("LIVE claude plugin validate: PASS")
    print("LIVE claude --plugin-dir discovery: NOT VERIFIED")
    print("REASON=claude --plugin-dir starts a session. This check does not attach one. Shared entry points are exercised by tools/check_shared_workflows.py, which is not a Claude session.")


def main():
    print("SUITE claude-plugin")
    print("NOTE=static manifest checks are not a loaded Claude Code session.")
    check_manifests()
    check_live()
    print(f"{len(errors)} structural problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
