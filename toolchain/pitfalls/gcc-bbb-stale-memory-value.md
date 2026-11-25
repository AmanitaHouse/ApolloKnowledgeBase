---
title: GCC 6.5 bbb pass keeps a stale memory value after a store and deletes the reload
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [toolchain]
applies_to:
  core: "any"
  os: [any]
tags: [gcc, bbb, optimizer, dead-assign, miscompile, int64, spill]
related:
  - toolchain/compiler-variants.md
  - toolchain/pitfalls/gcc-bbb-shift-wrong-code.md
sources:
  - "github.com/WDrijver/ApolloCrossDev pull request #30 by delwall (bbb-invalidate-mem-fix.patch, merged 2026-11-24)"
---

## Symptom

64-bit arithmetic gives wrong results at `-O2 -m68080`, for example
`int64_t a = ...; a * i / j`. There is no warning. `-fbbb=-`, `-fbbb`
without `e`, and `-O1` give correct results.

## Cause

Bebbo's bbb pass remembers which register holds which memory value. A
store must make it forget every cached value the store may overwrite. The
old `track_var::invalidate_mem` kept the cached value when the store had
another mode or other attributes, or lay within 3 bytes of it: its offset
test was inverted.

When a 64-bit (`DImode`) store overwrote a 32-bit spill slot, the pass still
believed a register held the slot's old value. `opt_elim_dead_assign`
(`-fbbb=e`) then deleted the reload of that slot:

```text
    move.l (-460,a5),d0
    move.l d0,(-456,a5)
    smi d4
    extb.l d4
    move.l d4,(-460,a5)     ; overwrites the slot
    muls.l d0,d1
    move.l (-460,a5),d0     ; deleted by -fbbb=e: d0 keeps the old value
    muls.l (-480,a5),d0
```

The fix forgets a cached value on every store that may overlap it: always
for the same base register, and otherwise unless the alias sets or
`nonoverlapping_memrefs_p` prove the two apart. Instructions with several
stores are handled too. Only GCC-6.50-Dev applies it.

## Wrong

```c
#include <stdint.h>

int64_t scale(int64_t a, int mul, int div)
{
    return a * mul / div;   /* can be miscompiled at -O2 -m68080 */
}
```

The function above shows the pattern, not a confirmed reproducer: the bug
needs register pressure that spills a value next to a 64-bit temporary.

## Right

Use GCC-6.50-Dev installed on or after 2026-11-24. With an older install,
GCC-6.50-Stable or GCC-6.50-Base, compile files with 64-bit arithmetic with
`-fbbb=-`, or reinstall GCC-6.50-Dev.

## Detection

Run 64-bit arithmetic against host results in a unit test. In `-S` output,
look for a store to a stack slot followed by a use of a register that held
that slot before the store, with no reload in between. Compare with
`-fbbb=-`.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| A `DImode` store over an `SImode` spill slot kept the stale value; `opt_elim_dead_assign` deleted the reload; wrong 64-bit products | (SRC) ApolloCrossDev PR #30 | any (compiler output) | Pull request description with the `-S` excerpt above |
| With the fix the reduced case matches the host | (M) delwall, PR #30 | V4 (core not stated) | Run on a Vampire V4 against host results |
| 703 of 720 compilations (373 C files at `-m68080 -O2/-O3/-Os`) unchanged; the rest only keep loads the old pass had replaced | (M) delwall, PR #30 | any (compiler output) | Comparison of compiler output before and after the patch |
| Only GCC-6.50-Dev applies the patch | (SRC) | any | `GCC-6.50-Dev-*.sh` and `GCC-6.50-Stable-*.sh`, ApolloCrossDev `c1fba26a4` |
