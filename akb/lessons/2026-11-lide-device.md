---
title: lide.device (V4 scsi.device) 48.14 moved to the AKB build defaults
type: lesson
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [toolchain, devs]
applies_to:
  core: "any"
  os: [amigaos-3.2, apolloos-r10]
  mode: [os-friendly]
tags: [makefile, ndk, vasm, hunk, section, linking, move16, resident, macos]
related:
  - toolchain/target-os-headers.md
  - toolchain/vasm-assembler.md
  - toolchain/c-compiler-options.md
  - toolchain/compiler-variants.md
  - toolchain/project-makefile.md
sources:
  - "lide.device V4 backend 48.14 (ApolloSoftware Drivers/scsi.device), Makefile change of 2026-11-24"
  - "ApolloCrossDev GCC-6.50-Dev, macOS install built 2026-11-16; GCC-6.50-Dev-MacOS.sh and GCC-6.50-Dev-Linux.sh at commit 053c5ad10 (2026-11-24)"
  - "Link tests with m68k-amigaos-ld and vasm 2.0g, objdump -h and nm on the result, 2026-11-24"
---

## Project

lide.device with the Apollo V4 Fast-IDE backend, installed as `scsi.device`
48.14 (the previous published release in ApolloSoftware is 48.13). The device
had its own Makefile: GCC-6.50-Stable, `-Os -mcpu=68060`, gas for two small
assembler files. On 2026-11-24 the Makefile was moved to the AKB defaults:
GCC-6.50-Dev, `-noixemul -O2 -m68080 -m68881 -ffast-math -fomit-frame-pointer`,
libnix and NDK 3.2 include paths, vasm. Built on macOS; the developer
tested the new build on a V4 and reported it OK on 2026-11-24.

## What went well

- All four variants (cache, no cache, no read-ahead, experimental postinc)
  built with GCC-6.50-Dev without errors or warnings on the first attempt.
- `-m68080` accepts the `move16 (a0)+,(a1)+` inline assembler of the read
  path; `-mcpu=68060` is not needed for MOVE16.
- Linking an unstripped copy and comparing `nm -n` and `objdump -s` with the
  old build caught a layout change that a successful build did not show.

## What went wrong

- The old Makefile pointed at `Compilers/GCC-6.50-Stable`, which was not
  installed; the build failed until the compiler path was changed.
- The NDK 3.2 path from the KB and the Makefile template,
  `<prefix>/m68k-amigaos/ndk32-include/Include_H`, does not exist in this
  install. NDK 3.2 is installed as `<prefix>/m68k-amigaos/ndk-include`
  (`exec/execbase.h` 47.2). There is no `ndk39-include` either; only
  `ndk13-include`. Neither install script (`GCC-6.50-Dev-MacOS.sh`,
  `-Linux.sh`) creates `ndk32-include` or `ndk39-include`; they run amiga-gcc
  `make all NDK=3.2`, which installs into `ndk-include`.
- The missing include path is silent: GCC ignores a `-I` folder that does
  not exist, and `ndk-include` is on its built-in search path, so the
  template still builds, with NDK 3.2 by accident rather than by its setting.
  Selecting NDK 3.9 through the template would also fall back to 3.2 without
  any message.
- `apollo-build`'s `find-acd.sh` does not check that the NDK folders exist.
- After the vasm conversion, `_endskip` (the `rt_EndSkip` target, linked last
  to mark the end of the resident) ended up at offset 0 of a separate code
  hunk instead of at the end of the device. The build gave no warning.

## What the AI got wrong

- It first planned to build with the project's own Makefile flags
  (`-mcpu=68060`, GCC-6.50-Stable) because they were "tested on hardware",
  and only switched when the developer asked for the AKB defaults.
- It wrote the vasm sources with `section code,code`, as in the KB vasm
  example, assuming the linker would merge them into the GCC code hunk. It
  did not: the hunk name decides merging, and only `.text` merges with GCC's
  code.
