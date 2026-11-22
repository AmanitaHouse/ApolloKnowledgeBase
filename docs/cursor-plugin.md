# Cursor plugin

This file is operational documentation for the Cursor plugin. It is not
Apollo V4 knowledge and it has no knowledge-base frontmatte
(`CONTRIBUTING.md` sections 2 and 4).

The `akb` plugin packages ApolloKnowledgeBase for Cursor. It is the same
knowledge base and the same three skills as the Claude Code plugin. Curso
discovers them from `.cursor-plugin/plugin.json`, `skills/`, and `rules/`.

Apollo Team wrote the knowledge base and the original skills. This repository
adds the Cursor package and points new projects at
`ApolloTeam-dev/ApolloKnowledgeBase` unless the developer asks for anothe
clone URL.

## What it does

After installation, Cursor Agent can run three skills:

| Skill | Invocation | What it does |
|---|---|---|
| `apollo-new-project` | `/apollo-new-project` | Guided or basic setup of an Apollo V4 project |
| `apollo-build` | `/apollo-build` | Find ApolloCrossDev, build with `make compile`, fix the cause of diagnostics |
| `akb-lesson` | `/akb-lesson` | Draft a lesson, validate it, and submit only after you approve |

The plugin does not copy the knowledge base into the prompt. The agent reads
`AGENTS.md` and then the files that document says to read.

A short rule, `rules/apollo-v4.mdc`, is available when the work is about the
68080, SAGA, ApolloOS, AmigaOS on V4, or ApolloCrossDev. It is not applied to
unrelated projects.

## Requirements and platforms

- Cursor with local plugin imports allowed. On Enterprise, an admin controls
  this under Dashboard, Settings, Security and Identity, Marketplace and Plugins.
