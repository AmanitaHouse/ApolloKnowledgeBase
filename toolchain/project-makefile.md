---
title: ApolloCrossDev project Makefile template
type: reference
owner: WDrijver
status: reviewed
origin: ai-assisted
components: [toolchain]
applies_to:
  core: "any"
  os: [any]
tags: [makefile, build, upload, debug, apolloexplorer, bgdbserver]
related:
  - toolchain/c-compiler-options.md
  - toolchain/vasm-assembler.md
  - toolchain/target-os-headers.md
sources:
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile (template v1.0 at 6db8ff8, 2025-11-28)"
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile (template v1.2, pull request #22, commit d636629, 2026-11-05)"
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile (template v1.2 rewritten in d571781, 2026-11-08; present on main at 605007e)"
  - "github.com/WDrijver/ApolloCrossDev README.md"
---

## Summary

New ApolloCrossDev projects copy `Projects/_makefiles/Makefile`. It compiles
all `.c` and `.s` files in the project folder and ApolloLib's sources, and
links them into one executable. Which Make targets exist, and whether any of
them upload to the V4, depends on the exact template revision. The label
`v1.2` alone does not identify the available targets.

Inspect the project's Makefile before running Make. A non-uploading target
is not permission to compile: the project compiler `PREFIX` and any active
documented NDK requirement must also be ready
(`toolchain/target-os-headers.md`).

## Details

### Project setup

1. Create the project folder: anywhere (its own git repository, for
   example), or `Projects/<project-name>` in the ApolloCrossDev checkout.
2. Copy `Projects/_makefiles/Makefile` into it.
3. Set `PROJECT_NAME` in the Makefile.
4. Add sources: `.c` for C, `.s` for assembly. For C++, see the Do / Don't
   section.
5. Read the template's targets (table below), then run only a command that
   that file defines and that you intend. Do not assume plain `make` is
   local-only, and do not assume `make compile` exists.

From template v1.2 (pull request #22, 2026-11-05) a project can live
anywhere. The template finds ApolloCrossDev through `ACD_ROOT`: the
environment variable `APOLLOCROSSDEV` when it is set, otherwise `../..`. A
project outside `Projects/` therefore needs `APOLLOCROSSDEV` set to the
ApolloCrossDev folder, for example
`export APOLLOCROSSDEV="$HOME/ApolloCrossDev"` in `~/.bashrc` or
`~/.zshrc`. The compiler is then `$(ACD_ROOT)/Compilers/GCC-6.50-Dev`
(`PREFIX`). Template v1.0 had no `ACD_ROOT` and only worked two levels
below the ApolloCrossDev root. Setting `APOLLOCROSSDEV` does not repair a
v1.0 relative `PREFIX`.

### Main variables

| Variable | Default | Purpose |
|---|---|---|
| `ACD_ROOT` | `$APOLLOCROSSDEV`, else `../..` | The ApolloCrossDev folder (v1.2) |
| `C_COMPILER` | `m68k-amigaos-gcc` | Switch to `m68k-amigaos-g++` for C++ |
| `C_LIB` | `-noixemul` | C runtime (libnix); alternative `-mcrt=clib2` |
| `C_INCL_NDK` | Makefile names `ndk32-include/Include_H` by default | NDK headers the project asks for; see `toolchain/target-os-headers.md` |
| `C_OPTIONS` | `-O2 -m68080 -m68881 -ffast-math -fomit-frame-pointer -DREGPARM=4` | Compiler options. Ignore `-DREGPARM=4`. |
| `C_DEBUG` | `-g` | Debug information |
| `S_FLAGS` | `-Fhunk -m68080 -m68881 -opt-speed -linedebug -kick1hunks -I<DevPac includes>` | Assembler options |
| `APOLLOLIB` | `$(ACD_ROOT)/Projects/ApolloLib` | ApolloLib, compiled into the program; put `#` before it to build without |
| `C_LIBS_SDL`, `C_LIBS_MUI`, `C_LIBS_MATH` | off | Extra libraries, enable by removing `#` |

The template only collects `.c` and `.s` files (`C_FILES`, `S_FILES`). From
v1.2 it compiles ApolloLib's `.c` and `.s` files with the project's flags
into the project's `.apollolib/` folder, and adds `-I$(APOLLOLIB)` (see
[apollolib/index.md](apollolib/index.md)). Template v1.0 linked ready-made
`.o` files from `Projects/ApolloLib` instead.

### Targets by verified revision

The same file name kept the label `v1.2` after its targets changed. Use the
revision, not the label alone.

| Revision | Local compile and link | Upload |
|---|---|---|
| v1.0 at `6db8ff8` (2025-11-28) | `make cleanbefore build`. No `compile` target | Default `make` (`all`) and `make debug` run ApolloExplorer `acp` uploads |
| Earlier v1.2 at `d636629` (pull request #22, 2026-11-05) | `make compile` runs `init cleanbefore build cleanafter exit` with no upload | Default `make` and `make debug` still upload via `acp` |
| Later v1.2 at `d571781` (2026-11-08), present on main at `605007e` | Default `make` is `all: init cleanbefore build cleanafter exit`. No `compile`, `debug`, or `upload_*` targets | None in the template. The README says build locally and copy the executable to the V4 |

On every revision above, `cleanbefore` and `build` perform local cleanup,
compile and link steps. Agents must still classify the project's actual
Makefile and must not invent a target. Prefer a verified non-uploading
command such as `make compile` when that target exists, otherwise
`make cleanbefore build` when those targets are local-only. Do not run
plain `make` or `make debug` unless the developer asks and the Makefile
shows what those goals do.

Where upload targets remain, upload uses ApolloExplorer's `acp` to
`"${AMIGAHOST}:Ram Disk/"`. Set `AMIGAHOST` to the Apollo V4's IP address.

### Remote debugging

`make debug`, bgdbserver upload and the VS Code launch wiring existed on
v1.0 and on earlier v1.2 (`d636629`). Commit `d571781` removed those
targets and the related VS Code launch file from the published tree at
`605007e`. Use `make debug` only when the project's Makefile still defines
it.

## Differences from AmigaOS / AROS / 68060

- The build runs on the host (Linux or macOS), not on the Amiga. The Apollo
  V4 only receives the executable when an upload recipe still exists and is
  run.
- Template v1.0 started with `clear`, which stops the build when there is no
  terminal (`TERM environment variable not set`), as in IDE tasks and AI
  agents. v1.2 ignores that error.

## Do / Don't

- DO start new projects from the Makefile template (v1.2 or later) and read
  the targets in that file.
- DO treat `v1.2` as a family of templates: check whether `compile`,
  `debug` and upload recipes are present.
- DO use a classified non-uploading command, and only after the compiler
  path and required NDK headers are ready.
- DO add `.cpp` files to the template's file lists yourself when using C++.
  The template does not collect them.
- DON'T remove `-m68080` from `C_OPTIONS` or `S_FLAGS`.
- DON'T assume plain `make` is safe to run unattended.
