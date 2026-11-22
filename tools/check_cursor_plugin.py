#!/usr/bin/env python3
"""Static checks for the Cursor plugin manifests, the generated akb/ package,
and a disposable copy of that package.

This does not load Cursor and does not compile. The canonical skill
workflows are tools/check_shared_workflows.py. This file also copies only
akb/ to a temporary plugins/local/akb tree and runs the skill programs
there, so a passing install section is not a Cursor Customize session.

Marketplace and plugin manifests are checked with a JSON Schema validator
against the pinned Cursor schemas in tools/cursor-schemas/. Those files are
snapshots of github.com/cursor/plugins at one revision. The check does not
download them.
"""
import json
import os
import re
import sys

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DIR = os.path.join(ROOT, "tools", "cursor-schemas")
SCHEMA_REVISION = "5229aad76c37451561c5b81a9b5072ae1c549a5b"

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


def load_vendor_schema(filename, expected_id):
    path = os.path.join(SCHEMA_DIR, filename)
    try:
        schema = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"vendor schema {filename}: {exc}")
        return None
    if schema.get("$id") != expected_id:
        fail(f"vendor schema {filename} $id is not {expected_id}")
        return None
    return schema


def draft7_validators(market_schema, plugin_schema):
    try:
        from jsonschema import Draft7Validator, FormatChecker
    except ImportError:
        fail("jsonschema is required to validate Cursor manifests")
        return None, None
    checker = FormatChecker()
    return (
        Draft7Validator(market_schema, format_checker=checker),
        Draft7Validator(plugin_schema, format_checker=checker),
    )


def schema_location(error):
    if not error.absolute_path:
        return "/"
    return "/" + "/".join(str(part) for part in error.absolute_path)


def report_schema_errors(label, validator, instance):
    if validator is None:
        return False
    ok = True
    found = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    for error in found:
        ok = False
        fail(f"{label} {schema_location(error)}: {error.message}")
    return ok


def reject_unsupported_marketplace_entry(validator):
    """The pinned schema must keep rejecting fields it does not list."""
    if validator is None:
        return
    sample = {
        "name": "example",
        "owner": {"name": "Example"},
        "plugins": [
            {
                "name": "akb",
                "source": ".",
                "description": "example",
                "keywords": ["unsupported"],
            }
        ],
    }
    messages = [error.message for error in validator.iter_errors(sample)]
    if not any("keywords" in message for message in messages):
        fail("pinned marketplace schema accepted an unsupported plugin entry field")
        return
    print("SCHEMA unsupported marketplace entry field: REJECTED")


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
    market_schema = load_vendor_schema(
        "marketplace.schema.json",
        "https://cursor.com/schemas/cursor-plugin/marketplace.json",
    )
    plugin_schema = load_vendor_schema(
        "plugin.schema.json",
        "https://cursor.com/schemas/cursor-plugin/plugin.json",
    )
    if market_schema and plugin_schema:
        market_validator, plugin_validator = draft7_validators(market_schema, plugin_schema)
    else:
        market_validator, plugin_validator = None, None
    market_ok = report_schema_errors("marketplace.json", market_validator, market)
    plugin_ok = report_schema_errors("plugin.json", plugin_validator, plugin)
    reject_unsupported_marketplace_entry(market_validator)
    if market_ok and plugin_ok and not errors:
        print(f"SCHEMA Cursor manifests against cursor/plugins {SCHEMA_REVISION}: PASS")
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
    source_problem = named_directory_source(source)
    if source_problem:
        fail(source_problem)
        return
    plugin_dir = os.path.abspath(os.path.join(ROOT, source))
    manifest = os.path.join(plugin_dir, ".cursor-plugin", "plugin.json")
    if os.path.normpath(plugin_dir) == os.path.normpath(ROOT):
        fail("marketplace source must be a subdirectory, not the repository root")
        return
    if os.path.islink(plugin_dir) or os.path.islink(manifest):
        fail("marketplace source must be a real directory, not a symlink")
        return
    if not os.path.isdir(plugin_dir) or not os.path.isfile(manifest):
        fail("marketplace source akb must contain .cursor-plugin/plugin.json")
        return
    try:
        packaged = load_json(manifest)
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"akb plugin.json: {exc}")
        return
    report_schema_errors("akb/.cursor-plugin/plugin.json", plugin_validator, packaged)
    if packaged.get("name") != "akb":
        fail("akb/.cursor-plugin/plugin.json name must be akb")
    if packaged.get("name") != plugin.get("name"):
        fail("packaged plugin name must match the root plugin.json")
    if packaged.get("repository") != plugin.get("repository"):
        fail("packaged plugin.json repository must match the root manifest")
    if "license" in packaged:
        fail("akb/.cursor-plugin/plugin.json must not claim a license")
    if entry.get("repository") not in (None, FORK_REPO):
        fail("marketplace repository must be the AmanitaHouse fork")
    if os.path.getsize(market_path) > 10 * 1024 * 1024:
        fail("marketplace.json exceeds 10 MB")
    if not errors:
        print("STATIC Cursor plugin and marketplace manifests: PASS")


