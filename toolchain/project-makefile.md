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
sources:
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile (template v1.0, 2025-11-28; v1.2, pull request #22, commit d636629, 2026-11-05)"
  - "github.com/WDrijver/ApolloCrossDev commit d571781 (ApolloCrossDev v1.2, 2026-11-08): upload, debug and compile targets removed, ApolloExplorer and bgdbserver no longer installed (WDrijver: intentional)"
  - "github.com/WDrijver/ApolloCrossDev pull request #38 (2026-11-25): include paths, DevPac/Lib, include/mui"
  - "ApolloKnowledgeBase pull request #92 by AmanitaHouse (closed; found the removed targets)"
  - "github.com/WDrijver/ApolloCrossDev README.md"
---

## Summary

New ApolloCrossDev projects copy `Projects/_makefiles/Makefile`. `make`
compiles all `.c` and `.s` files in the project folder and ApolloLib's
sources and links them into one executable on the host. It does not copy
anything to the Apollo V4. A project can live anywhere.

## Details

### Project setup

1. Create the project folder: anywhere (its own git repository, for
   example), or `Projects/<project-name>` in the ApolloCrossDev checkout.
2. Copy `Projects/_makefiles/Makefile` into it.
3. Set `PROJECT_NAME` in the Makefile.
4. Add sources: `.c` for C, `.s` for assembly. For C++, see the Do / Don't
   section.
5. Run `make` in the project folder.
6. Copy the executable to the Apollo V4 yourself, for example over the
   network as in [testing-on-v4-hardware.md](../guides/testing-on-v4-hardware.md).

The template finds ApolloCrossDev through `ACD_ROOT`: the environment
variable `APOLLOCROSSDEV` when it is set, otherwise `../..`. A project
outside `Projects/` therefore needs `APOLLOCROSSDEV` set to the
ApolloCrossDev folder, for example `export APOLLOCROSSDEV="$HOME/ApolloCrossDev"`
in `~/.bashrc` or `~/.zshrc`. The compiler is then
`$(ACD_ROOT)/Compilers/GCC-6.50-Dev` (`PREFIX`). Template v1.0 had no
`ACD_ROOT` and only worked two levels below the ApolloCrossDev root.

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

### Targets

| Command | What it does |
|---|---|
| `make` | Clean, compile, link, remove the object files |
| `make cleanbefore build` | Compile and link, keep the object files |

`make cleanbefore build` works with every template version, also with older
project Makefiles.

### Older project Makefiles

The ApolloCrossDev v1.2 release (2026-11-08) removed the targets that
copied files to the V4, on purpose. Both before and after it, the Makefile
says `Template v1.2` in its first line, so check its targets:

| Makefile | `make` | Also has |
|---|---|---|
| Since 2026-11-08 | Builds only | No other targets |
| v1.2 of 2026-11-05 | Builds and uploads with ApolloExplorer's `acp` to `$AMIGAHOST` | `make compile` (build only), `make debug` (uploads bgdbserver too) |
| v1.0 | Builds and uploads | `make debug`; no `compile` |

In a Makefile that still has an `upload_all:` target, `make` copies files to
the V4 over the network. Build with `make cleanbefore build` instead, or
copy the current template. ApolloCrossDev no longer installs ApolloExplorer
or bgdbserver, so these older targets fail on a new install.

## Differences from AmigaOS / AROS / 68060

- The build runs on the host (Linux or macOS), not on the Amiga. You copy
  the executable to the Apollo V4.
- Template v1.0 started with `clear`, which stops the build when there is no
  terminal (`TERM environment variable not set`), as in IDE tasks and AI
  agents. v1.2 ignores that error.

## Do / Don't

- DO start new projects from the current Makefile template.
- DON'T run `make` in an older project Makefile with an `upload_all:` target
  unless you want to copy to the V4: use `make cleanbefore build`.
- DO add `.cpp` files to the template's file lists yourself when using C++.
  The template does not collect them.
- DON'T remove `-m68080` from `C_OPTIONS` or `S_FLAGS`.
