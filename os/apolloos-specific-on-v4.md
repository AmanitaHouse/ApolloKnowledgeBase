---
title: ApolloOS-specific on Apollo V4
type: reference
owner: WDrijver
status: reviewed
origin: ai-assisted
components: [general]
applies_to:
  core: "any"
  os: [apolloos-r10]
related:
  - os/apolloos-and-amigaos-on-v4.md
  - os/pitfalls/aros-exec-differs-for-amigaos-modules.md
sources:
  - "ApolloOS-Port R8 (D20), commits daf5bad, c29d71a, 0747763, 15a0ea4; V4 test 2026-11-24"
---

## Summary

What is specific to ApolloOS R10: features that only ApolloOS offers, and
where ApolloOS differs from AROS (m68k), the code base it was forked from.
Only relevant for projects that target ApolloOS alone, and for work on
ApolloOS itself (github.com/ApolloTeam-dev/ApolloOS.R10). Programs that also
target AmigaOS 3.9 or 3.2 should follow `os/apolloos-and-amigaos-on-v4.md`
instead.

**This file has no content yet.** If your task depends on it, tell the user
that the knowledge base does not cover ApolloOS-specific topics yet.

## Details

### Architecture

No content yet.

### Libraries

No content yet.

### Devices

ApolloOS R10 has no storage drivers of its own. It uses the ones it shares
with AmigaOS, from the Expansion ROM (EXP) at `$F00000`-`$F2FFFF`: the
192 KB area that C:ApolloExpROM flashes and ApolloUpdate always flashes
together with the ROM.

- At boot the ROM scans the EXP for RomTags, but takes only five of them,
  by name: `scsi.device` (IDE/CF), `sagasd.device` (SD card),
  `ptable.library`, `fat95` and `exfat-handler`. The AmigaOS-only modules in
  the EXP (68040/680x0.library, processor.resource, vampire.resource,
  VampireSupport, VampireFastMem) are skipped; ApolloOS keeps its own
  processor and vampire resources.
- There is no fallback: the AROS ata.device, sagasd.device, gayle_ata and
  storage hidds were removed. A V4 without a current EXP has no disk
  drivers under ApolloOS R10.
- The IDE driver keeps the name `scsi.device`; open that name, not
  `ata.device`.
- dosboot does not scan partitions. Drives are mounted from their RDB (or,
  for FAT/exFAT cards, by the EXP drivers) as on AmigaOS.

### Filesystems

FAT volumes are served by `fat95` from the EXP, exFAT by `exfat-handler`
from the EXP. The AROS fat-handler is not part of R10. A mountlist for a
FAT partition names no `FileSystem`: DosType `0x46415400` ("FAT\0") finds
fat95 through FileSystem.resource.

### Commands

No content yet.

### Datatypes

No content yet.

### Build structure

No content yet.

## Differences from AmigaOS / AROS / 68060

- AROS m68k stopped scanning `$F00000`-`$F80000` for RomTags in 2024;
  ApolloOS R10 scans `$F00000`-`$F2FFFF` again, with the name whitelist
  above (see Devices).
- AmigaOS ROM modules run in an AROS exec. Where AROS exec behaved
  differently, R10 follows AmigaOS: see
  `os/pitfalls/aros-exec-differs-for-amigaos-modules.md`.

## Do / Don't

- DON'T assume AROS behavior applies to ApolloOS without checking this file
  or the ApolloOS.R10 source.
