---
title: Turtle mode changes what the performance counters mean
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured]
components: [cpu-68080]
applies_to:
  core: "Core 12856"
  os: [any]
  board: [v4-unicorn]
tags: [68080, turtle, apollocontrol, pcr, ccc, iep, counters, benchmark, superscalar]
related:
  - core/cpu-68080/performance-counters.md
  - core/cpu-68080/core-at-a-glance.md
  - guides/benchmark-method.md
sources:
  - "lessons/2026-11-v4-turtle-mode.md"
---

## Symptom

- A benchmark or a pipe test gives numbers far off the usual ones: code
  runs 4.5 to 177 times slower, the pipe test says "1 pipe", and IEP1 is
  2.5 to 96 times the number of instructions run.
- PCR bit 0 still says the second pipe is on, so the result looks like a
  core fault instead of a mode.

## Cause

Turtle mode (`ApolloControl TU=1`, `2` or `3`: A500, A1200, A4000 speed)
slows the 68080 down without lowering its clock:

- CCC keeps counting at 99.3 MHz in every mode.
- Only one pipe issues: IEP2 reads 0. PCR bit 0 stays 1 all the same.
- IEP1 then counts about one per cycle (94-97 % of CCC), not one per
  instruction.
- Each instruction takes more cycles. Counted loops on Core 12856:

| Mode | Independent ALU | Memory | Branches |
|---|---|---|---|
| Turtle off (TU=0) | 1x | 1x | 1x |
| TU=3 (A4000) | 4.5x | 4.9x | 6.5x |
| TU=2 (A1200) | 89x | 85x | 59x |
| TU=1 (A500) | 177x | 172x | 117x |

PCR bits 7-6 show the mode: `00` off, `01` TU=3, `11` TU=2, `10` TU=1.

## Wrong

```asm
; Time a routine and count pipes, whatever mode the machine is in.
    movec   ccc,a6
    bsr     routine
    movec   ccc,d7
    sub.l   a6,d7          ; in Turtle mode: up to 177x the real cost
    movec   iep1,d0        ; in Turtle mode: cycles, not instructions
```

## Right

```asm
; Check PCR bits 7-6 first (readable in user mode on Core 12856).
    movec   pcr,d0         ; PCR ($808)
    and.w   #$00c0,d0      ; bits 7-6: 0 = Turtle off
    bne     .turtle        ; Turtle on: report it, don't benchmark
    movec   ccc,a6
    bsr     routine
    movec   ccc,d7
    sub.l   a6,d7
```

Or set `ApolloControl TU=0` before measuring, and note the mode with every
result.

## Detection

- Read PCR before a benchmark run and log it: `$04400101` at full speed on
  Core 12856; `$04400141`, `$044001C1` or `$04400181` in Turtle mode.
- IEP2 = 0 while PCR bit 0 = 1 means Turtle mode (or a fault), not a
  single-pipe core.
- A remote job over the network shows much less slowdown (4x, 12x, 22x
  for a small file hash): measure the mode with a counted CPU loop.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| Counted loops run 4.5x / 89x / 177x slower in TU=3 / 2 / 1 (independent ALU loop: 128185 / 581499 / 11405896 / 22721312 CCC) | (M) 2026-11-25 | Core 12856, V4 UniCorn, ApolloOS R10 | 224007-instruction loop, CCC, 5 runs per mode, each mode set after a power cycle; see the lesson |
| CCC runs at 99.32 MHz in every mode | (M) 2026-11-25 | Core 12856 | CCC against the E-clock over timer waits, working and sleeping |
| IEP2 = 0 in every Turtle mode, while PCR bit 0 = 1 | (M) 2026-11-25 | Core 12856 | IEP1/IEP2 over the same loop; `movec` PCR in user and supervisor mode |
| IEP1 is 94-97 % of CCC in Turtle mode | (M) 2026-11-25 | Core 12856 | IEP1 564686 / 10874762 / 21430313 against CCC 581499 / 11405896 / 22721312 |
| PCR reads `$04400101`, `$04400141`, `$044001C1`, `$04400181` for TU=0, 3, 2, 1 | (M) 2026-11-25 | Core 12856 | `movec` PCR, one run per mode; other cores not checked |