- Python 3. `tools/check_frontmatter.py` and `tools/check_links.py`
  also need [PyYAML](https://pypi.org/project/PyYAML/). The skill entry
  points do not import PyYAML. `tools/submit_gate.py` uses the standard
  library only. Do not install PyYAML into a system or distro Python
  unless the developer agrees. The host-launch section says how to run
  the checkers with an interpreter that already has it, or with an
  isolated virtual environment.
- Git, for a project submodule.
- A POSIX shell (`sh`) on Linux, macOS, WSL, and Git Bash. Skill scripts
  are `sh` entry points, the same rule as `CONTRIBUTING.md` section 12.
  Two of them call Python 3 standard-library programs in `tools/`:
  `tools/write_project_files.py` and `tools/submit_gate.py`. There is one
  copy of each program. On Git Bash (`MSYSTEM` is set) those entry points,
  and `find-acd.sh`, re-exec under WSL when `wsl.exe -e python3` works.
  A Git Bash path `/x/...` or a Windows path `X:\...` becomes `/mnt/x/...`
  with `MSYS_NO_PATHCONV=1`, because WSL Python cannot open an `X:/...`
  path. A Git Bash path that exists in that shell, such as `/tmp/...`, is
  mapped with `cygpath -w` first. A WSL path that Git Bash cannot see,
  such as `/home/<wsl-user>/ApolloCrossDev`, is left unchanged. Flags,
  slugs and URLs are not rewritten.
  `APOLLOCROSSDEV` is forwarded only when it is already set.
  If WSL Python is not usable the entry point prints `PROBLEM=` and
  `RECOVERY=` and does not pretend the Windows Store `python3` alias ran.
  Windows PowerShell is not one of those shells. Use the host-launch
  section. Do not call `sh`, `python`, or `python3` from PowerShell.
- ApolloCrossDev (GCC 6.5 with the 68080 patches, and vasm) when you want to
  compile. Its install scripts support macOS and Linux. Windows is not a
  build host; a Linux environment such as WSL is, when ApolloCrossDev is
  installed there.
- The `gh` command only if you later ask to open a lesson pull request.

The agent must not run `sudo`, edit your shell startup files, change git
remotes, or upload to the V4 unless you agree in the conversation.

## Host launch

The same three skills run in Claude Code and in Cursor. Their entry points
stay the `sh` scripts. Their programs stay the Python files in `tools/`.
Nothing in this section adds a Windows or Claude copy of those programs.

| Shell | How to run an entry point | How to run a Python program the skill names |
|---|---|---|
| Linux, macOS, a shell that is already WSL | `sh <script> <arguments>` | `python3 <program> <arguments>` |
| Git Bash (`MSYSTEM` is set) | `sh <script> <arguments>`. The script re-execs into WSL. Do not wrap this call in `wsl.exe`. | Do not call Windows `python`. The entry point reaches WSL Python. |
| Windows PowerShell, where `sh` is not a command | `wsl.exe -e sh <translated script> <translated arguments>` | `wsl.exe -e python3 <translated program> <translated arguments>` |

Entry points: `skills/apollo-new-project/scripts/write-project-files.sh`,
`skills/apollo-build/scripts/find-acd.sh`, and
`skills/akb-lesson/scripts/submit-gate.sh`.

Python programs the skills name directly: `tools/resolve_kb.py`,
`tools/check_frontmatter.py`, and `tools/check_links.py`. The static
checkers in the validation section are the same kind of program.

On PowerShell, translate every Windows path before `wsl.exe` sees it.
Apply this to the script, the program, the project directory, and the
plugin directory:

1. A path that already starts with `/` stays as written. That includes
   `/mnt/x/...` and a WSL path such as a home directory.
2. A drive path `X:\a\b` or `X:/a/b` becomes `/mnt/x/a/b`. Lowercase the
   drive letter and replace each `\` with `/`.
3. In PowerShell, pass each translated path as one single-quoted
   argument. A single quote that is part of the path is written as two
   single quotes. Spaces and quotation marks in the path stay inside
   that argument.
4. Flags, slugs, and URLs are not paths. Leave them as written.

The plugin directory is the directory that contains
`.cursor-plugin/plugin.json` beside the skill Cursor loaded. Discover it
from that skill. Do not hard-code a user name, a project location, or a
drive letter.

`wsl.exe -e` from PowerShell does not set `MSYSTEM`, so the entry point
runs in WSL and does not re-exec a second time. Git Bash remains the only
shell that takes the `tools/wsl_reexec.sh` hop.

## Local development installation

Cursor does not follow a symlink in `~/.cursor/plugins/local` that points at a
checkout outside that folder. Copy the files.

macOS and Linux:

```sh
rm -rf ~/.cursor/plugins/local/akb
mkdir -p ~/.cursor/plugins/local
git clone https://github.com/ApolloTeam-dev/ApolloKnowledgeBase.git /tmp/akb-src
rsync -a --exclude .git /tmp/akb-src/ ~/.cursor/plugins/local/akb/
```

Windows PowerShell, from a clone of this repository:

```powershell
$dest = Join-Path $env:USERPROFILE ".cursor\plugins\local\akb"
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
New-Item -ItemType Directory -Force -Path $dest | Out-Null
robocopy $PWD $dest /E /XD .git /NFL /NDL /NJH /NJS /nc /ns /np
```

`robocopy` exits 0 through 7 when the copy succeeded. Then reload Curso
(Developer: Reload Window) and open Customize. You should see the plugin's
skills `apollo-new-project`, `apollo-build`, and `akb-lesson`, and the rule
`apollo-v4` set so the agent decides when to apply it.

Replace that folder with a fresh copy after you pull plugin changes, then
reload again.

## GitHub installation

Cursor's **From GitHub Repository** import reads
`.cursor-plugin/marketplace.json`. This file lists one plugin, `akb`, with
`source` `.`. That source is the repository root, so Cursor loads
`.cursor-plugin/plugin.json` from the same commit as the knowledge base.

In Customize, import:

`https://github.com/ApolloTeam-dev/ApolloKnowledgeBase`

Then install `akb` for yourself or for the project. This path depends on
Cursor's GitHub import UI and on access to the repository. It is separate
from the local folder above.

Official listing on the Cursor Marketplace is not claimed. This repository
has no `LICENSE` file, and Cursor reviews marketplace plugins before listing
them. Do not treat these manifests as a publication submission.

## Basic and guided setup

`/apollo-new-project` asks which one you want.

- **Basic** initializes git if needed, adds the knowledge-base submodule, and
  writes `AGENTS.md` plus `.cursor/rules/apollo-v4.mdc`. Fields you have not
  chosen are `not set yet`. It does not install a toolchain or write a program.
  The project name passed to the script must start with a letter or digit.
  The rest may be letters, digits, `-`, or `_`. When the directory name
  does not comply, the agent passes `--name` and does not rename or move
  the directory.
- **Guided** also asks for the name, kind, execution mode (`os-friendly` o
  `os-takeover`), and languages. It checks ApolloCrossDev, writes a Makefile
  from that install's template, writes `main.c`, and builds with `make compile`
  when the template has that target.

Existing files are left in place. The agent shows you a proposed change and
waits.

Claude Code files (`CLAUDE.md`, `.claude/settings.json`) are optional. Curso
does not read them. Say so if you do not want them.

## Knowledge-base resolution

`tools/resolve_kb.py` prints the directory the agent must read.

1. `<project>/ApolloKnowledgeBase` when that submodule is initialized
   (`AGENTS.md` and `skills/` or `core/` are present). That pinned revision
   is the one the project builds against.
2. Otherwise the knowledge base copied with the plugin. The plugin directory
   and the project directory are different, and the script does not assume
   they are the same.
3. If the submodule is declared or the folder exists but the tree is not
   initialized, the script exits with `PROBLEM=` and `RECOVERY=` lines. It
   does not quietly switch to the plugin copy.

Run `tools/resolve_kb.py` with the [host launch](#host-launch), passing
the project directory. On PowerShell that is `wsl.exe -e python3` and a
translated path. On Linux, macOS, and WSL it is `python3`.

New projects use the Apollo Team repository by default:

```sh
git submodule add https://github.com/ApolloTeam-dev/ApolloKnowledgeBase ApolloKnowledgeBase
```

Ask for another clone URL when the developer wants that history instead, fo
example:

```sh
git submodule add https://github.com/AmanitaHouse/ApolloKnowledgeBase ApolloKnowledgeBase
```

The skill does not change the URL after the submodule exists unless you ask.

## ApolloCrossDev

`/apollo-build` runs `skills/apollo-build/scripts/find-acd.sh`. The script
looks at `APOLLOCROSSDEV`, then two folders above the project, then
`~/ApolloCrossDev`. It prints `PROBLEM=`, `NOTE=`, and `UPDATE=` lines.

`UPDATE=` does not block a build. A missing compiler does. Installing o
reinstalling GCC-6.50-Dev takes a long time and uses `sudo`; you run that
script yourself. The agent may clone the toolchain only with your consent.

Build with `make compile` on Makefile template v1.2 or later. Plain `make`
and `make debug` upload to the V4 at `$AMIGAHOST`. The agent runs those only
when you ask. A template older than v1.2 has no `compile` target; its `build`
target may be used only when that recipe does not upload.

Header and flag choices come from `toolchain/`, not from memory. If the
documented NDK directory is not in your ApolloCrossDev tree, the build is not
described as successful.

## Lessons

`/akb-lesson` drafts `lessons/YYYY-MM-project-name.md` from
`templates/files/lesson.md`. You see the full draft. Nothing is pushed, and no
pull request or issue is opened, until you approve that exact text and name
the destination.

Two different checks follow the draft:

- `tools/check_frontmatter.py` and `tools/check_links.py` validate the
  knowledge base. They import PyYAML. Run them with the
  [host launch](#host-launch) and an interpreter that already provides
  PyYAML. When none does, and `python3 -m venv` works, create a virtual
  environment outside this checkout and outside `~/.cursor/plugins`,
  install PyYAML only into that environment, and run the two checkers
  with its Python. When that module is missing (`ensurepip` is absent),
  download the PyYAML wheel that matches the interpreter into a directory
  outside the checkout and put that directory on `PYTHONPATH`. Do not
  copy it into the system `site-packages`, and do not use `sudo` or the
  distro package manager unless the developer agrees.
- `skills/akb-lesson/scripts/submit-gate.sh` is the submission gate. It
  uses the Python standard library and does not import PyYAML. Run it
  with the host launch. It exits successfully only when an `owner/repo`
  was given and the approved file matches the draft. The script itself
  does not publish.

The destination is not assumed. It may be this repository, another clone
the developer names, the manager at
<https://apolloknowledgebase.com/manager/>, or the issue form on the
repository you name. After a pull request, the project's submodule is
returned to the commit the project had pinned.

## Claude Code compatibility

`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` keep
the Apollo Team installation identifiers: marketplace `apolloknowledgebase`,
plugin `akb`, repository `ApolloTeam-dev/ApolloKnowledgeBase`. Do not add a
second marketplace name. Claude Code cannot load two marketplaces that share
`apolloknowledgebase`. Point that marketplace at this repository or at one
named alternative, not at both under the same name.

The skill files are shared. Cursor-specific behaviour is the resolver's
caller, the project rule, and the optional Claude files no longer being
required for Cursor. The resolver itself accepts a Claude plugin tree
without `.cursor-plugin/plugin.json`.

Claude Code users install with
`/plugin marketplace add` and `/plugin install akb@apolloknowledgebase`, as
in `AGENTS.md` section 9. Point that marketplace at
`ApolloTeam-dev/ApolloKnowledgeBase` unless the developer asks for anothe
clone.

## Known limitations

- Cursor plugin rules cannot expand `${PLUGIN_ROOT}`. The resolver finds the
  bundle from its own file path. A copied install works; a symlink that leaves
  `~/.cursor/plugins/local` does not.
- Skill frontmatter is only `name` and `description`, one description line,
  so Claude and Cursor read the same file. Cursor keys such as
  `disable-model-invocation` are not added.
- There is no MCP server, hook, or background process. The agent runs the
  existing scripts with its shell.
- No slash commands were added under `commands/`. The skill names are already
  invocable.
- This repository has no license file. Local use and a GitHub import are
  described above. Marketplace publication is not.
- ApolloCrossDev template v1.0 cannot `make compile` and its default goal
  uploads. Follow `/apollo-build` rather than running `make` to "see if it
  builds".
- Git Bash is not a build host. Its `python3` is often a Windows Store
  alias, and the ApolloCrossDev compiler is a Linux binary. The skill
  entry points re-exec in WSL when that `python3` works. They do not
  change shell startup files. Windows PowerShell does not take that hop:
  `sh` is not a command there, so the agent uses `wsl.exe -e` as the
  host-launch section describes.
- The display takeover in the `os-takeover` starter is still a gap in
  `os/os-takeover.md`. The starter does not invent that sequence.
- The plugin does not install ApolloCrossDev for you.

## Troubleshooting and validation

| What you see | What to do |
|---|---|
| Skills missing in Customize | Confirm the copy is a real directory at `~/.cursor/plugins/local/akb` with `.cursor-plugin/plugin.json` inside. Reload the window. On Enterprise, ask whether local plugin imports are allowed. |
| `PROBLEM=` from `tools/resolve_kb.py` | Follow the `RECOVERY=` lines. An empty `ApolloKnowledgeBase/` folder means the submodule is not initialized. |
| `PROBLEM=` from `find-acd.sh` | Install ApolloCrossDev or fix `APOLLOCROSSDEV`. Do not point it at a directory without `Compilers/`. |
| `sh` is not recognized in PowerShell | The agent shell is Windows PowerShell. Use the host-launch section: `wsl.exe -e sh` or `wsl.exe -e python3`, with Windows paths translated. Do not call the Windows Store `python` alias. |
| `PROBLEM=python3 is not on PATH` from a skill entry point | The `sh` script is running, and the shared program in `tools/` needs Python 3. PyYAML is not required for that program. On Git Bash this line means WSL `python3` was not usable either. The Windows Store aliases in `WindowsApps` are not a Python install. Start WSL, or install a Python 3 that `python3 -c "import sys"` can run. |
| `UPDATE=compiler` or `UPDATE=checkout` | You decide. A build may continue. A reinstall is yours to run. |
| Build has no `compile` target | The template is older than v1.2. Do not run plain `make` unless you intend to upload. |
| Lesson gate prints `SUBMIT=no` | The approved copy differs from the draft, or the destination is not `owner/repo`. Nothing was published. |

From the repository root, with PyYAML available to the content checks.
On Windows PowerShell, run these with `wsl.exe -e python3` after path
translation, using an interpreter that imports PyYAML (an existing one,
or the isolated environment in the lessons section). On Linux, macOS,
and WSL, `python3` is enough:

```sh
python tools/check_frontmatter.py
python tools/check_links.py
python tools/check_skills.py
python tools/check_shared_workflows.py
python tools/check_cursor_plugin.py
python tools/check_claude_plugin.py
```

`check_frontmatter.py`, `check_links.py` and `check_skills.py` are the
content and skill checks from `CONTRIBUTING.md`. `docs/cursor-plugin.md` is
included in the link check and in Markdown lint. It is excluded from the
knowledge-base frontmatter check.

`check_cursor_plugin.py` and `check_claude_plugin.py` check manifests. That
is static validation. It does not load Cursor or Claude Code.
`check_claude_plugin.py` prints `LIVE claude plugin validate: NOT VERIFIED`
when the `claude` command is absent. That line is not a passing plugin load.

`check_shared_workflows.py` runs the shared entry points (resolver,
scaffolding, a missing ApolloCrossDev, the lesson gate) in a temporary
directory. It does not load either editor. When ApolloCrossDev is absent it
prints `RESULT guided-build NOT VERIFIED` and still exits 0. It prints
`RESULT guided-build PASS` only after a real compile with no errors and no
warnings. It never runs `make` or `make debug`.
