# Cursor plugin

This file is operational documentation for the Cursor plugin. It is not
Apollo V4 knowledge and it has no knowledge-base frontmatte
(`CONTRIBUTING.md` sections 2 and 4).

The `akb` plugin packages ApolloKnowledgeBase for Cursor. It is the same
knowledge base and the same three skills as the Claude Code plugin. A
GitHub marketplace install uses the generated `akb/` directory. Cursor
discovers the skills from that directory's `.cursor-plugin/plugin.json`,
`skills/`, and `rules/`.

Apollo Team wrote the knowledge base and the original skills. This repository
adds the Cursor package and points new projects at
`ApolloTeam-dev/ApolloKnowledgeBase` unless the developer asks for anothe
clone URL.

## What it does

After installation, Cursor Agent can run three skills:

| Skill | Invocation | What it does |
|---|---|---|
| `apollo-new-project` | `/apollo-new-project` | Guided or basic setup of an Apollo V4 project |
| `apollo-build` | `/apollo-build` | Find ApolloCrossDev, build with the classified non-uploading command, fix the cause of diagnostics |
| `akb-lesson` | `/akb-lesson` | Draft a lesson, validate it, and submit only after you approve |

The plugin also ships a read-only MCP server (`akb-knowledge`) that searches
and reads the packaged knowledge articles. Skills remain the primary
workflow for project setup and builds; MCP is for targeted document lookup.

The plugin does not copy the knowledge base into the prompt. The agent reads
`AGENTS.md` and then the files that document says to read, or calls the MCP
tools when those are enabled.

A short rule, `rules/apollo-v4.mdc`, is available when the work is about the
68080, SAGA, ApolloOS, AmigaOS on V4, or ApolloCrossDev. It is not applied to
unrelated projects.

## Requirements and platforms

- Cursor with local plugin imports allowed. On Enterprise, an admin controls
  this under Dashboard, Settings, Security and Identity, Marketplace and Plugins.
- Python 3 available as `python` when launched through `cmd.exe` (Windows Store
  app-execution aliases are fine in that path). Cursor starts the MCP server
  with `cmd.exe /c …/tools/akb_mcp_launch.cmd`, which runs
  `tools/akb_mcp_server.py`. The server uses the standard library only (no pip
  install). Optional override: `AKB_PYTHON`. Linux/macOS hosts can point MCP at
  `node …/akb_mcp_launch.js` or `python3 -u …/akb_mcp_server.py` instead.
