#!/usr/bin/env python3
"""Check that a lesson may be submitted. This script does not submit it.

The skill runs skills/akb-lesson/scripts/submit-gate.sh.
This program is the shared implementation (Python standard library only).

Usage:
  python tools/submit_gate.py --draft FILE --approved FILE --destination owner/repo

Exit 0 only when --destination is an owner/repo slug and the approved file
is byte-for-byte the draft. Exit 1 otherwise. A successful check is not
permission to push: the developer must also have asked for that destination
in the conversation. The script never runs git or gh.
"""
import argparse
import re
import sys

DEST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--draft", required=True)
    parser.add_argument("--approved", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args(argv)
    problems = []
    if not DEST_RE.fullmatch(args.destination or ""):
        problems.append(
            "destination must be owner/repo, named by the developer before submission"
        )
    try:
        with open(args.draft, "rb") as fh:
            draft = fh.read()
    except OSError as exc:
        draft = None
        problems.append(f"draft cannot be read: {exc}")
    try:
        with open(args.approved, "rb") as fh:
            approved = fh.read()
    except OSError as exc:
        approved = None
        problems.append(f"approved copy cannot be read: {exc}")
    if draft is not None and approved is not None and draft != approved:
        problems.append("approved text does not match the draft; do not submit")
    if problems:
        for item in problems:
            print(f"PROBLEM={item}")
        print("SUBMIT=no")
        return 1
    print("SUBMIT=yes")
    print(f"DESTINATION={args.destination}")
    print("NOTE=this check does not push, open a pull request, or open an issue")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
