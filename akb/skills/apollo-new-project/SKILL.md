---
name: apollo-new-project
description: Set up a new Apollo V4 software project (game, demo, tool, application, library, device, datatype) as its own git repository in which every AI agent uses ApolloKnowledgeBase as its central source of Apollo V4 knowledge, then check, install or update ApolloCrossDev, and create the Makefile and a starting program for os-friendly or os-takeover mode that builds without warnings (guided setup), or only the AKB setup for the agent (basic setup). Use when the user wants to start, create, scaffold or set up a new program or project for the Apollo V4, Vampire V4, 68080 or SAGA, pastes the "Start Apollo V4 Project" prompt from apolloknowledgebase.com, or wants an existing folder of Apollo code prepared for AI-assisted work.
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

**Which repository the submodule tracks.** On this fork the default is
`https://github.com/AmanitaHouse/ApolloKnowledgeBase`. Say that once. If
the developer asks for the original Apollo Team repository, use
`https://github.com/ApolloTeam-dev/ApolloKnowledgeBase` instead. Do not
change the remote afterwards unless they ask.

## 0. Guided or basic setup

The project is the folder this session was started in: don't ask where.
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
the directory. It fills `AGENTS.md`
with the folder name, the defaults from the table in step 1, and
`not set yet` for what it is, kind, execution mode and languages. Then
go to step 8: show the files, offer a first commit, and mention that the
guided setup can still check ApolloCrossDev and add a Makefile and a
starting program later.

## 1. Ask what the project is (guided setup)

Ask these four in one go, and suggest the defaults in brackets:

