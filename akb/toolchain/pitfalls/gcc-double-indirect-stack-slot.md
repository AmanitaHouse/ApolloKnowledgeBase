---
title: GCC 6.5 puts memory indirect operands on the wrong stack slot after a call
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [toolchain]
applies_to:
  core: "any"
  os: [any]
tags: [gcc, double-indirect, memory-indirect, reload, miscompile, m68080]
related:
  - toolchain/compiler-variants.md
  - core/pitfalls/double-memory-indirect.md
sources:
  - "ApolloOS R10 port (ApolloOS-Port), 2026-11-17: libjpeg 9 jdsample.c sep_upsample in jfif.library; whole-build scan of 7662 C files"
  - "github.com/WDrijver/ApolloCrossDev pull request #15 (removes double-indirect-fix.patch, 2026-11-04)"
  - "github.com/WDrijver/ApolloCrossDev issue #27 (this bug, with the reproduction)"
---

## Symptom

Code compiled with GCC-6.50-Dev and `-m68080 -O2 -fomit-frame-pointer`
updates the wrong variable through a pointer argument. In libjpeg 9,
`jpeg_read_scanlines()` returned 0 rows forever and corrupted `cinfo->err`.
A program decoding a JPEG looped and then crashed with a garbage PC.

## Cause

- Since `double-indirect-fix.patch` was removed (2026-11-04), GCC-6.50-Dev
  emits memory indirect operands `([bd,An],od)` on `-m68080`. Its cost model
  chooses them there. On `-m68020` and `-m68060` it does not.
- When a pointer argument gets no register, reload replaces it by its stack
  slot inside the outer memory reference: `([N,sp])`. `N` is the offset at
  function entry. Reload does not add the bytes of a call's pushed
  arguments, so between the pushes and the pop the operand addresses
  another argument's slot.
- The bbb pass is not involved: `-fbbb=-` gives the same code.

## Wrong

```c
/* out_ctr: 6th argument; -m68080 -O2 -fomit-frame-pointer */
cinfo->cconvert->convert(cinfo, st->buf, st->next_row, out_buf + *out_ctr, n);
*out_ctr += n;
```

```text
    jsr     (a0)
    add.l   d2,([56,sp])     ; 20 bytes still pushed: this is cinfo's slot
    lea     (20,sp),sp
```

## Right

Build with `-fno-double-indirect`. GCC then loads the pointer from the right
slot (`move.l (76,sp),a0`) and emits no memory indirect operands at all.
That also avoids the slow mode (see
[double-memory-indirect.md](../../core/pitfalls/double-memory-indirect.md)).

## Detection

Compile with `-S` and search for `([`. In the ApolloOS R10 tree (7662 C
files), the Dev compiler emitted 23437 memory indirect operands, 2236 of them
sp-based in 676 files. With `-fno-double-indirect` it emitted none.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| `add.l d2,([56,sp])` after the call, with 20 bytes of arguments pushed | (M) 2026-11-17 | any | `-S` of a 50-line reduction of libjpeg `sep_upsample`; RTL dumps: the bad operand first appears in the reload pass, from the REG_EQUIV `(mem (plus argp 28))` |
| Only `-m68080` | (M) 2026-11-17 | any | Same file with `-m68020`, `-m68060`: pointer loaded into a register first |
| `-fno-double-indirect` fixes it | (M) 2026-11-17 | Core 12856, V4 UniCorn | Reduction: `move.l (76,sp),a0`. jfif.library rebuilt: MultiView shows the JPEG on the V4 |
| Scale | (M) 2026-11-17 | any | Whole-build `-S` scan, ApolloOS R10 tree |
