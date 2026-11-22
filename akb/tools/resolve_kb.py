#!/usr/bin/env python3
"""Resolve which ApolloKnowledgeBase a project must read.

Usage: python tools/resolve_kb.py [project-directory]

The project directory is the user's repository, not the installed plugin.
Resolution order:

1. <project>/ApolloKnowledgeBase when that tree is present and initialized
   (AGENTS.md plus skills/ or core/). Its pinned checkout wins over the plugin.
2. Otherwise the knowledge base bundled with this script (the installed akb
   plugin, Claude Code or Cursor, or a checkout of this repository).
3. If the project has a submodule entry that is missing or not initialized,
   stop. Do not silently use the plugin. If neither tree is usable, stop.

Prints KEY=value lines. Exits 0 when KB_ROOT is set, and 1 otherwise.
"""
import os
import subprocess
import sys

SUBMODULE = "ApolloKnowledgeBase"


def _commit(root):
    try:
        out = subprocess.check_output(
            ["git", "-C", root, "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _valid_tree(root):
    agents = os.path.join(root, "AGENTS.md")
    if not (os.path.isfile(agents) and os.path.getsize(agents) > 0):
        return False
    return os.path.isdir(os.path.join(root, "skills")) or os.path.isdir(
        os.path.join(root, "core")
    )


def _declared(project):
    gitmodules = os.path.join(project, ".gitmodules")
    if not os.path.isfile(gitmodules):
        return False
    try:
        with open(gitmodules, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return False
    return SUBMODULE in text


def _bundle_ok(root):
    """True when root is a knowledge-base tree.

    The bundle is the directory that contains this script. Claude Code and
    Cursor both install that directory. A Cursor manifest is not required:
    requiring `.cursor-plugin/plugin.json` would reject a Claude plugin tree.
    """
    return _valid_tree(root)


def resolve(project, bundle):
    """Return a dict: ok, root, source, commit, problems, recovery, notes."""
    project = os.path.abspath(project)
    bundle = os.path.abspath(bundle)
    sub = os.path.join(project, SUBMODULE)
    problems = []
    recovery = []
    notes = []

    present = os.path.exists(sub)
    declared = _declared(project)
    if present or declared:
        if not os.path.isdir(sub):
            problems.append(
                f"{SUBMODULE}/ is not an initialized directory "
                f"({sub} is missing or is not a directory)."
            )
        elif not _valid_tree(sub):
            problems.append(
                f"{SUBMODULE}/ is present but not initialized: "
                "AGENTS.md is missing or the tree has neither skills/ nor core/."
            )
        else:
            if not declared and not os.path.exists(os.path.join(sub, ".git")):
                notes.append(
                    f"{SUBMODULE}/ is initialized but is not recorded as a git "
                    "submodule (.gitmodules has no entry and there is no .git). "
                    "Its files are still the project's knowledge base."
                )
            commit = _commit(sub)
            return {
                "ok": True,
                "root": sub,
                "source": "submodule",
                "commit": commit,
                "problems": [],
                "recovery": [],
                "notes": notes,
            }
        recovery.append(
            "From the project directory, initialize the pinned submodule: "
            "git submodule update --init ApolloKnowledgeBase"
        )
        recovery.append(
            "If ApolloKnowledgeBase/ is an empty leftover and you have confirmed "
            "it holds nothing you need, remove that directory and run the same "
            "command. Do not read the installed plugin instead: the submodule "
            "pin is authoritative."
        )
        return {
            "ok": False,
            "root": None,
            "source": None,
            "commit": None,
            "problems": problems,
            "recovery": recovery,
            "notes": notes,
        }

    if _bundle_ok(bundle):
        notes.append(
            "No project submodule. Using the knowledge base bundled with "
            "this script (the installed akb plugin, or a checkout of this "
            "repository)."
        )
        if os.path.abspath(project) == os.path.abspath(bundle):
            notes.append(
                "The project directory is that same checkout. KB_ROOT is the "
                "checkout you have open, not a nested ApolloKnowledgeBase/ folder."
            )
        return {
            "ok": True,
            "root": bundle,
            "source": "plugin",
            "commit": _commit(bundle),
            "problems": [],
            "recovery": [],
            "notes": notes,
        }

    problems.append(
        "Neither an initialized ApolloKnowledgeBase/ submodule nor the "
        "bundled plugin knowledge base is accessible."
    )
    recovery.append(
        "Install the akb plugin (Claude Code: AGENTS.md section 9; Cursor: "
        "docs/cursor-plugin.md), or add "
        "the knowledge base: git submodule add "
        "https://github.com/ApolloTeam-dev/ApolloKnowledgeBase "
        "ApolloKnowledgeBase && git submodule update --init ApolloKnowledgeBase"
    )
    recovery.append(
        "To track another clone the developer names instead: git submodule add "
        "<that-url> ApolloKnowledgeBase"
    )
    return {
        "ok": False,
        "root": None,
        "source": None,
        "commit": None,
        "problems": problems,
        "recovery": recovery,
        "notes": notes,
    }


def bundle_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def emit(result):
    if result["ok"]:
        print(f"KB_ROOT={result['root']}")
        print(f"KB_SOURCE={result['source']}")
        print(f"KB_COMMIT={result['commit'] or 'unavailable'}")
    for note in result["notes"]:
        print(f"NOTE={note}")
    for problem in result["problems"]:
        print(f"PROBLEM={problem}")
    for step in result["recovery"]:
        print(f"RECOVERY={step}")


def main(argv):
    project = argv[1] if len(argv) > 1 else os.getcwd()
    if not os.path.isdir(project):
        print(f"PROBLEM=project directory does not exist: {project}")
        print("RECOVERY=Pass the user's project directory, not the plugin directory.")
        return 1
    result = resolve(project, bundle_root())
    emit(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
