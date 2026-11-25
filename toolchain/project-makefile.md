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
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile (earlier v1.2, pull request #22, commit d636629, 2026-11-05)"
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile (later local-only v1.2, commit d571781, 2026-11-08)"
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile (include and path fixes, pull request #38, commit c1fba26 / 57cb85c, 2026-11-25)"
  - "github.com/WDrijver/ApolloCrossDev README.md"
---

## Summary

New ApolloCrossDev projects copy `Projects/_makefiles/Makefile`. It compiles
all `.c` and `.s` files in the project folder and ApolloLib's sources, and
links them into one executable. Which Make targets exist, and whether any of
them upload to the Apollo V4, depends on the exact template revision: the
header comment `v1.2` alone does not distinguish the earlier upload-capable
v1.2 template from the later local-build-only v1.2 template.

Inspect the project's actual Makefile before running any Make target.

## Details

### Project setup

1. Create the project folder: anywhere (its own git repository, for
   example), or `Projects/<project-name>` in the ApolloCrossDev checkout.
2. Copy `Projects/_makefiles/Makefile` into it.
3. Set `PROJECT_NAME` in the Makefile.
4. Add sources: `.c` for C, `.s` for assembly. For C++, see the Do / Don't
   section.
5. Inspect the targets defined in that Makefile, then run only a target
   whose actual recipes match your intent (local build vs hardware upload).

From template v1.2 (pull request #22, `d636629`, 2026-11-05), a project can
live anywhere. The template finds ApolloCrossDev through `ACD_ROOT`: the
environment variable `APOLLOCROSSDEV` when it is set, otherwise `../..`. A
project outside `Projects/` therefore needs `APOLLOCROSSDEV` set to the
ApolloCrossDev folder, for example
`export APOLLOCROSSDEV="$HOME/ApolloCrossDev"` in `~/.bashrc` or
`~/.zshrc`. The compiler is then `$(ACD_ROOT)/Compilers/GCC-6.50-Dev`
(`PREFIX`). Template v1.0 (`6db8ff8`) had no `ACD_ROOT` and only worked two
levels below the ApolloCrossDev root.

### Main variables

| Variable | Default (PR #38, `c1fba26`) | Purpose |
|---|---|---|
| `ACD_ROOT` | `$APOLLOCROSSDEV`, else `../..` | The ApolloCrossDev folder (v1.2) |
| `C_COMPILER` | `m68k-amigaos-gcc` | Switch to `m68k-amigaos-g++` for C++ |
| `C_LIB` | `-noixemul` | C runtime (libnix); commented `-mcrt=clib2` / `clib2/include` is not installed by ApolloCrossDev |
| `C_INCL_NDK` | `$(PREFIX)/$(TARGET)/ndk-include` | Installed NDK 3.2 headers; `ndk13-include` is installed; `ndk39-include` is not installed (`toolchain/target-os-headers.md`) |
| `C_INCL_MUI` | off (`$(PREFIX)/$(TARGET)/include/mui`) | Optional MUI headers (lowercase `mui`, fixed in PR #38 for case-sensitive filesystems) |
| `C_OPTIONS` | `-O2 -m68080 -m68881 -ffast-math -fomit-frame-pointer -DREGPARM=4` | Compiler options. Ignore `-DREGPARM=4`. |
| `C_DEBUG` | `-g` | Debug information |
| `S_FLAGS` | `-Fhunk -m68080 -m68881 -opt-speed -linedebug -kick1hunks -I<DevPac includes>` | Assembler options (`S_INCLUDE` is `DevPac/Include`; unused `S_LIBS` is `DevPac/Lib` from PR #38) |
| `APOLLOLIB` | `$(ACD_ROOT)/Projects/ApolloLib` | ApolloLib, compiled into the program; put `#` before it to build without |
| `C_LIBS_SDL`, `C_LIBS_MUI`, `C_LIBS_MATH` | off | Extra libraries, enable by removing `#` |

Pull request #38 (`c1fba26`, 2026-11-25) also fixed these Makefile paths
across the template and project Makefiles:

- Switched `C_INCL_NDK` from nonexistent `ndk32-include/Include_H` to
  installed `ndk-include`, and marked commented `ndk39-include` and
  `clib2/include` as not installed by ApolloCrossDev.
- Removed the undefined `-I$(C_INCL)` token from `C_INCL_ALL` (which
  previously expanded to `-I -I.../sys-include` and caused GCC to treat
  `-I.../sys-include` as a directory name).
- Changed `S_LIBS` from `DevPac/Libs` to `DevPac/Lib`.
- Changed `C_INCL_MUI` from `include/MUI` to `include/mui`.

The template only collects `.c` and `.s` files (`C_FILES`, `S_FILES`). From
v1.2 (`d636629`) it compiles ApolloLib's `.c` and `.s` files with the
project's flags into the project's `.apollolib/` folder, and adds
`-I$(APOLLOLIB)` (see [apollolib/index.md](apollolib/index.md)). Template
v1.0 (`6db8ff8`) linked ready-made `.o` files from `Projects/ApolloLib`
instead.

### Targets by revision

Both upload-capable and local-build-only templates carry the
`# ApolloCrossDev Makefile Template v1.2` header. Identify behaviour from
the actual Makefile targets and recipes, not from the `v1.2` label alone:

| Revision | Local compile and link | Upload / remote debug |
|---|---|---|
| v1.0 (`6db8ff8`, 2025-11-28) | `make cleanbefore build` (no `compile` target) | Default `make` (`all`) and `make debug` upload to `"${AMIGAHOST}:Ram Disk/"` via ApolloExplorer `acp` |
| Earlier v1.2 (PR #22, `d636629`, 2026-11-05) | `make compile` (no upload) | Default `make` and `make debug` still upload via `acp` |
| Later v1.2 (`d571781`, 2026-11-08) and PR #38 (`c1fba26`, 2026-11-25) | Default `make` (`all: init cleanbefore build cleanafter exit`); no `compile` target | No `upload_*` or `debug` targets in the template; copy the executable to the V4 separately |

Never run `make`, `make compile`, `make debug`, or any other Make target
without first inspecting the project's Makefile to confirm its actual
effects. On revisions that still include upload targets, upload uses
ApolloExplorer's `acp` to `"${AMIGAHOST}:Ram Disk/"` (requiring `AMIGAHOST`
to be set to the Apollo V4's IP address).

### Remote debugging

`make debug` (uploading `bgdbserver` and a `<name>_Debug` script to
`RAM Disk:`) was present in template v1.0 (`6db8ff8`) and earlier v1.2
(`d636629`), and was removed in later v1.2 (`d571781`). When working with a
Makefile that still defines `make debug`:

1. Confirm `make debug` is defined in the project's Makefile, then run it.
2. Set breakpoints in VS Code on the host.
3. Start debugging in VS Code (F5) and select the project.
4. On the Apollo V4, double-click the program's `_Debug` icon in `RAM Disk:`.

## Differences from AmigaOS / AROS / 68060

- The build runs on the host (Linux or macOS), not on the Amiga. The Apollo
  V4 only receives the executable when an upload target is present and run,
  or when you copy the executable manually.
- Template v1.0 (`6db8ff8`) started with `clear`, which stops the build when
  there is no terminal (`TERM environment variable not set`), as in IDE
  tasks and AI agents. Template v1.2 (`d636629` onward) ignores that error.

## Do / Don't

- DO start new projects from a current ApolloCrossDev Makefile template
  (pull request #38, `c1fba26`, or later).
- DO inspect a project's actual Makefile targets and recipes before running
  Make, rather than assuming behaviour from the `v1.2` header alone.
- DO add `.cpp` files to the template's file lists yourself when using C++.
  The template does not collect them.
- DON'T run an arbitrary Make target without checking whether its recipe or
  prerequisites upload to hardware.
- DON'T remove `-m68080` from `C_OPTIONS` or `S_FLAGS`.
