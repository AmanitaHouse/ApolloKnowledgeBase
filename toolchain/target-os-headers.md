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
  - os/apolloos-and-amigaos-on-v4.md
sources:
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile"
  - "github.com/WDrijver/ApolloCrossDev GCC-6.50-Dev-Linux.sh"
  - "WDrijver (ApolloCrossDev maintainer), 2026-11-02"
  - "github.com/WDrijver/ApolloCrossDev pull request #38 (2026-11-25, fixes issue #32): the GCC-6.50 scripts install ndk-include (NDK 3.2) and ndk13-include, not ndk32-include or ndk39-include"
  - "lessons/2026-11-lide-device.md (found the missing folders, 2026-11-24)"
---

## Summary

The GCC-6.50 scripts of ApolloCrossDev install the Amiga NDK headers for
versions 3.2 (the default) and 1.3. They do not install NDK 3.9. For a
project that also targets AmigaOS 3.9, check by hand that every OS function
it calls exists on 3.9.

## Details

### Installed NDKs

| NDK | Include path | Target OS |
|---|---|---|
| 3.2 (default) | `<prefix>/m68k-amigaos/ndk-include` | `amigaos-3.2`, `apolloos-r10`, and `amigaos-3.9` with a manual check |
| 1.3 | `<prefix>/m68k-amigaos/ndk13-include` | none of the supported targets |

`ndk-include` is also on GCC's built-in include path, so a wrong or missing
`-I` for the NDK does not give an error: GCC silently uses NDK 3.2. The
Makefile template up to ApolloCrossDev pull request #38 (2026-11-25) pointed
at `ndk32-include/Include_H` and an `ndk39-include` line; neither folder is
installed.

ApolloCrossDev builds its runtime libraries against NDK 3.2
(`make all NDK=3.2`).

### Which NDK for which target

- Targets `amigaos-3.2` and/or `apolloos-r10`: NDK 3.2. ApolloOS R10 aims to
  be compatible with AmigaOS 3.2.x.
- Target includes `amigaos-3.9`: NDK 3.2, as there is no NDK 3.9 install.
  The compiler then does not catch functions that AmigaOS 3.9 lacks, so
  check each OS function the program calls against
  `os/apolloos-and-amigaos-on-v4.md`.

### Why it matters

The NDK 3.2 headers declare functions added in AmigaOS 3.2. A program built
against them for AmigaOS 3.9 compiles and links without errors, but fails at
run time when it calls a function that 3.9 does not have.

## Differences from AmigaOS / AROS / 68060

- DON'T use the AROS SDK headers for Apollo V4 programs. Use the NDK that
  matches the target OS.

## Do / Don't

- DO use `ndk-include` (NDK 3.2) for every supported target.
- DON'T point `-I` at `ndk32-include` or `ndk39-include`: they are not
  installed, and GCC falls back to NDK 3.2 without a warning.
- DON'T call a function that is missing in one of the project's target
  operating systems.
