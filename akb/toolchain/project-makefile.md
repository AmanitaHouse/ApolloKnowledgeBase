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
tags: [makefile, build]
related:
  - toolchain/c-compiler-options.md
  - toolchain/vasm-assembler.md
  - toolchain/target-os-headers.md
sources:
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile (template v1.0 at 6db8ff8, 2025-11-28)"
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile (template v1.2, pull request #22, commit d636629, 2026-11-05)"
  - "github.com/WDrijver/ApolloCrossDev commit d571781 (ApolloCrossDev v1.2, 2026-11-08): upload, debug and compile targets removed, ApolloExplorer and bgdbserver no longer installed (WDrijver: intentional)"
  - "github.com/WDrijver/ApolloCrossDev pull request #38 (2026-11-25): include paths, DevPac/Lib, include/mui"
  - "ApolloKnowledgeBase pull request #92 by AmanitaHouse (closed; found the removed targets)"
  - "github.com/WDrijver/ApolloCrossDev README.md"
---

## Summary

New ApolloCrossDev projects copy `Projects/_makefiles/Makefile`. It compiles
all `.c` and `.s` files in the project folder and ApolloLib's sources, and
links them into one executable on the host. Since ApolloCrossDev v1.2
(commit `d571781`, 2026-11-08), `make` builds locally only and does not
copy anything to the Apollo V4. Which Make targets exist, and whether any
of them upload to the V4, depends on the exact template revision because the
label `v1.2` alone does not distinguish the 2026-11-05 upload-capable
template from the 2026-11-08 local-only template.

Inspect or classify the project's Makefile before running Make. A
non-uploading target is not permission to compile: the project compiler
`PREFIX` and any active documented NDK requirement must also be ready
(`toolchain/target-os-headers.md`).

## Details

### Project setup

1. Create the project folder: anywhere (its own git repository, for
   example), or `Projects/<project-name>` in the ApolloCrossDev checkout.
2. Copy `Projects/_makefiles/Makefile` into it.
3. Set `PROJECT_NAME` in the Makefile.
4. Add sources: `.c` for C, `.s` for assembly. For C++, see the Do / Don't
   section.
5. Classify the project's Makefile and run the verified local build command
   (`make` on the current local-only template, `make compile` on earlier
   v1.2, or `make cleanbefore build` on older upload-capable templates). Do
   not assume plain `make` is local-only without inspecting the Makefile.
6. Copy the executable to the Apollo V4 yourself, for example over the
   network as in [testing-on-v4-hardware.md](../guides/testing-on-v4-hardware.md).

From template v1.2 (pull request #22, 2026-11-05) a project can live
anywhere. The template finds ApolloCrossDev through `ACD_ROOT`: the
environment variable `APOLLOCROSSDEV` when it is set, otherwise `../..`. A
project outside `Projects/` therefore needs `APOLLOCROSSDEV` set to the
ApolloCrossDev folder, for example `export APOLLOCROSSDEV="$HOME/ApolloCrossDev"`
in `~/.bashrc` or `~/.zshrc`. The compiler is then
`$(ACD_ROOT)/Compilers/GCC-6.50-Dev` (`PREFIX`). Template v1.0 had no
`ACD_ROOT` and only worked two levels below the ApolloCrossDev root.
Setting `APOLLOCROSSDEV` does not repair a v1.0 relative `PREFIX`.

### Main variables

| Variable | Default | Purpose |
|---|---|---|
| `ACD_ROOT` | `$APOLLOCROSSDEV`, else `../..` | The ApolloCrossDev folder (v1.2) |
| `C_COMPILER` | `m68k-amigaos-gcc` | Switch to `m68k-amigaos-g++` for C++ |
| `C_LIB` | `-noixemul` | C runtime (libnix). The `-mcrt=clib2` line is there, but clib2 is not installed |
| `C_INCL_NDK` | `ndk-include` (NDK 3.2) | NDK headers, see `toolchain/target-os-headers.md` |
| `C_OPTIONS` | `-O2 -m68080 -m68881 -ffast-math -fomit-frame-pointer -DREGPARM=4` | Compiler options. Ignore `-DREGPARM=4`. |
| `C_DEBUG` | `-g` | Debug information |
| `S_FLAGS` | `-Fhunk -m68080 -m68881 -opt-speed -linedebug -kick1hunks -I<DevPac includes>` | Assembler options (`DevPac/Include`) |
| `APOLLOLIB` | `$(ACD_ROOT)/Projects/ApolloLib` | ApolloLib, compiled into the program; put `#` before it to build without |
| `C_LIBS_SDL`, `C_LIBS_MUI`, `C_LIBS_MATH` | off | Extra libraries, enable by removing `#` |
| `C_INCL_GL`, `C_INCL_SDL`, `C_INCL_MUI` | off | Extra include folders (`include/GL`, `include/SDL`, `include/mui`) |

The template only collects `.c` and `.s` files (`C_FILES`, `S_FILES`). From
v1.2 it compiles ApolloLib's `.c` and `.s` files with the project's flags
into the project's `.apollolib/` folder, and adds `-I$(APOLLOLIB)` (see
[apollolib/index.md](apollolib/index.md)). Template v1.0 linked ready-made
`.o` files from `Projects/ApolloLib` instead.

### Targets by verified revision

The same file name kept the label `Template v1.2` after its targets changed.
Use the actual targets and recipes in the project Makefile, not the header
comment alone.

| Revision | Local compile and link | Upload |
|---|---|---|
| v1.0 at `6db8ff8` (2025-11-28) | `make cleanbefore build`. No `compile` target | Default `make` (`all`) and `make debug` run ApolloExplorer `acp` uploads |
| Earlier v1.2 at `d636629` (pull request #22, 2026-11-05) | `make compile` runs `init cleanbefore build cleanafter exit` with no upload (`make cleanbefore build` also works) | Default `make` and `make debug` still upload via `acp` |
| Later v1.2 at `d571781` (2026-11-08) and pull request #38 (2026-11-25) | Default `make` (`all: init cleanbefore build cleanafter exit`). No `compile`, `debug`, or `upload_*` targets | None in the template. Build locally and copy the executable to the V4 |

On every revision above, `cleanbefore` and `build` perform local cleanup,
compile and link steps (keeping object files, whereas `make` or
`make compile` runs `cleanafter`). Agents must still classify the
project's actual Makefile and must not invent a target. Prefer the verified
non-uploading command (`make compile` when defined, `make` when the
default `all` target builds locally without uploading, or
`make cleanbefore build` on older upload-capable Makefiles). Do not run an
uninspected `make` or `make debug` unless the developer asks and the
Makefile shows what those goals do.

### Older project Makefiles

The ApolloCrossDev v1.2 release (`d571781`, 2026-11-08) removed `acp`,
`bgdbserver`, `make debug`, `make compile`, and the upload targets on
purpose. In a project Makefile that still has an `upload_all:` or `upload:`
target, plain `make` copies files to `"${AMIGAHOST}:Ram Disk/"` with
ApolloExplorer (`acp`), and `make debug` uploads `bgdbserver`. ApolloCrossDev
no longer installs ApolloExplorer or bgdbserver, so those upload targets
fail on a current install. Build with `make compile` (if present) or
`make cleanbefore build`, or migrate to the current template.

## Differences from AmigaOS / AROS / 68060

- The build runs on the host (Linux or macOS), not on the Amiga. You copy
  the executable to the Apollo V4.
- Template v1.0 started with `clear`, which stops the build when there is no
  terminal (`TERM environment variable not set`), as in IDE tasks and AI
  agents. v1.2 ignores that error.

## Do / Don't

- DO start new projects from the current Makefile template and classify the
  targets in that file.
- DO treat `v1.2` as a family of templates: check whether `compile`,
  `debug` and upload recipes are present before running `make`.
- DO use a classified non-uploading command, and only after the compiler
  path and required NDK headers are ready.
- DO add `.cpp` files to the template's file lists yourself when using C++.
  The template does not collect them.
- DON'T remove `-m68080` from `C_OPTIONS` or `S_FLAGS`.
- DON'T assume plain `make` is safe to run unattended on an uninspected
  Makefile.
