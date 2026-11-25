---
title: LowRes with 8 bitplanes stays blank while BPLCON0 ECSENA is set
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured]
components: [saga-video-isabelle]
applies_to:
  core: "Core 12856"
  os: [any]
  mode: [any]
  board: [v4-unicorn]
last_verified: 2026-11-24
tags: [aga, bplcon0, ecsena, lowres, 256-colours, ham8, copper, planar]
related:
  - core/saga-registers/chunky-plane.md
sources:
  - "ApolloOS-Port, arch/m68k-amiga/hidd/amigavideo/amigavideo_chipset.c, commit f93703c1 (2026-11-24)"
  - "Hardware test on a V4 Unicorn, Core 12856: BPLCON0 patched in the live copper list"
---

## Symptom

An AGA LowRes screen with 8 bitplanes (256 colours or HAM8) shows only the
border colour: the whole display window is one flat colour (colour 0),
although the copper list, the bitplane pointers and the bitmap data are
right. The system keeps running. The same screen in HiRes or SuperHiRes
with 8 planes shows, and LowRes with 1 to 7 planes shows.

## Cause

On this core, BPLCON0 bit 0 (ECSENA, "enable BPLCON3 features") together
with BPU3 (bit 4, 8 planes) and HIRES/SHRES clear blanks the bitplane
display. The same value with ECSENA clear shows the picture. Classic AGA
(Lisa) shows both. The SAGA register documentation lists only the OCS bits
of BPLCON0 (no ECSENA, no BPU3), so this is not documented behaviour.

The AROS-derived `amigavideo.hidd` sets ECSENA in every copper list
(`bplcon0_null = system_bplcon0 | 1`), which runs into this.

## Wrong

```c
/* copper list: LowRes, 8 planes, ECSENA set */
COPPEROUT(c, 0x0100, 0x0211);   /* BPU3 | COLOR | ECSENA: blank display */
```

## Right

```c
/* LowRes with 8 planes: leave ECSENA out of BPLCON0 */
UWORD bplcon0 = 0x0210;         /* BPU3 | COLOR: 256 colours show */
if (depth > 7 && lowres)
    bplcon0 &= ~0x0001;
```

## Detection

A LowRes 256-colour or HAM8 screen that comes up as one flat colour while
`info screens` / the screen list shows it open with depth 8. Read the
copper list (GfxBase->LOFlist) and check BPLCON0 for `0x0211` (or
`0x0215` interlaced).

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| LowRes 8 planes with BPLCON0 `0x0211` shows only colour 0; the same copper list with `0x0210` shows the 256-colour Workbench | (M) 2026-11-24 | Core 12856 | Workbench on PAL:LowRes depth 8; one word of the live copper list in chip RAM poked with rxnet, screen captured after each value |
| LowRes 2, 6, 7 planes and HiRes 2, 8 planes show with ECSENA set | (M) 2026-11-24 | Core 12856 | Same Workbench, screen mode switched through ENV:Sys/screenmode.prefs |
| SAGA BPLCON0 documentation lists no ECSENA and no BPU3 | (official) sagadoc bplcon0.htm | any | Read |