- On macOS it created `bootblock.s` and then ran `rm bootblock.S`. The
  default macOS filesystem is case-insensitive, so both names are the same
  file and the new source was deleted. Renaming `.S` to `.s` on macOS needs
  `git mv` or a two-step rename, or writing the new file after removing the
  old one.
- It told the developer that the pending GCC-6.50-Dev reinstall would add
  `ndk32-include`. The install scripts show it would not.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| A vasm `-Fhunk` section named `code` or `CODE` stays a separate hunk when linked with GCC objects by `m68k-amigaos-ld`; a section named `.text` is merged into GCC's code hunk | (M) 2026-11-24 | none (host) | One C object plus a vasm object with `section <name>,code`; `objdump -h` shows 2 sections for `code`/`CODE`, 1 for `.text`; `nm` places the vasm symbol at 0 of its own hunk or after the C code |
| In lide.device, `section .text,code` gives the same layout as the old gas build: `_endskip` and `_bootblock` after the C and libc code, boot block 0x22 bytes with identical bytes | (M) 2026-11-24 | none (host) | Unstripped link of old and new objects, `nm -n`, `objdump -s` |
| The GCC-6.50-Dev install has `ndk-include` (NDK 3.2, `execbase.h` 47.2) and `ndk13-include`, no `ndk32-include` or `ndk39-include` | (M) 2026-11-24 | none (host) | `ls <prefix>/m68k-amigaos`, install built 2026-11-16 |
| The install scripts do not create `ndk32-include` or `ndk39-include` | (SRC) `GCC-6.50-Dev-MacOS.sh`, `GCC-6.50-Dev-Linux.sh` at 053c5ad10 | none | `grep ndk`; NDK only through `make all NDK=3.2` |
| A missing `-I` folder is ignored; `<exec/execbase.h>` then comes from `ndk-include` | (M) 2026-11-24 | none (host) | `m68k-amigaos-gcc -H -E` with `-I.../ndk32-include/Include_H` |
| `-m68080` accepts MOVE16 in inline assembler | (M) 2026-11-24 | none (host) | Build without `-mcpu=68060`; `objdump -d` shows 113 `move16` in the postinc variant |
| The installed vasm is 2.0g; the KB names 2.0f | (M) 2026-11-24 | none (host) | `vasmm68k_mot -v` |
| The 48.14 build with the AKB defaults (GCC-6.50-Dev, `-O2 -m68080`, vasm) works on a V4 | Developer report, 2026-11-24 | not recorded | Hardware test of the built device |
| `-O2` instead of `-Os` makes the device about 4 KB larger (28216 to 32536 bytes) | (M) 2026-11-24 | none (host) | File size of `build/scsi.device` before and after |

## Candidates for distillation

- `toolchain/target-os-headers.md` and `toolchain/c-compiler-options.md`:
  correct the NDK paths to what the install scripts create (`ndk-include` for
  NDK 3.2), or record which ApolloCrossDev version creates
  `ndk32-include/Include_H` and `ndk39-include`. Mention that a wrong NDK
  path is silent.
- ApolloCrossDev `Projects/_makefiles/Makefile`: same path fix, or a check
  that fails when `C_INCL_NDK` does not exist.
- `skills/apollo-build/scripts/find-acd.sh`: report a `PROBLEM=` when the NDK
  folder the template uses is missing.
- New `toolchain/pitfalls/vasm-section-name-hunk-merge.md`: when vasm objects
  are linked with GCC objects, use `section .text,code` (and `.data`/`.bss`)
  when the code must share GCC's hunk: resident end markers (`rt_EndSkip`),
  single-hunk devices and ROM modules, 16-bit PC-relative references between
  C and assembler. Change the example in `toolchain/vasm-assembler.md`
  accordingly or add a note to it.
- `toolchain/vasm-assembler.md`: vasm version 2.0g in current installs.
- `toolchain/c-compiler-options.md`: note that `-m68080` covers MOVE16, so
  code that used `-mcpu=68060` / `-m68060` for MOVE16 can drop it.
- `toolchain/pitfalls/gcc-misc-traps.md` or a host note: on macOS, `foo.S`
  and `foo.s` are the same file.
