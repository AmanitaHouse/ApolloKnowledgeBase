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
---

## Summary

ApolloCrossDev project Makefiles select Amiga NDK headers through
`C_INCL_NDK`. Choose the NDK path that matches the oldest target OS of the
project. The documented installer does **not** create the version-specific
directories those Makefiles name. Build readiness must check the path the
Makefile actually references.

## Details

### Paths the project Makefile names

ApolloCrossDev `Projects/_makefiles/Makefile` (v1.0 and both inspected v1.2
blobs) comments or activates these `C_INCL_NDK` values:

| Intended NDK | Makefile path | Use when the Target OS includes |
|---|---|---|
| 3.2 (template default) | `<prefix>/m68k-amigaos/ndk32-include/Include_H` | `amigaos-3.2`, `apolloos-r10` |
| 3.9 | `<prefix>/m68k-amigaos/ndk39-include` | `amigaos-3.9` |
| 1.3 | `<prefix>/m68k-amigaos/ndk13-include` | none of the supported targets |

A directory name does not prove which NDK archive was unpacked into it.
Confirm content only from the install procedure or from the archive that
was installed.

### What the inspected installer produces

`GCC-6.50-Dev-Linux.sh` (and the other GCC-6.50 install scripts inspected at
ApolloCrossDev `6db8ff8` and `605007e`) run amiga-gcc with `NDK=3.2`. That
selects the NDK 3.2 download in amiga-gcc. amiga-gcc then installs the
selected headers under:

| Produced path | Role in amiga-gcc |
|---|---|
| `<prefix>/m68k-amigaos/ndk-include` | Destination for the selected NDK (`NDK=3.2` by default; `NDK=3.9` would still land here) |
| `<prefix>/m68k-amigaos/ndk13-include` | Tree derived from that selected NDK for Kickstart 1.3-era headers |

ApolloCrossDev PART 7 clones DevPac into the prefix. It does not create
`ndk32-include` or `ndk39-include`.

So a completed run of the documented installer is **not** sufficient, by
itself, to satisfy a Makefile that requires
`ndk32-include/Include_H` or `ndk39-include`. Presence of `ndk-include`
does not satisfy those paths, and it does not show that NDK 3.9 headers
are available.

ApolloCrossDev still builds its runtime libraries with `NDK=3.2`
(`make all NDK=3.2` in the install script).

### Which Makefile NDK for which target

- Targets `amigaos-3.2` and/or `apolloos-r10`: activate the Makefile's NDK
  3.2 line (`ndk32-include/Include_H`). ApolloOS R10 aims to be compatible
  with AmigaOS 3.2.x.
- Target includes `amigaos-3.9`: activate the Makefile's NDK 3.9 line
  (`ndk39-include`), so functions that AmigaOS 3.9 does not have are not
  declared, and calling them gives a compiler warning or error instead of
  a crash at run time.

After selecting the line, confirm that directory exists under the effective
project `PREFIX`. If it is missing, compilation is blocked until the
ApolloCrossDev maintainer's intended provisioning step for that path is
followed. Do not retarget `C_INCL_NDK` to `ndk-include` and call the build
successful.

### Why it matters

NDK 3.2 headers declare functions added in AmigaOS 3.2. A program built
against them for AmigaOS 3.9 can compile and link without errors, but fails
at run time when it calls a function that 3.9 does not have. Using the
wrong include directory, or a generic `ndk-include` tree of unknown
provenance, hides that mismatch.

## Differences from AmigaOS / AROS / 68060

- DON'T use the AROS SDK headers for Apollo V4 programs. Use the NDK that
  matches the target OS.
- DON'T treat `m68k-amigaos/ndk-include` as a documented substitute for
  `ndk39-include` or `ndk32-include/Include_H`.

## Do / Don't

- DO pick the Makefile NDK line from the project's target OS list.
- DO verify that path under the effective compiler `PREFIX` before treating
  the project as build-ready.
- DON'T call a function that is missing in one of the project's target
  operating systems.
- DON'T assume the installer created `ndk32-include` or `ndk39-include`.