def named_directory_source(source):
    """Return an error when source is not the named directory akb.

    The GitHub indexer does not accept "." and may skip a source that
    starts with "./". The installable plugin is the directory akb/.
    """
    if not isinstance(source, str):
        return f"marketplace source must be the named directory akb, got {source!r}"
    normalized = source.replace("\\", "/").strip()
    if normalized in {"", ".", "./"} or normalized.startswith("./"):
        return "marketplace source must be a named directory; '.' and './' are not indexed"
    if normalized.startswith("/") or "://" in normalized or re.match(r"^[A-Za-z]:", normalized):
        return f"marketplace source must be a relative directory name, got {source!r}"
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return f"marketplace source must be a named directory, got {source!r}"
    if normalized != "akb":
        return "marketplace source must be akb"
    return None


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
        "tools/classify_build.py",
        "tools/resolve_compiler.py",
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


def check_package():
    import package_cursor_plugin

    for rel in package_cursor_plugin.REQUIRED_PACKAGE_PATHS:
        path = os.path.join(ROOT, "akb", *rel.split("/"))
        if os.path.islink(path):
            fail(f"akb/{rel} must be a real file or directory, not a symlink")
        elif not os.path.exists(path):
            fail(f"akb/{rel} is missing from the distributable package")
    for rel in package_cursor_plugin.FORBIDDEN_PACKAGE_PATHS:
        path = os.path.join(ROOT, "akb", *rel.split("/"))
        if os.path.exists(path):
            fail(f"akb/{rel} must stay out of the distributable package")
    problems = package_cursor_plugin.check_tree()
    for item in problems:
        fail(item)
    if problems:
        print("INSTALL disposable copy: SKIPPED")
        print("REASON=akb/ does not match tools/package_cursor_plugin.py")
        return
    info = package_cursor_plugin.summary()
    print(
        f"PACKAGE files={info['files']} bytes={info['bytes']} "
        f"duplicated_bytes={info['duplicated_bytes']}"
    )
    print("PACKAGE akb/ matches tools/package_cursor_plugin.py: PASS")
    before = len(errors)
    for item in package_cursor_plugin.verify_installed_copy():
        fail(item)
    if len(errors) == before:
        print("INSTALL disposable akb/ copy: PASS")


def main():
    print("SUITE cursor-plugin-static")
    print("NOTE=manifest, package, and disposable-install checks. This does not load the Cursor IDE.")
    check_manifests()
    before = len(errors)
    check_rule_and_files()
    if len(errors) == before:
        print("STATIC Cursor rule and skill entry points: PASS")
    check_package()
    print("LIVE Cursor plugin discovery: NOT VERIFIED")
    print("REASON=no Cursor plugin-host session was driven. Interactive Customize loading was not run.")
    print(f"{len(errors)} structural problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