1. **Project name** [the current folder's name]: becomes `PROJECT_NAME` and
   the program's name. Letters, digits, `-` or `_`, no spaces. The first
   character must be a letter or digit, so a folder name that begins with
   `_` or `-` is rejected. Pass `--name` with a compliant name and leave
   the directory where it is.
2. **What it is**, in one sentence, and its **kind**: game, demo, tool,
   application, library, device or datatype.
3. **Execution mode**: `os-takeover` (games and demos: multitasking off,
   direct 68080 and SAGA access, OS restored on exit) or `os-friendly`
   (applications and tools: OS calls). Explain the difference if asked; it
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

Don't ask about the rest; every new project gets these, and the developer
can change them later in `AGENTS.md`:

| Setting | Value |
|---|---|
| Target OS | ApolloOS R10, AmigaOS 3.9 and AmigaOS 3.2 |
| Target core | the latest core release. When code uses something that a knowledge base file limits to a minimum core (its `applies_to.core`), tell the developer. |
| V4 model | any V4 model |
| ApolloLib | yes, for SAGA sound, pictures, PIP, pointer and input (`KB core/best-practices/prefer-library-calls-for-saga-chips.md`) |

## 2. Create the repository with AKB

In the current folder, and only there:

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

**`APOLLOCROSSDEV`:** the project lives outside `ApolloCrossDev/Projects/`,
so the Makefile needs it. If the check notes it is unset, offer to add
`export APOLLOCROSSDEV="<ACD_ROOT>"` to `~/.zshrc` (macOS) or `~/.bashrc`
(Linux), next to `AMIGAHOST` (the V4's IP address, needed for upload; ask
for it if that is missing too). Change the file only with the user's
consent. For this session, pass `APOLLOCROSSDEV=<ACD_ROOT>` on the classified
build command from step 7. Do not assume that command is `make compile`.

## 5. Makefile and project instructions (guided setup)

Run `scripts/write-project-files.sh` with the host launch. This is the
guided invocation that creates `AGENTS.md` when that file does not exist
yet. Pass `--project`, `--setup guided`, the answers from step 1, and
`--makefile-template` set to `<ACD_ROOT>/Projects/_makefiles/Makefile`.
The script classifies that template with `KB tools/classify_build.py` before
it writes `AGENTS.md`. That is the same classifier `find-acd.sh` uses.

| Classification | What `AGENTS.md` documents |
|---|---|
| verified non-uploading `compile` | `make compile` |
| verified non-uploading `cleanbefore` and `build`, and no safe `compile` | `make cleanbefore build` |
| unverified, upload-capable, or no template | an explanation, and no Make command |

If `AGENTS.md` already exists, the script leaves it unchanged. If it prints
`NOTE=` because the file's build command does not match the template, show
that note and wait. Do not rewrite the file.

The same run writes the Makefile. It changes only:

| Line | Set to |
|---|---|
| `PROJECT_NAME` | the name |
| `C_INCL_NDK` | the `ndk39-include` line: AmigaOS 3.9 is a target, so a function that 3.9 lacks gives a compile error instead of a crash on 3.9 (`KB toolchain/target-os-headers.md`) |
| `C_COMPILER` | when the request includes C++, the commented `m68k-amigaos-g++` line, if that pair is in the template. If the line is absent, `C_COMPILER` stays as it is and the script says so separately. The installed v1.0 template and the documented v1.2 template collect `.c` and `.s` only. Add `.cpp` files as `KB toolchain/project-makefile.md` says before anyone claims a C++ build. Switching the compiler does not verify C++ |

It leaves `APOLLOLIB`, `C_OPTIONS` and `S_FLAGS` as they are. If the
template has no `ndk39-include` line, it says so and does not invent one.

## 6. The starting program (guided setup)

The script copies one file from `assets/` to `main.c` and replaces
`@PROJECT@`, `@WHAT@` and `@TARGETS@`:

| Mode | File |
|---|---|
| os-friendly | `assets/main-os-friendly.c` |
| os-takeover | `assets/main-os-takeover.c` |

The takeover programs leave the display takeover open on purpose: the KB
doesn't document it yet (`KB os/os-takeover.md`). Tell the user, and don't
fill it in from general Amiga knowledge.

That C-style `main.c` is the only starter, including when the request is
C++ only, assembler only, or a combination. Do not write a `.cpp` file, a
`.s` file, or a 68080 assembler entry point, and do not change `S_FLAGS`.
It is not a dedicated C++ starter and not an assembler program. The
ApolloCrossDev template compiles sources with `$(C_COMPILER) -c $(C_FLAGS)`
and does not pass `-x`, so when `C_COMPILER` is `m68k-amigaos-g++`, `g++`
may treat `main.c` as C++ source. That still does not verify C++ project
generation or compilation, and the template still does not collect `.cpp`
files unless its file lists are changed as
`KB toolchain/project-makefile.md` describes.

When C++ or assembler was requested, the script prints `NOTE=LANGUAGE`
lines and, in a new `AGENTS.md`, a "Guided setup language support" section.
Repeat both to the developer. The Languages line records the request. It is
not evidence that the language was implemented. The installed ApolloCrossDev
v1.0 template and the documented v1.2 template collect project `.c` and `.s`
files and do not collect `.cpp` files. Trust the notes for the template that
was supplied: they say whether `.cpp` sources are collected, whether `.s`
files are discovered, and whether `m68k-amigaos-g++` was selected. A missing
compiler-selection line is a separate note. C alone prints none of these
notes.

A non-uploading Make classification does not verify C++ project generation,
C++ compilation, or an assembler program. Do not describe the result as a
verified C++ or assembler project.

It also copies `assets/gitignore` to `.gitignore`.

## 7. Build it (guided setup)

Build as the apollo-build skill describes (`KB skills/apollo-build/SKILL.md`).
Run the command in the project's `AGENTS.md` only when that file names
`make compile` or `make cleanbefore build`. Those are the commands this
script documents after classifying the template. If the Build and test
section does not name one of them, do not run make. Do not run `make` or
`make debug` unless the developer asks. The build must end with no errors
and no warnings before you continue. A successful build of `main.c` is a
build of that C-style starter. When the language notes say C++ or assembler
was not generated, do not report the build as a verified C++ or assembler
program, even if `C_COMPILER` is `m68k-amigaos-g++` and `g++` treats the
`.c` file as C++.

## 8. Hand over

- Show the user the files you made and, for a guided setup, the build
  result. Never claim the build succeeded unless you ran it and it printed
  no errors and no warnings. When C++ or assembler was requested, show the
  `NOTE=LANGUAGE` lines as well. Do not say that language was implemented,
  generated, or verified. `make compile` or `make cleanbefore build` being
  classified as non-uploading is a statement about upload safety, not about
  C++ or assembler support.
- Offer a first commit; commit only when they agree.
- Tell them how to work from here: open the project folder in Cursor (or
  Claude Code). Cursor reads `AGENTS.md` and `.cursor/rules/apollo-v4.mdc`
  and, with the akb plugin installed, the three skills. Claude Code uses
  `CLAUDE.md` and `.claude/settings.json` when those files were written.
  `git submodule update --remote ApolloKnowledgeBase` brings in newer AKB
  content when they want it.
