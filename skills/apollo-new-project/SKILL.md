---
name: apollo-new-project
description: Set up a new Apollo V4 software project (game, demo, tool, application, library, device, datatype) as its own git repository in which every AI agent uses ApolloKnowledgeBase as its central source of Apollo V4 knowledge, then check, install or update ApolloCrossDev, and create the Makefile and a starting program for os-friendly or os-takeover mode (guided setup), or only the AKB setup for the agent (basic setup). A C build is checked for warnings. Experimental os-friendly C++ files are generated and are not build-verified. Use when the user wants to start, create, scaffold or set up a new program or project for the Apollo V4, Vampire V4, 68080 or SAGA, pastes the "Start Apollo V4 Project" prompt from apolloknowledgebase.com, or wants an existing folder of Apollo code prepared for AI-assisted work.
---

# apollo-new-project

Create a project that every AI agent can work in correctly from the first
prompt: it treats ApolloKnowledgeBase (AKB) as the central source of Apollo
V4 knowledge, knows its target, and builds with ApolloCrossDev.

**Knowledge root.** The installed plugin directory is not the user's
project. **KB** paths are relative to the root printed by
`KB tools/resolve_kb.py`. Run that program with the host launch below
and the project directory.

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

The resolver lives in `tools/` at the root of this skill's repository (the
installed `akb` plugin, in Claude Code or Cursor, or an AKB checkout).
From step 2 on, an initialized `ApolloKnowledgeBase/` submodule is that
root (`KB_SOURCE=submodule`). Before the submodule exists, the same
command reports the bundled plugin (`KB_SOURCE=plugin`); use it for
`KB templates/repo/AGENTS.md` and the other template files. Skill assets
that are not in the submodule yet are next to this file: `assets/` and
`scripts/write-project-files.sh`. The toolchain check is
`KB skills/apollo-build/scripts/find-acd.sh`. If the resolver prints
`PROBLEM=`, stop and follow every `RECOVERY=` line. Do not guess paths.

**Which repository the submodule tracks.** The default is
`https://github.com/ApolloTeam-dev/ApolloKnowledgeBase`. Say that once. If
the developer asks for another clone URL, use that instead. Do not
change the remote afterwards unless they ask.

## 0. Guided or basic setup

Establish the intended project directory before writing files. The usual
case is the folder this Cursor session was started in. When the developer
wants a **new directory outside that folder**, create that directory first
(for example `mkdir` on an absolute path the developer names), then either
open a Cursor session there or pass that absolute path as `--project`.
`scripts/write-project-files.sh` / `tools/write_project_files.py` require
`--project` to already exist; they do not create the directory and they
do not invent a `--mode` flag. The supported execution-mode argument is
`--execution-mode`.

First ask which setup the developer wants:

- **Guided setup:** the full procedure, steps 1 to 8: a few questions, AKB,
  ApolloCrossDev checked, installed or updated, Makefile, a starting
  program, and a build without warnings.
- **Basic setup:** only what an agent needs to use AKB correctly: steps 2
  and 3, without questions. The developer does the rest (toolchain,
  Makefile, code).

For a basic setup, skip step 1. Run `scripts/write-project-files.sh` with
the host launch, `--project` set to the project directory, and
`--setup basic`. When that directory's name does not match the rule in
step 1, also pass `--name` with a name that does. Do not rename or move
the directory. Do not pass `--target-os` or `--target-core`: basic setup
rejects those flags with `PROBLEM=` and writes nothing. It fills
`AGENTS.md` with the folder name, the defaults from the table in step 1,
and `not set yet` for what it is, kind, execution mode and languages. Then
go to step 8: show the files, offer a first commit, and mention that the
guided setup can still check ApolloCrossDev and add a Makefile and a
starting program later.

## 1. Ask what the project is (guided setup)

Ask these in one go, and suggest the defaults in brackets:

1. **Project name** [the current folder's name]: becomes `PROJECT_NAME` and
   the program's name. Letters, digits, `-` or `_`, no spaces. The first
   character must be a letter or digit, so a folder name that begins with
   `_` or `-` is rejected. Pass `--name` with a compliant name and leave
   the directory where it is.
2. **What it is**, in one sentence, and its **kind**: game, demo, tool,
   application, library, device or datatype.
3. **Execution mode**: `os-takeover` (games and demos: multitasking off,
   direct 68080 and SAGA access, OS restored on exit) or `os-friendly`
   (applications and tools: OS calls). Pass that answer as
   `--execution-mode` (not `--mode`). Explain the difference if asked; it
   is in `KB AGENTS.md` section 1 and `KB os/os-takeover.md`.
4. **Which language(s)**: C, C++ and/or assembler [C]. Pass that answer as
   `--languages`. The script accepts those three words in any case, with
   surrounding whitespace ignored. Combinations may be separated by commas,
   plus signs, or the words `and`, `or`, and `and/or`. A plus sign inside
   `C++` is not a separator. It records them as `C`, `C++`, and `assembler`.
   It does not treat a string as C++ just because the characters C++ occur
   in it, and it does not accept `cpp`, `assembly`, `asm`, or `68080 assembly`.
   An empty value or any other name prints `PROBLEM=` and writes no project
   file. Stop, show that line, and ask for one of the three words. Do not
   write the files by hand and do not substitute C.

   C++ scaffolding is experimental and os-friendly only. If the request is
   C++ and `os-takeover`, the script prints `PROBLEM=` and writes nothing.
   Stop and show that line. Do not invent a C++ takeover starter. C
   `os-takeover` is unchanged.
5. **Target OS** [ApolloOS R10, AmigaOS 3.9 and AmigaOS 3.2]: one or more of
   `ApolloOS R10`, `AmigaOS 3.9`, `AmigaOS 3.2`. Pass the answer as
   `--target-os`. When the developer already named a specific OS in the
   request, pass that value; do not expand it to all three. Omit the flag
   only when they accept the default. Invalid or ambiguous values print
   `PROBLEM=` and write no project file.
6. **Target core** [the latest core release]: `the latest core release`,
   `any`, a single `Core N`, `Core N+`, or an inclusive `Core N–M` range
   (ASCII hyphen or en/em dash). Pass the answer as `--target-core`. When
   the developer already named a core or range, pass that value; do not
   replace it with the latest core. Omit the flag only when they accept
   the default. Invalid or ambiguous values print `PROBLEM=` and write no
   project file.

Don't ask about the rest; every new project gets these, and the developer
can change them later in `AGENTS.md`:

| Setting | Value |
|---|---|
| Target OS | ApolloOS R10, AmigaOS 3.9 and AmigaOS 3.2 (default when `--target-os` is omitted) |
| Target core | the latest core release (default when `--target-core` is omitted). When code uses something that a knowledge base file limits to a minimum core (its `applies_to.core`), tell the developer. |
| V4 model | any V4 model |
| ApolloLib | yes, for SAGA sound, pictures, PIP, pointer and input (`KB core/best-practices/prefer-library-calls-for-saga-chips.md`) |

Those defaults are the project's intended targets. They are not a list of
hardware configurations verified by every cited knowledge-base article.
Explicit `--target-os` / `--target-core` values become the intended
targets recorded in `AGENTS.md` and `.cursor/rules/apollo-v4.mdc`. Do not
rewrite reviewed source-code applicability comments in starters to match
user-selected targets.

The os-friendly starters use the AttnFlags technique from
`KB os/best-practices/detect-68080-and-fpu-at-run-time.md`. That article's
reviewed applicability is Core 12798–12841 with AmigaOS 3.9 and AmigaOS 3.2.
Its recorded measurements are for AmigaOS 3.9. ApolloOS R10 and newer core
releases remain intended project targets; that article's measurements do
not demonstrate them. Absence of measurements does not establish
incompatibility. Tell the developer this boundary when the starter cites
that article. Do not change the detection checks from the article's
Technique sample.

## 2. Create the repository with AKB

In the established project directory from section 0 (the session folder, or
the absolute path the developer chose):

```sh
git init
git submodule add <the URL from the knowledge-root section> ApolloKnowledgeBase
git submodule update --init ApolloKnowledgeBase
```

If the folder already holds code, don't overwrite anything: add only what is
missing and show the user what you would change. If it is already a git
repository, skip `git init`. If `ApolloKnowledgeBase/` is already a
submodule, do not add it again and do not change its URL.

Never run `sudo`, never edit shell startup files, and never change a git
remote unless the developer agrees in this conversation.

## 3. Make AKB the agents' central source

For a basic setup, run `scripts/write-project-files.sh` with the host
launch after the submodule is initialized, so the templates come from that
pin (`KB_SOURCE=submodule`). Pass `--project` and `--setup basic`, plus
`--name` when the directory name breaks the rule in step 1. Do not rename
or move the directory. It writes only files that do not exist yet. If it
prints `SKIPPED=` because a file exists, show the developer the diff you
would apply and wait. Do not pass any flag that overwrites, and do not
write the files by hand over theirs.

For a guided setup, do not run the script yet. The run that creates
`AGENTS.md` is step 5, after ApolloCrossDev has been found, and that run
passes `--makefile-template`. Running it here would record a build command
before the selected template has been classified.

- **`AGENTS.md`** (Cursor and most other agents): from
  `KB templates/repo/AGENTS.md`, placeholders filled, HTML comments removed.
- **`.cursor/rules/apollo-v4.mdc`** (Cursor): a short project rule that
  points at `ApolloKnowledgeBase/AGENTS.md` and the three akb skills. Cursor
  does not need `.claude/settings.json`.
- **`CLAUDE.md` and `.claude/settings.json`** (Claude Code only): optional.
  The script writes them unless you pass `--no-claude`. Skip them when the
  developer does not want Claude Code files. The settings repository slug
  matches the submodule URL from step 2. Cursor never reads these files.

A basic setup stops after `AGENTS.md`, the Cursor rule, and the optional
Claude files. A guided run without `--makefile-template` writes an
explanation and names no Make command.

## 4. ApolloCrossDev: check, install or update (guided setup)

Run `KB skills/apollo-build/scripts/find-acd.sh` from the submodule with
the host launch. On PowerShell that is `wsl.exe -e sh` and the translated
script path. On Linux, macOS, WSL, and Git Bash it is `sh`.

Tell the user what you found and let them choose:

| Finding | Offer |
|---|---|
| `PROBLEM=` ApolloCrossDev not found | Install it (`KB toolchain/index.md`, sections Host requirements and Install). With the user's consent, clone it: `git clone https://github.com/WDrijver/ApolloCrossDev ~/ApolloCrossDev`. The install script needs `sudo` and takes about 30 minutes, so the user runs it in their terminal: `cd ~/ApolloCrossDev && ./GCC-6.50-Dev-MacOS.sh` (or `-Linux.sh`). Wait until it is done. |
| `PROBLEM=` a binary is missing | The install failed: point the user to `Compilers/GCC-6.50-Dev/_logs/*_err.log` and the reinstall command. Wait until it is fixed. |
| `UPDATE=checkout` | `git pull` in the ApolloCrossDev folder: quick, brings new Makefile templates, ApolloLib and scripts. If `LOCAL_CHANGES=` is reported, the user decides about those first. Run the pull only with their consent. |
| `UPDATE=compiler` | Reinstall GCC-6.50-Dev (the command is in the line; `sudo`, about 30 minutes; the user runs it). Say what the newer build changes: the bug table in `KB toolchain/compiler-variants.md`. The user may also continue now and reinstall later. |
| `UPDATES=none` | Say the toolchain is up to date. |

Run the check again after an install or update, until it reports no
`PROBLEM=` line.

**`APOLLOCROSSDEV` (template-version specific):** read the NOTE= lines.
Do not claim one fix for every template.

| Template | Guidance |
|---|---|
| v1.2 (`PREFIX=$(ACD_ROOT)/Compilers/...`) | An out-of-tree project needs `APOLLOCROSSDEV` set to the ApolloCrossDev root, or the project two levels under that root. If the check notes it is unset, offer to add `export APOLLOCROSSDEV="<ACD_ROOT>"` to `~/.zshrc` (macOS) or `~/.bashrc` (Linux), next to `AMIGAHOST` (the V4's IP address, needed for upload; ask for it if that is missing too). Change the file only with the user's consent. For this session, pass `APOLLOCROSSDEV=<ACD_ROOT>` on the classified build command from step 7 when that command is documented. |
| v1.0 (`PREFIX=$(PWD)/../../Compilers/...`) | Setting `APOLLOCROSSDEV` does **not** fix PREFIX. The relative path only works when the project is under `ApolloCrossDev/Projects/<name>`. If the project is elsewhere, explain that location incompatibility. Offer developer decisions only: move/create the project under `Projects/`, or update ApolloCrossDev for a v1.2+ template. Do not relocate the project, rewrite PREFIX, or pull ApolloCrossDev unless the developer asks. |

Do not assume the documented build command is `make compile`.

## 5. Makefile and project instructions (guided setup)

Run `scripts/write-project-files.sh` with the host launch. This is the
guided invocation that creates `AGENTS.md` when that file does not exist
yet. Pass `--project` (existing directory from section 0), `--setup guided`,
the answers from step 1, and `--makefile-template` set to
`<ACD_ROOT>/Projects/_makefiles/Makefile`. Required guided flags are
`--what`, `--kind`, and `--execution-mode` (never `--mode`). Pass
`--languages`, and pass `--target-os` / `--target-core` whenever the
developer chose non-default targets. Example (Experiment 1 shape):

```sh
sh skills/apollo-new-project/scripts/write-project-files.sh \
  --project /absolute/path/to/project \
  --setup guided \
  --name apollo-v4-capability-probe \
  --what "Capability probe for Apollo V4 guided setup" \
  --kind tool \
  --execution-mode os-friendly \
  --languages C \
  --target-os "AmigaOS 3.9" \
  --target-core "Core 12798–12841" \
  --makefile-template "<ACD_ROOT>/Projects/_makefiles/Makefile"
```

The script classifies that template with `KB tools/classify_build.py` and
checks compiler-path readiness with `KB tools/resolve_compiler.py` before
it writes `AGENTS.md`. Upload safety and build readiness stay separate.

| Classification and readiness | What `AGENTS.md` documents |
|---|---|
| verified non-uploading `compile`, and PREFIX plus required NDK ready | `make compile` |
| verified non-uploading `cleanbefore` and `build`, no safe `compile`, and PREFIX plus required NDK ready | `make cleanbefore build` |
| verified non-uploading, but PREFIX unresolved/invalid or required NDK absent | an explanation that compilation is blocked; no Make command |
| unverified, upload-capable, or no template | an explanation, and no Make command |

A non-uploading classification alone is never enough to document a Make
command. The effective project `PREFIX` must resolve for this project
location, the compiler executable must exist there, and any active
documented NDK requirement must be present. Do not substitute
`m68k-amigaos/ndk-include`.

If `AGENTS.md` already exists, the script leaves it unchanged. If it prints
`NOTE=` because the file's build command does not match the template or the
current compiler readiness, show that note and wait. Do not rewrite the file.

The same run writes the Makefile. For C, assembler, and C `os-takeover`
it changes only:

| Line | Set to |
|---|---|
| `PROJECT_NAME` | the name |
| `C_INCL_NDK` | the NDK that matches the selected Target OS (`KB toolchain/target-os-headers.md`): `ndk39-include` when AmigaOS 3.9 is among the targets (including the three-OS default); `ndk32-include/Include_H` when the targets are only AmigaOS 3.2 and/or ApolloOS R10 |

It leaves `C_COMPILER`, `O_LINKER`, `APOLLOLIB`, `C_OPTIONS` and `S_FLAGS`
as they are. `.c` files stay on the template GCC line. ApolloLib's C
compile rule stays on that line. `.s` files stay on the assembler rule.
If the template has no identifiable `C_INCL_NDK` line, or has only a
different NDK than the Target OS requires, it says so, leaves the
Makefile NDK lines unchanged, and does not claim build readiness or
document a Make command from upload-safety alone. Do not invent include
paths or substitute unrelated NDK directories. Do not assume one OS's NDK
is interchangeable with another.

For an os-friendly C++ request it also adds the minimum `.cpp` rules the
template shape allows, without new compiler or linker flags:

- `CPP_FILES` discovers project `*.cpp` files when the template does not already.
- The project object list that already turns `*.c` into objects gains the matching `*.cpp` objects.
- A copy of the project `.c` compile rule compiles `*.cpp` with `m68k-amigaos-g++`, through `CXX_COMPILER`. That path comes from the template's commented `m68k-amigaos-g++` line, or from an already-active `CXX_COMPILER` that names `m68k-amigaos-g++`. The script does not invent a G++ path from a GCC assignment. When the template has no identifiable G++ assignment, it prints `PROBLEM=` and writes nothing.
- `C_COMPILER` is not switched to `g++`. A same basename in `.c` and `.cpp` would produce one `.o` name. The script reports `NOTE=CONFLICT` and does not write `main.cpp` when `main.c` is already there.

If that Makefile cannot be classified as non-uploading, or the compiler
path / required NDK is not ready, `AGENTS.md` names no Make command and
explains the blocker. An existing Makefile is left unchanged, and the
notes say `.cpp` discovery was not added. Generating files still creates
the starter and Makefile when those paths are free; readiness only
controls whether a Make command is documented.

## 6. The starting program (guided setup)

The script copies one starter and replaces `@PROJECT@`, `@WHAT@` and
`@TARGETS@`. It never writes a second `main`.

| Request | File |
|---|---|
| os-friendly C, assembler, or C plus assembler | `assets/main-os-friendly.c` as `main.c` |
| os-takeover C, with or without assembler | `assets/main-os-takeover.c` as `main.c` |
| os-friendly C++, with or without C or assembler | `assets/main-os-friendly.cpp` as `main.cpp` |
| os-takeover C++ | no files; `PROBLEM=` |

The takeover programs leave the display takeover open on purpose: the KB
doesn't document it yet (`KB os/os-takeover.md`). Tell the user, and don't
fill it in from general Amiga knowledge. There is no C++ takeover starter.

Do not write a `.s` file or a 68080 assembler entry point, and do not
change `S_FLAGS`. Assembler-only still gets the C `main.c` and says so.
That file is not an assembler program.

When C++ or assembler was requested, the script prints `NOTE=LANGUAGE`
lines and, in a new `AGENTS.md`, a "Guided setup language support" section.
Repeat both to the developer. For a supported os-friendly C++ request,
those notes distinguish a written `main.cpp`, `.cpp` discovery, a
non-uploading Make command when one was classified, and the fact that
C++ compilation, linkage, and hardware execution are not verified. They
also say that generation does not show the documented NDK directories
are installed. Trust the notes when an existing `main.c`, `main.cpp`, or
Makefile made the C++ setup incomplete. C alone, and C `os-takeover`,
print none of the C++ notes.

A non-uploading Make classification does not verify C++ compilation,
C++ linkage, or an assembler program. Standard C++ library and
runtime-dependent features are not established. C++ os-takeover remains
unsupported. Do not describe the result as a build-verified C++ project.

It also copies `assets/gitignore` to `.gitignore`.

## 7. Build it (guided setup)

Build as the apollo-build skill describes (`KB skills/apollo-build/SKILL.md`).
Run the command in the project's `AGENTS.md` only when that file names
`make compile` or `make cleanbefore build`. Those commands are documented
only after a non-uploading classification **and** a ready compiler path
(and required NDK). If the Build and test section does not name one of
them, do not run make: compilation is blocked or no safe target exists.
Do not run `make` or `make debug` unless the developer asks. The build
must end with no errors and no warnings before you continue. A successful
build of `main.c` is a build of that C starter. A successful build of
`main.cpp` is still not something this skill has verified: compilation
and linkage of the C++ starter remain unverified until a separate
authorised test. Do not run that test unless the developer asks. When the
language notes say the C++ setup is incomplete, or that assembler was not
generated, say that.

## 8. Hand over

- Show the user the files you made and, for a guided setup, the build
  result. Never claim the build succeeded unless you ran it and it printed
  no errors and no warnings. When C++ or assembler was requested, show the
  `NOTE=LANGUAGE` lines as well. For os-friendly C++, say that `main.cpp`
  and the `.cpp` rules were generated when the notes say so, and that
  compilation, linkage, and hardware execution are not verified. A
  non-uploading `make compile` or `make cleanbefore build` is a statement
  about upload safety. It is not proof that the C++ project compiles, and
  it does not show that the documented NDK directories are installed.
- Offer a first commit; commit only when they agree.
- Tell them how to work from here: open the project folder in Cursor (or
  Claude Code). Cursor reads `AGENTS.md` and `.cursor/rules/apollo-v4.mdc`
  and, with the akb plugin installed, the three skills. Claude Code uses
  `CLAUDE.md` and `.claude/settings.json` when those files were written.
  `git submodule update --remote ApolloKnowledgeBase` brings in newer AKB
  content when they want it.
