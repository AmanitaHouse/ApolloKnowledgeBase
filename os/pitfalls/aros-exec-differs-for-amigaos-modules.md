---
title: AROS exec differs from AmigaOS for AmigaOS ROM modules
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [libraries, devs, filesys]
applies_to:
  core: "any"
  os: [apolloos-r10]
  mode: [os-friendly]
  board: [any]
tags: [exec, waitio, iof-quick, initresident, romtag, etd, trackdisk, fat95, expansion-rom]
related:
  - os/apolloos-specific-on-v4.md
  - os/pitfalls/v4-rom-modules-and-reset.md
sources:
  - "ApolloOS-Port R8, commits ce4f7f7 (InitResident), 4a2be87 (WaitIO), 433fe9a (diskimage.device); V4 tests 2026-11-24 with EXP 48.12-beta"
  - "(SRC) AROS rom/exec/waitio.c, rom/exec/initresident.c; fat95 src/fat95.s (ChangeReport, OpenAll, DiskUpdate)"
---

## Symptom

AmigaOS modules from the Expansion ROM (fat95, exfat-handler, sagasd.device,
scsi.device) running under the AROS-based ApolloOS:

- Inserting a FAT SD card kills the V4 without an alert; booting with the
  card in hangs in dosboot.
- Modules initialised after a certain RomTag (here fat95) never start:
  exfat-handler and sagasd.device were missing after boot.
- A FAT volume turns write-protected after the first write ("not a valid
  DOS disk", then "disk is write-protected").

## Cause

| Trap | Cause |
|---|---|
| Crash on FAT insertion | fat95 sets `IOF_QUICK` on its input.device request right after OpenDevice and calls `WaitIO()` on it before it was ever sent. AmigaOS `WaitIO` returns at once for `IOF_QUICK`. AROS `WaitIO` saw `ln_Type == NT_REPLYMSG` (left by OpenDevice) and called `Remove()` on a node with NULL `ln_Succ`/`ln_Pred`: writes to address 0 and 4 (`SysBase`). |
| Later RomTags not started | An AmigaOS RomTag init routine may change `d2`-`d7`/`a2`-`a6` (fat95 does), as AmigaOS saves them around the call. AROS `InitResident` called the routine directly, and AROS `InitCode` keeps its loop state (version in `d4`, start class in `d3`, list pointer in `d2`) in those registers. |
| Write-protected FAT volume | A trackdisk-style device that lists `ETD_READ` in `NSCMD_DEVICEQUERY` gets `ETD_UPDATE` from fat95. AROS diskimage.device only handled `CMD_UPDATE`; `IOERR_NOCMD` made fat95 latch a write fault. |

## Wrong

```c
/* exec: AROS WaitIO */
if (io->io_Message.mn_Node.ln_Type == NT_REPLYMSG)
    Remove(&io->io_Message.mn_Node);       /* node never queued */

/* exec: AROS InitResident */
lib = AROS_UFC3(..., resident->rt_Init, ...); /* d2-d7/a2-a6 not saved */

/* device: ETD form missing */
case CMD_UPDATE: io->io_Error = 0; break;  /* but ETD_READ is advertised */
```

## Right

```c
/* WaitIO: as AmigaOS */
if (io->io_Flags & IOF_QUICK)
    return io->io_Error;
/* ... wait ... */
if (io->io_Message.mn_Node.ln_Type == NT_REPLYMSG &&
    io->io_Message.mn_Node.ln_Succ != NULL)
    { Disable(); Remove(&io->io_Message.mn_Node); Enable(); }

/* InitResident: movem.l d2-d7/a2-a6 around jsr (a1) */

/* device: every ETD_ form of an advertised command */
case CMD_UPDATE: case ETD_UPDATE:
case CMD_CLEAR:  case ETD_CLEAR:
case TD_MOTOR:   case ETD_MOTOR:
    io->io_Error = 0; break;
```

All three are fixed in ApolloOS R10. Releases before R10 (R9.x) still have
the first two; code meant for them must not `WaitIO()` a request that was
never sent, and RomTag init code must save the registers it uses.

## Detection

- A V4 crash without an alert right after a device event: check for writes
  to address 0/4 (`SysBase` overwritten); trace the handler with
  `RawPutChar` markers.
- A RomTag that is in the resident list but never initialised: look for the
  module initialised just before it and compare its register use with the
  AmigaOS ABI.
- A device driver that answers `NSCMD_DEVICEQUERY`: every command it lists
  in an `ETD_` form must also be handled in that form.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| fat95 calls `WaitIO` on an unsent `IOF_QUICK` request; AROS removed the unqueued node | (M) 2026-11-24, (SRC) fat95.s ChangeReport | Core 12856 | Traced fat95 build on a V4; request dump: `ln_Type` 7, `io_Flags` 1, succ/pred 0; fixed WaitIO: FAT image and FAT32 SD mount, hot-swap OK |
| fat95 init changes `d4`; AROS InitCode loses its loop state | (M) 2026-11-24 | Core 12856 | exfat-handler and sagasd.device not started; started after InitResident saved d2-d7/a2-a6 |
| diskimage.device without `ETD_UPDATE` makes fat95 write-protect the volume | (M) 2026-11-24, (SRC) fat95.s DiskUpdate | Core 12856 | Copy/MakeDir on a fat95-mounted FAT16 image fail, pass after the fix; `fsck_msdos` clean |
