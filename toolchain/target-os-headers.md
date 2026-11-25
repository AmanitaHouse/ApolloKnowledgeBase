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
  - "github.com/WDrijver/ApolloCrossDev Projects/_makefiles/Makefile (pull request #38, commit c1fba26 / 57cb85c, 2026-11-25)"
  - "github.com/WDrijver/ApolloCrossDev GCC-6.50-Dev-Linux.sh"
  - "github.com/WDrijver/ApolloCrossDev issue #32 (WDrijver decision, 2026-11-25)"
  - "WDrijver (ApolloCrossDev maintainer), 2026-11-02"
---

## Summary

ApolloCrossDev installs the Amiga NDK 3.2 headers at `ndk-include` (default)
and the NDK 1.3 headers at `ndk13-include`. It does **not** install
`ndk39-include` or `clib2/include`. Assess any project's need for
AmigaOS 3.9-specific headers separately before configuring `C_INCL_NDK`.

## Details

### Installed NDKs

From ApolloCrossDev pull request #38 (`c1fba26`, 2026-11-25), the project
Makefile template and project Makefiles match the `amiga-gcc` layout that
the GCC-6.50 install scripts produce (`make all NDK=3.2`):

| NDK | Include path | Installed by ApolloCrossDev | Target OS |
|---|---|---|---|
| 3.2 (default) | `<prefix>/m68k-amigaos/ndk-include` | yes | `amigaos-3.2`, `apolloos-r10` (and general APIs on `amigaos-3.9`) |
| 1.3 | `<prefix>/m68k-amigaos/ndk13-include` | yes | none of the supported V4 targets |
| 3.9 | `<prefix>/m68k-amigaos/ndk39-include` | no | optional, if a project supplies NDK 3.9 headers itself |

Earlier ApolloCrossDev Makefiles named `ndk32-include/Include_H` as the
default `C_INCL_NDK`. The GCC-6.50 install scripts never created that
directory; builds succeeded only because GCC's built-in include search path
already contains `m68k-amigaos/ndk-include` and GCC silently ignores `-I`
directories that do not exist. Pull request #38 switched `C_INCL_NDK` to
`$(PREFIX)/$(TARGET)/ndk-include` and marked `ndk39-include` (and
`clib2/include`) as `# NOT installed by ApolloCrossDev`.

ApolloCrossDev builds its runtime libraries against NDK 3.2
(`make all NDK=3.2`).

### Which NDK for which target

- Targets `amigaos-3.2` and/or `apolloos-r10`: use the installed NDK 3.2 at
  `<prefix>/m68k-amigaos/ndk-include`. ApolloOS R10 aims to be compatible
  with AmigaOS 3.2.x.
- Target includes `amigaos-3.9`: assess the project's header needs
  separately. ApolloCrossDev does not install NDK 3.9; its scripts install
  NDK 3.2, which covers AmigaOS 3.9 and later but also declares functions
  added in AmigaOS 3.2. If a project requires strict compile-time
  enforcement against AmigaOS 3.2-only APIs, obtain and install NDK 3.9
  headers separately and point `C_INCL_NDK` at that directory.

### Why it matters

The NDK 3.2 headers declare functions added in AmigaOS 3.2. A program built
against them for AmigaOS 3.9 compiles and links without errors, but fails at
run time when it calls a function that 3.9 does not have. Because GCC
silently skips nonexistent `-I` directories, uncommenting an uninstalled
`ndk39-include` line in a Makefile does not switch headers — GCC quietly
falls back to its built-in `ndk-include` (NDK 3.2).

## Differences from AmigaOS / AROS / 68060

- DON'T use the AROS SDK headers for Apollo V4 programs. Use the Amiga NDK
  headers that match the project's target OS policy.

## Do / Don't

- DO use `<prefix>/m68k-amigaos/ndk-include` for NDK 3.2 on current
  ApolloCrossDev installs.
- DO verify that any custom `C_INCL_NDK` directory (such as a user-supplied
  NDK 3.9 tree) actually exists before relying on it for compile-time API
  checks.
- DON'T assume ApolloCrossDev installs `ndk39-include` or `clib2/include`.
- DON'T call a function that is missing in one of the project's target
  operating systems.
