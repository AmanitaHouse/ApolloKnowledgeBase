from pathlib import Path


def resolve(path, old, new):
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing conflict chunk in {path}:\n{old[:200]}")
    p.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
    print("resolved", path)


resolve(
    "README.md",
    "<<<<<<< HEAD\n"
    "  Point that marketplace at another clone only when the developer asks.\n"
    "- Cursor: install `akb` as described in\n"
    "=======\n"
    "- Cursor: install the generated `akb/` directory as described in\n"
    ">>>>>>> 11f1d15 (Package the Cursor plugin as the akb directory.)\n",
    "  Point that marketplace at another clone only when the developer asks.\n"
    "- Cursor: install the generated `akb/` directory as described in\n",
)

resolve(
    "docs/cursor-plugin.md",
    "<<<<<<< HEAD\n"
    "knowledge base and the same three skills as the Claude Code plugin. Curso\n"
    "discovers them from `.cursor-plugin/plugin.json`, `skills/`, and `rules/`.\n"
    "=======\n"
    "knowledge base and the same three skills as the Claude Code plugin. A\n"
    "GitHub marketplace install uses the generated `akb/` directory. Cursor\n"
    "discovers the skills from that directory's `.cursor-plugin/plugin.json`,\n"
    "`skills/`, and `rules/`.\n"
    ">>>>>>> 11f1d15 (Package the Cursor plugin as the akb directory.)\n",
    "knowledge base and the same three skills as the Claude Code plugin. A\n"
    "GitHub marketplace install uses the generated `akb/` directory. Cursor\n"
    "discovers the skills from that directory's `.cursor-plugin/plugin.json`,\n"
    "`skills/`, and `rules/`.\n",
)

resolve(
    "docs/cursor-plugin.md",
    "<<<<<<< HEAD\n"
    "git clone https://github.com/ApolloTeam-dev/ApolloKnowledgeBase.git /tmp/akb-src\n"
    "rsync -a --exclude .git /tmp/akb-src/ ~/.cursor/plugins/local/akb/\n"
    "=======\n"
    "git clone https://github.com/AmanitaHouse/ApolloKnowledgeBase.git /tmp/akb-src\n"
    "rsync -a /tmp/akb-src/akb/ ~/.cursor/plugins/local/akb/\n"
    ">>>>>>> 11f1d15 (Package the Cursor plugin as the akb directory.)\n",
    "git clone https://github.com/ApolloTeam-dev/ApolloKnowledgeBase.git /tmp/akb-src\n"
    "rsync -a /tmp/akb-src/akb/ ~/.cursor/plugins/local/akb/\n",
)

resolve(
    "tools/check_cursor_plugin.py",
    "<<<<<<< HEAD\n"
    "    if os.path.normpath(plugin_dir) != os.path.normpath(ROOT) or not os.path.isfile(manifest):\n"
    '        fail("marketplace source must resolve to this repository\'s .cursor-plugin/plugin.json")\n'
    "    if entry.get(\"repository\") not in (None, DEFAULT_REPO):\n"
    '        fail("marketplace repository must be the Apollo Team repository")\n'
    "=======\n"
    "    if os.path.normpath(plugin_dir) == os.path.normpath(ROOT):\n"
    '        fail("marketplace source must be a subdirectory, not the repository root")\n'
    "        return\n"
    "    if os.path.islink(plugin_dir) or os.path.islink(manifest):\n"
    '        fail("marketplace source must be a real directory, not a symlink")\n'
    "        return\n"
    "    if not os.path.isdir(plugin_dir) or not os.path.isfile(manifest):\n"
    '        fail("marketplace source akb must contain .cursor-plugin/plugin.json")\n'
    "        return\n"
    "    try:\n"
    "        packaged = load_json(manifest)\n"
    "    except (OSError, json.JSONDecodeError) as exc:\n"
    '        fail(f"akb plugin.json: {exc}")\n'
    "        return\n"
    '    report_schema_errors("akb/.cursor-plugin/plugin.json", plugin_validator, packaged)\n'
    '    if packaged.get("name") != "akb":\n'
    '        fail("akb/.cursor-plugin/plugin.json name must be akb")\n'
    '    if packaged.get("name") != plugin.get("name"):\n'
    '        fail("packaged plugin name must match the root plugin.json")\n'
    '    if packaged.get("repository") != plugin.get("repository"):\n'
    '        fail("packaged plugin.json repository must match the root manifest")\n'
    '    if "license" in packaged:\n'
    '        fail("akb/.cursor-plugin/plugin.json must not claim a license")\n'
    "    if entry.get(\"repository\") not in (None, FORK_REPO):\n"
    '        fail("marketplace repository must be the AmanitaHouse fork")\n'
    ">>>>>>> 11f1d15 (Package the Cursor plugin as the akb directory.)\n",
    "    if os.path.normpath(plugin_dir) == os.path.normpath(ROOT):\n"
    '        fail("marketplace source must be a subdirectory, not the repository root")\n'
    "        return\n"
    "    if os.path.islink(plugin_dir) or os.path.islink(manifest):\n"
    '        fail("marketplace source must be a real directory, not a symlink")\n'
    "        return\n"
    "    if not os.path.isdir(plugin_dir) or not os.path.isfile(manifest):\n"
    '        fail("marketplace source akb must contain .cursor-plugin/plugin.json")\n'
    "        return\n"
    "    try:\n"
    "        packaged = load_json(manifest)\n"
    "    except (OSError, json.JSONDecodeError) as exc:\n"
    '        fail(f"akb plugin.json: {exc}")\n'
    "        return\n"
    '    report_schema_errors("akb/.cursor-plugin/plugin.json", plugin_validator, packaged)\n'
    '    if packaged.get("name") != "akb":\n'
    '        fail("akb/.cursor-plugin/plugin.json name must be akb")\n'
    '    if packaged.get("name") != plugin.get("name"):\n'
    '        fail("packaged plugin name must match the root plugin.json")\n'
    '    if packaged.get("repository") != plugin.get("repository"):\n'
    '        fail("packaged plugin.json repository must match the root manifest")\n'
    '    if "license" in packaged:\n'
    '        fail("akb/.cursor-plugin/plugin.json must not claim a license")\n'
    "    if entry.get(\"repository\") not in (None, DEFAULT_REPO):\n"
    '        fail("marketplace repository must be the Apollo Team repository")\n',
)

# Ensure no conflict markers remain
for f in ["README.md", "docs/cursor-plugin.md", "tools/check_cursor_plugin.py"]:
    text = Path(f).read_text(encoding="utf-8")
    if "<<<<<<<" in text or "=======" in text or ">>>>>>>" in text:
        raise SystemExit(f"markers remain in {f}")
print("all conflicts cleared")
