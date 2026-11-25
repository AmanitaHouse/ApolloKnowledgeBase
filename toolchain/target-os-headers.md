---
title: NDK headers per target OS
type: reference
owner: WDrijver
status: reviewed
origin: ai-assisted
components: [toolchain]
applies_to:
  core: "any"
  os: [apolloos-r10, amigaos-3.9, amigaos-3.2]
tags: [ndk, headers, target-os]
related:
  - toolchain/c-compiler-options.md
  - toolchain/project-makefile.md
  - os/apolloos-and-amigaos-on-v4.md
sources:
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile (C_INCL_NDK paths on v1.0 at 6db8ff8 and v1.2 at d636629 / d571781 / 605007e)"
  - "github.com/WDrijver/ApolloCrossDev GCC-6.50-Dev-Linux.sh (NDK=3.2; PART 7 clones DevPac only; inspected at 6db8ff8 and 605007e)"
  - "github.com/WDrijver/amiga-gcc amiga-gcc-stable Makefile (NDK destination ndk-include / ndk13-include; local install tree at 81514368)"
  - "WDrijver (ApolloCrossDev maintainer), 2026-11-02"
  - "github.com/WDrijver/ApolloCrossDev pull request #38 (2026-11-25, fixes issue #32): the GCC-6.50 scripts install ndk-include (NDK 3.2) and ndk13-include, not ndk32-include or ndk39-include"
  - "lessons/2026-11-lide-device.md (found the missing folders, 2026-11-24)"
---

## Summary

The GCC-6.50 scripts of ApolloCrossDev install the Amiga NDK headers for
versions 3.2 (the default, under `m68k-amigaos/ndk-include`) and 1.3
(`m68k-amigaos/ndk13-include`). They do not install NDK 3.9. For a project
that also targets AmigaOS 3.9 using the installed NDK 3.2 headers, check by
hand that every OS function it calls exists on 3.9. Build readiness checks
the exact NDK directory referenced by the active, wired `C_INCL_NDK` in the
project Makefile.

## Details

### Paths the project Makefile names

ApolloCrossDev `Projects/_makefiles/Makefile` (since pull request #38,
2026-11-25) and older templates comment or activate these `C_INCL_NDK`
values:

| Intended NDK | Makefile path | Use when the Target OS includes |
|---|---|---|
| 3.2 (default) | `<prefix>/m68k-amigaos/ndk-include` | `amigaos-3.2`, `apolloos-r10`, and `amigaos-3.9` with a manual check |
| 1.3 | `<prefix>/m68k-amigaos/ndk13-include` | none of the supported targets |
| 3.9 (explicit, user-supplied) | `<prefix>/m68k-amigaos/ndk39-include` | only when a project explicitly requires NDK 3.9-specific headers |

`ndk-include` is also on GCC's built-in include path, so a wrong or missing
`-I` for the NDK does not give an error: GCC silently uses NDK 3.2.
Makefile templates prior to ApolloCrossDev pull request #38 (2026-11-25)
pointed at `ndk32-include/Include_H` and a commented `ndk39-include` line;
neither folder is installed by the standard installer.

ApolloCrossDev builds its runtime libraries against NDK 3.2
(`make all NDK=3.2`).

### What the inspected installer produces

`GCC-6.50-Dev-Linux.sh` (and the other GCC-6.50 install scripts) run
amiga-gcc with `NDK=3.2`. amiga-gcc installs those headers under:

| Produced path | Role in amiga-gcc |
|---|---|
| `<prefix>/m68k-amigaos/ndk-include` | Destination for the selected NDK (`NDK=3.2` by default) |
| `<prefix>/m68k-amigaos/ndk13-include` | Tree derived from that selected NDK for Kickstart 1.3-era headers |

ApolloCrossDev PART 7 clones DevPac into the prefix. It does not create
`ndk32-include` or `ndk39-include`.

So:

- When a project Makefile selects `m68k-amigaos/ndk-include` and that
  directory exists under the effective compiler `PREFIX`, the NDK 3.2
  requirement is satisfied.
- Presence of `ndk-include` does **not** satisfy an explicit
  `ndk39-include` requirement or an unupdated pre-PR-#38
  `ndk32-include/Include_H` path, and does not show that NDK 3.9 headers
  are available.

### Which Makefile NDK for which target

- Targets `amigaos-3.2` and/or `apolloos-r10`: NDK 3.2 (`ndk-include`).
  ApolloOS R10 aims to be compatible with AmigaOS 3.2.x.
- Target includes `amigaos-3.9`: NDK 3.2 (`ndk-include`) by default, as the
  standard installer provides no NDK 3.9 install. Check each OS function
  the program calls against `os/apolloos-and-amigaos-on-v4.md`.
- Projects that genuinely require NDK 3.9-specific headers may explicitly
  configure `C_INCL_NDK` for `ndk39-include`, and build readiness remains
  blocked unless `<prefix>/m68k-amigaos/ndk39-include` is provisioned on
  disk.

After selecting the active `C_INCL_NDK` line, confirm that directory exists
under the effective project `PREFIX`. If it is missing, compilation is
blocked until that directory is provisioned (or, for a legacy
`ndk32-include/Include_H` Makefile intending NDK 3.2, `C_INCL_NDK` is
updated to `ndk-include`).

### Why it matters

NDK 3.2 headers declare functions added in AmigaOS 3.2. A program built
against them for AmigaOS 3.9 can compile and link without errors, but fails
at run time when it calls a function that 3.9 does not have. When an
explicit `ndk39-include` path is missing, GCC's silent fallback to
`ndk-include` hides that mismatch unless the path is verified beforehand.

## Differences from AmigaOS / AROS / 68060

- DON'T use the AROS SDK headers for Apollo V4 programs. Use the NDK that
  matches the target OS.
- DON'T treat `m68k-amigaos/ndk-include` as a documented substitute for
  an explicit `ndk39-include` requirement.

## Do / Don't

- DO use `ndk-include` (NDK 3.2) for supported targets by default, and check
  AmigaOS 3.9 compatibility manually against
  `os/apolloos-and-amigaos-on-v4.md`.
- DO verify that the active `C_INCL_NDK` directory exists under the
  effective compiler `PREFIX` before treating the project as build-ready.
- DON'T point `-I` at `ndk32-include` or `ndk39-include` unless that
  directory is actually installed under `PREFIX`: GCC falls back to NDK 3.2
  without a warning.
- DON'T call a function that is missing in one of the project's target
  operating systems.
- DON'T assume the installer created `ndk32-include` or `ndk39-include`.
