---
title: Clearing the data-cache enable bit does not turn the data cache off
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured]
components: [cpu-68080]
applies_to:
  core: "Core 12856"
  os: [any]
tags: [68080, cache, cacr, cachecontrol, enabled, data-cache]
related:
  - core/cpu-68080/caches-and-memory.md
  - core/pitfalls/self-modifying-code-and-caches.md
sources:
  - "Hardware test tools/v4/tests/dcache-enable-bit, V4 UniCorn, Core 12856, ApolloOS R10, 2026-11-17"
---

## Symptom

- Code clears the data-cache enable bit and expects uncached reads. Reads
  still hit the cache and stay just as fast.
- Tools that show the data cache state from `CacheControl()` or CACR report
  "data cache off" while the data cache is in use.

## Cause

- CACR bit 31 (DE, `CACRF_EnableD` through `CacheControl()`) can be written and
  read back: the raw CACR changes from `$00008000` to `$80008000` and back.
- Load latency does not change with it. A dependent load that hits a 64 KB
  buffer costs 3 cycles with the bit clear or set. A 4 MB buffer that cannot
  fit costs about 28.6 cycles per load (M).
- So the core keeps its data cache on whatever the bit says.

## Wrong

```c
/* Read a buffer uncached, e.g. to see what a bus master wrote. */
ULONG old = CacheControl(0, CACRF_EnableD);   /* "data cache off" */
check(buffer);                                 /* may still read cached lines */
CacheControl(old, CACRF_EnableD);
```

## Right

Do not rely on the enable bit for uncached access or to slow a program
down. Assume the data cache is always on. Whether `CachePreDMA()` /
`CachePostDMA()` or `CacheClearE()` keep data written by other bus masters
coherent on the 68080 is not covered by this measurement.

## Detection

Search for `CACRF_EnableD`, `CacheControl(` with a mask that includes it,
and `movec` writes to `cacr` that clear bit 31. Measure with
`tools/v4/tests/dcache-enable-bit`.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| CACR bit 31 is writable and reads back | (M) 2026-11-17 | Core 12856, V4 UniCorn | `tools/v4/tests/dcache-enable-bit`: raw CACR found `$00008000`, after `CacheControl(CACRF_EnableD, CACRF_EnableD)` `$80008000`, restored `$00008000` |
| Bit 31 does not change data-load latency | (M) 2026-11-17 | Core 12856, V4 UniCorn | Same test, under `Disable()`: pointer chase, one load per 64-byte line in random order, 16384 loads, best of 8: 49161 cycles as found (bit clear), with `CacheControl(0, CACRF_EnableD)`, and with the bit set; 5 runs, identical |
| The test can see a cache miss | (M) 2026-11-17 | Core 12856, V4 UniCorn | Same chase over 4 MB: 468071–470680 cycles (about 28.6 per load against 3 per load in 64 KB) |
| A sequential sum is not a valid test | (M) 2026-11-17 | Core 12856, V4 UniCorn | A 4-long unrolled sum of 64 KB vs a 4 MB stream: 28702 vs 28680 cycles per 64 KB. Prefetch hides the misses, so equal timings there prove nothing about the cache |