- `tools/check_frontmatter.py` and `tools/check_links.py`
  also need [PyYAML](https://pypi.org/project/PyYAML/). The skill entry
  points do not import PyYAML. `tools/submit_gate.py` and
  `tools/akb_mcp_server.py` use the standard library only. Do not install
  PyYAML into a system or distro Python unless the developer agrees. The
  host-launch section says how to run the checkers with an interpreter that
  already has it, or with an isolated virtual environment.
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

## Canonical sources and the packaged plugin

The skills, the knowledge articles, and the shared programs in `tools/`
are maintained at the repository root. Claude Code installs that root
(`.claude-plugin/`, source `./`).

Cursor's GitHub marketplace indexer does not accept a plugin whose
`source` is `.` or `./`. It installs a named directory. This repository's
marketplace entry points at `akb/`. That directory is a generated,
self-contained copy of the files the three skills need when Cursor copies
only `akb/`.

`tools/package_cursor_plugin.py` writes `akb/` from those canonical files.
`akb/PACKAGE.txt` says the directory is generated. Do not edit anything
under `akb/` by hand, and do not treat those copies as separate knowledge
articles. Change the canonical file, then run the packaging script.
`tools/check_cursor_plugin.py` fails when `akb/` is missing a file, has an
extra file, or differs from a fresh run of the script.

The root `.cursor-plugin/plugin.json` is the manifest the script copies to
`akb/.cursor-plugin/plugin.json`. A full checkout still has a plugin
manifest at its root. The marketplace file stays at the repository root
and is not copied into `akb/`.

The package includes the three skills and their assets, `rules/`, the
programs those skills run, the templates they fill, `mcp.json`,
`tools/akb_mcp_server.py`, and the knowledge base those skills and the MCP
server read when a project has no submodule: `AGENTS.md`,
`CONTRIBUTING.md`, the four pillars, guides, examples, conventions,
lessons, `sources/`, and this file.

It does not include `.claude-plugin/`, CI workflows, the document-intake
converters, the V4 test runner, or `evals/`. Those stay canonical. The
installed plugin does not need them to set up a project, resolve the
knowledge base, find ApolloCrossDev, or check a lesson.

## Local development installation

Cursor does not follow a symlink in `~/.cursor/plugins/local` that points at a
checkout outside that folder. Copy the files.

macOS and Linux:

```sh
rm -rf ~/.cursor/plugins/local/akb
mkdir -p ~/.cursor/plugins/local
git clone https://github.com/ApolloTeam-dev/ApolloKnowledgeBase.git /tmp/akb-src
rsync -a /tmp/akb-src/akb/ ~/.cursor/plugins/local/akb/
```

Windows PowerShell, from a clone of this repository:

```powershell
$dest = Join-Path $env:USERPROFILE ".cursor\plugins\local\akb"
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
New-Item -ItemType Directory -Force -Path $dest | Out-Null
robocopy (Join-Path $PWD "akb") $dest /E /NFL /NDL /NJH /NJS /nc /ns /np
```

`robocopy` exits 0 through 7 when the copy succeeded. Then reload Curso
(Developer: Reload Window) and open Customize. You should see the plugin's
skills `apollo-new-project`, `apollo-build`, and `akb-lesson`, the rule
`apollo-v4` set so the agent decides when to apply it, and the MCP server
`akb-knowledge` (shown with a `plugin-akb-` prefix in approval prompts).

Replace that folder with a fresh copy after you pull plugin changes, then
reload again.

## MCP server (read-only knowledge lookup)

### Runtime and transport

| Item | Value |
|---|---|
| Transport | Local stdio |
| Command | `cmd.exe /c ${CURSOR_PLUGIN_ROOT}/tools/akb_mcp_launch.cmd` → `python -u akb_mcp_server.py` |
| Config | `mcp.json` at the plugin root; `plugin.json` sets `"mcpServers": "mcp.json"` |
| Credentials | None. No `AKB_PAT`, no remote URL, no secrets in config |
| Knowledge root | The installed plugin directory (`AKB_PLUGIN_ROOT` / `${CURSOR_PLUGIN_ROOT}`) |

Windows Cursor launches this on the Windows host. It does not go through WSL.
Skill `sh` entry points still use WSL from PowerShell as documented above; that
is a separate path from MCP startup.

### Enable and verify in Cursor

1. Install the packaged `akb/` tree under `~/.cursor/plugins/local/akb` (see above).
2. Reload the window (**Developer: Reload Window**).
3. Open **Customize** (or MCP settings) and confirm `akb-knowledge` is listed and enabled.
4. In a new Agent chat, ask for a tool-backed lookup, for example:

   > Using the AKB MCP tool `akb_read_document`, read
   > `lessons/2026-11-akb-verification.md` and report its title.

5. Confirm the tool call appears in the agent tool record and the title
   contains `Automated verification of the knowledge base`.

### Tools

| Tool | Purpose |
|---|---|
| `akb_get_info` | Plugin root, version, document count (smoke check) |
| `akb_list_sections` | Section folders and markdown counts |
| `akb_search` | Case-insensitive search; optional `section`, `limit` |
| `akb_read_document` | Read one `.md` path relative to the plugin root |

### Offline protocol tests

From a repository checkout (after `python tools/package_cursor_plugin.py`):

```powershell
python tools/test_akb_mcp.py
```

```sh
python3 tools/test_akb_mcp.py
```

That exercises initialize, `tools/list`, read-only tool calls, invalid
arguments, missing documents, path traversal rejection, shutdown/restart,
and launch from the packaged `akb/` copy. Optional Inspector smoke (pinned):

```powershell
npx --yes @modelcontextprotocol/inspector@0.16.2 --cli python -u tools/akb_mcp_server.py --method tools/list
```

### Marketplace import vs MCP operation

| Layer | What “pass” means |
|---|---|
| Marketplace manifest | Valid `.cursor-plugin/marketplace.json` with `source` `akb` |
| Local plugin discovery | Plugin visible under Customize after a local copy |
| MCP configuration | `mcp.json` registered; server name `akb-knowledge` |
| MCP startup | Server process connects |
| MCP protocol | Initialize, discovery, and a real tool call succeed |
| Cursor Agent integration | Agent invokes an AKB MCP tool and uses the result |
| Personal Marketplace import | Plugin appears after a GitHub marketplace import |

A green local MCP test does not prove the Personal Marketplace importer works.
A broken marketplace import does not block local MCP validation. Do not change
a Support-validated marketplace layout only to retry an import that still shows
zero plugins.

### Troubleshooting MCP

| What you see | What to do |
|---|---|
| MCP server missing after install | Confirm `mcp.json` and `tools/akb_mcp_server.py` exist under the local plugin folder. Confirm `plugin.json` has `"mcpServers": "mcp.json"`. Reload the window. |
| Server fails to start on Windows | In `cmd.exe`, run `python -c "import sys; print(sys.version)"`. Check MCP logs for `akb-mcp: listening`. Set `AKB_PYTHON` if needed. Do not point MCP at WSL unless you deliberately change the command. |
| Tools missing in Agent | Enable the server under Customize / MCP. Start a **new** Agent conversation after enable. |
| Duplicate MCP entry | Remove any user-level MCP config that also registers `akb-knowledge` for the same install. |
| Path or search errors | Paths are relative to the plugin root (`lessons/…`, not a Windows absolute path). |

## GitHub installation

Cursor's **From GitHub Repository** import reads
`.cursor-plugin/marketplace.json` at the repository root. This file lists
one plugin, `akb`, with `source` `akb`. That source is a named directory.
The indexer does not accept `source` `.`, and it may skip a `source` of
`./`. The directory `akb/` contains `.cursor-plugin/plugin.json`,
`skills/`, `rules/`, and the knowledge base those skills read.

The marketplace entry is only `name`, `source`, and `description`. Version,
author, homepage, repository, and keywords stay in
`.cursor-plugin/plugin.json`. Cursor's published marketplace schema rejects
any other field on a plugin entry, including fields that the prose reference
lists.

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
- **Guided** also asks for the name, kind, execution mode (`os-friendly` or
  `os-takeover`), and languages (`C`, `C++`, `assembler`, or a combination).
  It checks ApolloCrossDev, writes a Makefile from that install's template,
  and builds with the command that template was classified as non-uploading.
  C, assembler, and C `os-takeover` write `main.c`. Os-friendly C++ writes
  `main.cpp` and adds project `.cpp` discovery when the Makefile template
  names `m68k-amigaos-g++`. Those `.cpp` files are compiled with that
  driver through `CXX_COMPILER`. `.c` files stay on the template GCC
  `C_COMPILER` line. A template with no identifiable G++ assignment, and
  C++ `os-takeover`, each print `PROBLEM=` and write nothing. Assembler is
  recorded, and the notes say whether the template discovers `.s` files.
  No assembler starter is written. A non-uploading Make classification
  does not verify C++ compilation, linkage, or hardware execution, and it
  does not verify an assembler program. Standard C++ library and runtime
  support are not established. An empty or unknown language is rejected
  before any project file is written.

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

When the project has a Makefile, `find-acd.sh` prints `BUILD=` only for a
command it has classified as non-uploading: `make compile`, or
`make cleanbefore build`. If it prints `NOTE=` that no Make command can be
recommended, the agent does not run make. Plain `make` and `make debug`
upload on v1.0 and earlier v1.2 templates; later v1.2 removed those upload
recipes (`toolchain/project-makefile.md`). The agent runs plain `make` or
`make debug` only when you ask. A `BUILD=` line does not clear a `PROBLEM=`.

Header and flag choices come from `toolchain/`, not from memory. `find-acd.sh`
checks the NDK directories the project Makefile names, as listed in
`toolchain/target-os-headers.md`
(`m68k-amigaos/ndk39-include`, `m68k-amigaos/ndk32-include/Include_H`) under
the effective Makefile `PREFIX` when that location and an active wired
`C_INCL_NDK` can be established without evaluating Make. A missing required
directory is `PROBLEM=`; uncertainty about the compiler path or flag wiring,
or an absent directory whose use is not established, is `NOTE=`.
`m68k-amigaos/ndk-include` is not a substitute. The documented installer
does not create the version-specific Makefile paths. If the required NDK
directory is not under the effective `PREFIX`, the build is not described as
successful.

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
- The GitHub marketplace install is the `akb/` directory, not the
  repository root. A project without a submodule reads that directory.
  An initialized submodule still wins.
- Skill frontmatter is only `name` and `description`, one description line,
  so Claude and Cursor read the same file. Cursor keys such as
  `disable-model-invocation` are not added.
- There is no hook or background process beyond the stdio MCP server Cursor
  launches when `akb-knowledge` is enabled. Skill workflows still run the
  existing scripts with the agent shell.
- The MCP server is read-only local files. It does not write lessons, open
  pull requests, or replace `/apollo-build` / `/akb-lesson`.
- No slash commands were added under `commands/`. The skill names are already
  invocable.
- This repository has no license file. Local use and a GitHub import are
  described above. Marketplace publication is not.
- A Makefile is not treated as safe just because one recipe never mentions
  `acp`. `/apollo-build` runs a Make command only when `find-acd.sh` prints
  `BUILD=` for that command.
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
| MCP server missing in Customize | Confirm `mcp.json` and `tools/akb_mcp_server.py` were copied with the package. See [MCP troubleshooting](#troubleshooting-mcp). |
| `PROBLEM=` from `tools/resolve_kb.py` | Follow the `RECOVERY=` lines. An empty `ApolloKnowledgeBase/` folder means the submodule is not initialized. |
| `PROBLEM=` from `find-acd.sh` | Install ApolloCrossDev or fix `APOLLOCROSSDEV`. Do not point it at a directory without `Compilers/`. A `PROBLEM=` about a documented NDK directory means that path is missing under the reported compiler install; do not substitute `ndk-include`. |
| `sh` is not recognized in PowerShell | The agent shell is Windows PowerShell. Use the host-launch section: `wsl.exe -e sh` or `wsl.exe -e python3`, with Windows paths translated. Do not call the Windows Store `python` alias. |
| `PROBLEM=python3 is not on PATH` from a skill entry point | The `sh` script is running, and the shared program in `tools/` needs Python 3. PyYAML is not required for that program. On Git Bash this line means WSL `python3` was not usable either. The Windows Store aliases in `WindowsApps` are not a Python install. Start WSL, or install a Python 3 that `python3 -c "import sys"` can run. |
| `UPDATE=compiler` or `UPDATE=checkout` | You decide. A build may continue. A reinstall is yours to run. |
| `NOTE=` that no Make command can be recommended | The Makefile was not classified as non-uploading. Do not run `make`, `make compile`, or `make cleanbefore build` from that note. |
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
python tools/package_cursor_plugin.py --check
python tools/check_cursor_plugin.py
python tools/check_claude_plugin.py
python tools/test_akb_mcp.py
```

`test_akb_mcp.py` is the MCP protocol suite. It needs only the standard
library and a packaged `akb/` tree. It does not load Cursor.

`check_frontmatter.py`, `check_links.py` and `check_skills.py` are the
content and skill checks from `CONTRIBUTING.md`. `docs/cursor-plugin.md` is
included in the link check and in Markdown lint. It is excluded from the
knowledge-base frontmatter check.

`check_cursor_plugin.py` and `check_claude_plugin.py` check manifests.
Neither loads Cursor or Claude Code.
`check_cursor_plugin.py` imports `jsonschema` and validates the root
marketplace manifest, the root plugin manifest, and
`akb/.cursor-plugin/plugin.json` against the pinned schemas in
`tools/cursor-schemas/`. It also checks that `akb/` matches
`tools/package_cursor_plugin.py` and runs the skill programs from a
temporary copy of only that directory. CI installs `jsonschema==4.25.1`
with PyYAML. A marketplace entry that adds a field the schema does not
list fails this check. A `source` of `.` or `./` fails it as well.
`check_claude_plugin.py` prints `LIVE claude plugin validate: NOT VERIFIED`
when the `claude` command is absent. That line is not a passing plugin load.

`check_shared_workflows.py` runs the shared entry points (resolver,
scaffolding, a missing ApolloCrossDev, the lesson gate, build-command
classification, and language-selection fixtures) in a temporary directory.
It does not load either editor. The default invocation is fixture-only: it
does not run Make or the compiler, and it prints
`RESULT guided-build SKIPPED`. Pass `--run-toolchain` for the authorised
real-toolchain probe. That probe may run a verified non-uploading Make
target such as `make compile` or `make cleanbefore build`, and a compiler
smoke test when the documented NDK path is absent. It still never runs
`make` or `make debug` as those upload. `RESULT guided-build PASS` appears
only after that opt-in probe finishes a real compile with no errors and no
warnings.
