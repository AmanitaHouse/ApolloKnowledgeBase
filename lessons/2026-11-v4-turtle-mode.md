---
title: Turtle mode on the V4 - what it slows down and what it does to the counters
type: lesson
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured]
components: [cpu-68080, hardware]
applies_to:
  core: "Core 12856"
  os: [apolloos-r10]
  mode: [any]
  board: [v4-unicorn]
tags: [turtle, apollocontrol, pcr, ccc, iep, counters, superscalar, benchmark, speed]
related:
  - core/cpu-68080/performance-counters.md
  - core/cpu-68080/core-at-a-glance.md
  - guides/benchmark-method.md
  - guides/testing-on-v4-hardware.md
sources:
  - "Probe programs run remotely on a V4 UniCorn, Core 12856, ApolloOS R10 dev card, 2026-11-25: one run per mode (full speed, TU=3, TU=2, TU=1), each after a power cycle"
  - "ApolloControl 2.23 (28.10.2026) template: TU=TURTLE/N 0=Off, 1=A500, 2=A1200, 3=A4000"
distilled_into:
  - core/pitfalls/turtle-mode-counters.md
  - core/cpu-68080/performance-counters.md
  - core/cpu-68080/core-at-a-glance.md
  - guides/testing-on-v4-hardware.md
---

## Project

Measuring how a V4 behaves in each Turtle mode, as part of probing the
68080 for a debugging and remote-control tool. Done by Claude (AI) with
WDrijver on 2026-11-24 and 2026-11-25, on the V4 UniCorn test machine
(Core 12856, ApolloOS R10 dev card, RTG Workbench). Each mode was set
with `ApolloControl TU=n` right after a power cycle, then the same probe
programs ran: counted loops read with CCC and IEP1-IEP3, a timing of
CCC against the E-clock, PCR reads, and the trace bits.

## What went well

- `ApolloControl TU=n` switches the mode at once, without a reboot, and
  a power cycle returns to full speed (TU=0).
- The network stack, a remote shell and file transfers kept working in
  every Turtle mode, just slower, so the whole run could be unattended.
- The same counted loops in every mode gave clean, repeatable numbers
  (5 runs per loop, within a few percent).

## What went wrong

- In Turtle 1, a 60-second CPU-bound loop kept the V4 from answering on
  the network for about two minutes. A remote runner with a short
  timeout took that for a hang and power-cycled a machine that was
  still working. (Observation, one occurrence.)
- A remote directory listing that takes well under a second at full
  speed did not finish within 30 s in Turtle 1, so a script with fixed
  timeouts lost its results. Timeouts that suit full speed are too short
  in Turtle mode.

## What the AI got wrong

- **It measured the slowdown with a network-bound job.** Timing a small
  remote job (a file hash over the network) gave 4x, 12x and 22x for
  TU=3, 2, 1. Counted CPU loops show 4.5x, 89x and 177x: the network
  part hid most of the slowdown in Turtle 1 and 2.
- **It expected a lower clock.** A MHz value estimated from the board's
  multiplier reads 99.2 MHz in every mode, and CCC really does run at
  99.3 MHz in every mode. Turtle does not lower the clock; it makes each
  instruction take more cycles.
- **It trusted PCR bit 0 for the number of pipes.** PCR bit 0 (second
  pipe) stays 1 in every Turtle mode, yet IEP2 stays 0: only one pipe
  issues.
- **It read IEP1 as an instruction count.** In Turtle mode IEP1 follows
  CCC (94-97 % of it), so it counts cycles, not instructions: 2.5, 48 and
  96 counts per real instruction in TU=3, 2, 1.

## Evidence

All (M): V4 UniCorn, Core 12856, ApolloOS R10, 2026-11-25. Loops of
224007 independent ALU instructions, 32768 memory instructions and
112003 instructions with branches, read with `movec` CCC/IEP1/IEP2 in
user mode, 5 runs each (run 0 shown, the others within 4 %).

| Claim | Source | Core | Method |
|---|---|---|---|
| Independent ALU loop takes 128185 / 581499 / 11405896 / 22721312 CCC at full speed / TU=3 / TU=2 / TU=1: 1.0x / 4.5x / 89x / 177x | (M) | Core 12856 | counted loop, CCC |
| Memory loop: 16697 / 82644 / 1411433 / 2879166 CCC (1.0x / 4.9x / 85x / 172x); branch loop: 96183 / 625994 / 5717206 / 11239674 CCC (1.0x / 6.5x / 59x / 117x) | (M) | Core 12856 | counted loops, CCC |
| CCC runs at 99.32 MHz in every mode, working and sleeping (within 1 %) | (M) | Core 12856 | CCC against the E-clock over timer waits |
| Only one pipe issues in TU=1, 2 and 3: IEP2 = 0; at full speed IEP1 + IEP2 = 224017 for 224007 instructions | (M) | Core 12856 | IEP1, IEP2 over the independent loop |
| In Turtle mode IEP1 is 94-97 % of CCC (564686, 10874762, 21430313 for TU=3, 2, 1), not the instruction count | (M) | Core 12856 | IEP1 against CCC, same loop |
| PCR reads `$04400101` at full speed, `$04400141` in TU=3, `$044001C1` in TU=2, `$04400181` in TU=1: bits 7-6 change with the mode, bit 0 stays 1 | (M) | Core 12856 | `movec` PCR in supervisor and user mode (same value) |
| Trace bits behave the same in every mode: T1 gives a trace exception per instruction (6 of 6), T0 gives none | (M) | Core 12856 | trace test with T1, then T0 |
| A remote file hash took 0.04 / 0.15 / 0.47 / 0.88 s at full speed / TU=3 / TU=2 / TU=1 | (M) | Core 12856 | same small file, over the network |

## Candidates for distillation

- `core/cpu-68080/performance-counters.md`: add that in Turtle mode IEP1
  counts cycles, IEP2 reads 0, and the pipe-count rule ("IEP2 < n/16: 1
  pipe") answers 1 pipe; CCC keeps its rate. Add the PCR bits 7-6 values
  per mode (needs a check on another core before it becomes a rule).
- New `core/pitfalls/turtle-mode-counters.md`: DON'T benchmark or count
  instructions in Turtle mode; check PCR bits 7-6 (or set TU=0) before
  timing code, and don't read PCR bit 0 as "two pipes are issuing".
- `guides/testing-on-v4-hardware.md`: remote timeouts in Turtle mode
  (minutes, not seconds), and measure the slowdown with a CPU loop, not
  a network job.
- `core/cpu-68080/core-at-a-glance.md`: one line on Turtle mode (single
  issue, same clock, 4.5x / 89x / 177x slower for TU=3 / 2 / 1 on
  Core 12856).
