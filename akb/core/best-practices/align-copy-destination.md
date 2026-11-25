---
title: Align the destination of copies and fills
type: best-practice
owner: TuKo1982
status: reviewed
origin: ai-assisted
basis: [core-developer, measured, official]
components: [cpu-68080]
applies_to:
  core: "Core 12841"
  os: [any]
tags: [68080, alignment, copy, blit, ammx, move16]
related:
  - core/cpu-68080/caches-and-memory.md
  - core/best-practices/ammx-where-it-wins.md
  - core/pitfalls/fused-copy-overlap.md
sources:
  - "TuKo1982, 68080 compilation and optimisation guide (2026-10-30), sections 0 (rules 12-13), 5.1 and 12"
  - "Gunnar (core developer), answers to questions on the guidelines, 2026-11-03"
  - "Gunnar (core developer), Simply 68080 coding guidelines, version of 2026-11-23"
  - "Gunnar (core developer), answers on the guidelines, 2026-11-24"
---

## Goal

Bandwidth: about 3.2–3.5 bytes per cycle for copies, instead of about 1.8.

## Technique

- Align the **destination** to 8 bytes (quad). A misaligned source costs only
  0–13 %; a misaligned destination 1.7–1.8x.
- Use aligned AMMX `load`/`store`, or fused quad moves
  (`move.l (a0)+,(a1)+` twice), for the bulk. Handle the misaligned head and
  tail separately.
- Use AMMX `storem` (masked store) for the edges: about 1.85 cycles per quad,
  whatever the alignment.
- Remember that P96 `AllocBitMap` bases are only 4-byte aligned.

## Evidence

Copy of a 156 x 2464-byte shape (M, Core 12841):

| Variant | Measurement | Core | Test setup |
|---|---|---|---|
| `move.l` loop | 1.7–2.0 bytes/cycle | Core 12841 | CCC |
| AMMX `load`/`store`, misaligned | About 1.8 | Core 12841 | Same |
| AMMX `load`/`store`, 8-byte aligned | 3.2–3.5 | Core 12841 | Same |
| `move16`, 16-byte aligned | 3.1–3.2 | Core 12841 | Same |
| `move16`, misaligned | About 1.75 | Core 12841 | Same |

## When not to use

- Copies are memory-bound at about 3 bytes per cycle: beyond alignment,
  optimising a blit copy gained only 3–10 %.
- `move16` is never faster than aligned AMMX or fused quad moves, so it is
  not worth the extra alignment work.
- Copies under 1 KB: don't add code to align the pointers; use a simple copy
  loop (G, 2026-11-23).
- Gunnar states that the CPU reads and writes misaligned without penalty and
  combines writes into 16-byte chunks (G, 2026-11-23). This applies to
  **Core 13000+** (G, 2026-11-24). On Core 12841 a misaligned destination
  measured 1.7–1.8x slower on 2464-byte rows (M), so on cores before 13000,
  align the destination of large copies and fills. To be re-measured on
  Core 13000+.
- Tiny shapes: for rows of 64 bytes or less, plain 68k code wins (see
  [ammx-where-it-wins.md](ammx-where-it-wins.md)).
