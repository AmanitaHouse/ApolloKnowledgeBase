---
name: akb-lesson
description: Write down what an Apollo V4 project learned as a lesson for ApolloKnowledgeBase, show it to the developer and, with their approval, submit it as a pull request or issue. Use when the developer says a project, release or milestone is done, asks for a summary or retrospective, or when something the agent assumed about the 68080, SAGA, ApolloOS, AmigaOS on V4 or ApolloCrossDev turned out wrong (offer it right away then, while the details are fresh).
---

# akb-lesson

Carry what a project learned back into ApolloKnowledgeBase, where every
later agent finds it once it is distilled.

**The knowledge base (KB).** Run `KB tools/resolve_kb.py` with the host
launch below and the project directory. **KB** paths below are relative
to `KB_ROOT`.

**Host launch.** Use this for every `sh` entry point and every Python
program this skill names. Linux, macOS, a shell that is already WSL, and
Git Bash run `sh` on an entry point and `python3` on a program. Git Bash
(`MSYSTEM` set) still re-execs into WSL through `tools/wsl_reexec.sh`.
Do not call `wsl.exe` from those shells.

Windows PowerShell does not have `sh`. Its `python` and `python3`
commands are often Windows Store aliases and do not run Python. From
that shell, translate each Windows path and run `wsl.exe -e sh` for an
entry point or `wsl.exe -e python3` for a program. A path that starts
with `/` is unchanged. `X:\a\b` and `X:/a/b` become `/mnt/x/a/b`:
lowercase the drive letter and replace `\` with `/`. In PowerShell, pass
each translated path as one single-quoted argument. A single quote that
belongs to the path is written twice, so spaces and quotation marks stay
inside the argument. The plugin directory is the directory that contains
`.cursor-plugin/plugin.json` beside the loaded skill. Do not hard-code a
user name, a project location, or a drive letter. The same contract is
[Host launch](../../docs/cursor-plugin.md#host-launch).

1. `KB_SOURCE=submodule`: draft and contribute inside the project's
   `ApolloKnowledgeBase/` checkout. Its pin is what the project uses.
2. `KB_SOURCE=plugin`: there is no submodule. Draft against the bundled
   knowledge base only to show the text. Do not treat the plugin install as
   a clone you may push.
3. `PROBLEM=`: stop and follow every `RECOVERY=` line.

The rules behind this skill are `KB AGENTS.md` section 8 and
`KB CONTRIBUTING.md` section 7.

## 1. Offer, don't impose

Offer the lesson in one or two sentences and say what it would contain.
Write it only when the developer wants it. Nothing is submitted without
their approval of the final text. Do not open a pull request, issue, o
the manager form in the same turn as the first draft.

## 2. Gathe

- The project's `AGENTS.md`: name, target core, model, OS, mode.
- `git log` since the start or the last release, and the conversation.
- Above all: **what the agent got wrong**, especially the assumptions from
  `KB AGENTS.md` section 2 (68060 habits on the 68080, classic chipset
  habits on SAGA, generic GCC habits on ApolloCrossDev), and what fixed it.
- Measurements, with how they were made: core, test program, counters,
  before and after numbers.
- Which KB files helped, and which were wrong or missing.

## 3. Draft

Create `lessons/YYYY-MM-<project-name>.md` (year and month of today,
kebab-case project name) from `KB templates/files/lesson.md`:

| Field | Value |
|---|---|
| `type`, `status` | `lesson`, `draft` (a lesson stays draft) |
| `owner` | the developer's GitHub login (`gh api user -q .login`, or ask) |
| `origin` | `ai-assisted` |
| `basis` | only what the evidence is: `measured`, `core-developer`, `source-code`, `official`, `other` |
| `applies_to` | from the project's `AGENTS.md`; the core in the KB notation (`"Core 12841"`, `"Core 12500+"`) |
| `sources` | the project repository and commits, test programs, people and dates |

Fill every section of the template; remove every `<placeholder>`. Be
specific and honest in "What the AI got wrong": concrete mistakes with
examples. Every claim in "Evidence" names its source tag ((G), (M),
(official), (SRC)), the core and the method; a claim without evidence goes
under "What went wrong" as an observation, not as a fact. Unde
"Candidates for distillation", name the KB file to create or change
(`core/pitfalls/...`, `toolchain/best-practices/...`).

## 4. Check

These two programs validate the knowledge base. They import PyYAML. The
submission gate in step 6 does not: `scripts/submit-gate.sh` uses the
Python standard library and only compares the draft with an approved
copy. Do not treat a passing gate as a passing frontmatter or link check.

Run `KB tools/check_frontmatter.py` and `KB tools/check_links.py` with
the host launch, from the KB clone, using a Python that already imports
PyYAML. When no such Python is available and `python3 -m venv` works,
create a virtual environment outside the checkout and outside the plugin
install, install PyYAML only there, and run the two programs with that
interpreter. When `venv` is missing, download the PyYAML wheel that
matches the interpreter into a directory outside the checkout and put
that directory on `PYTHONPATH`. Do not copy it into system
`site-packages`, and do not use `sudo` or the distro package manage
unless the developer agrees.

Fix what they report. Do not submit a file that still fails these checks.

## 5. Show and approve

Show the complete lesson to the developer. Change it until they approve
that exact text. Keep the approved bytes (a copy of the file they accepted).
A later edit invalidates the approval until they accept the new text.

## 6. Submit only after a destination and a gate

Do not assume the pull request goes to
`ApolloTeam-dev/ApolloKnowledgeBase` or to another clone the develope
names. Before any `git push`, `gh pr create`, or issue creation:

1. In the submodule, read `git remote -v` and `git status`. If there is no
   submodule, say so and offer the manager or an issue instead of pushing
   the plugin install.
2. Tell the developer the remotes you found and ask which destination they
   want: that `origin`, `ApolloTeam-dev/ApolloKnowledgeBase`, another clone
   they name, the ApolloKnowledgeBase-Manager, or the "Submit a lesson"
   issue form on the repository they name.
3. Wait for an explicit yes to that destination and to the lesson text.

Then run `scripts/submit-gate.sh` with the host launch, the draft, the
approved copy, and
the `owner/repo` destination. On PowerShell that is `wsl.exe -e sh` and
translated paths. It prints `SUBMIT=yes` only when those files
match. It does not push. If it prints `SUBMIT=no`, stop.

**Pull request (preferred),** only after `SUBMIT=yes` and the yes in the
conversation. In the project's `ApolloKnowledgeBase/` submodule:

```sh
used=$(git rev-parse HEAD)
git fetch origin main
git switch -c lesson/YYYY-MM-<project-name> origin/main
git add lessons/YYYY-MM-<project-name>.md
git commit -m "Lesson: <project name>"
gh pr create --repo "<destination they named>" --base main \
  --title "Lesson: <project name>" --body "<two lines on what it covers>"
git switch --detach "$used"
```

Without write access, `gh pr create` offers to push to a fork; accept only
if they chose that. Afterwards `git status` in the project must not show
the submodule as changed. From the project,
`git submodule update ApolloKnowledgeBase` is the other way back to the pin.

**The ApolloKnowledgeBase-Manager.** At
<https://apolloknowledgebase.com/manager/> the developer signs in with GitHub
and uses "Submit a lesson"; paste the approved text there. You do not sign
in for them.

**Issue form.** Open an issue with the "Submit a lesson" form on the
repository they named and paste the lesson.

Tell the developer the pull request or issue link. A maintainer merges it;
the team later distills it into best practices, pitfalls or guides. Neve
publish or submit a lesson automatically.
