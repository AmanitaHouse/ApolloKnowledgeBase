---
title: GCC 6.5 bbb pass fixes up a post-increment it just made, and a pointer advances too little
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [toolchain]
applies_to:
  core: "any"
  os: [any]
tags: [gcc, bbb, optimizer, autoincrement, miscompile, struct-stride]
related:
  - toolchain/compiler-variants.md
  - toolchain/pitfalls/gcc-bbb-autoinc.md
sources:
  - "github.com/WDrijver/ApolloCrossDev pull request #29 by delwall (bbb-autoinc-converted-insn-fix.patch, merged 2026-11-24)"
  - "Reproduction with GCC-6.50-Dev 6.5.0b, installed 2026-11-25 (this file, Evidence)"
---

## Symptom

A loop over packed records (for example 12-byte `float[3]` vertices) reads
the wrong fields and advances its pointer too little. The result is silently
wrong. There is no warning and no crash. `-fbbb=-` gives correct code.

It needs a loop body that reads the same record in two groups, such as two
dot products on the same vertex. The original case was a 68080 renderer.
`float`, `double`, and 3, 4 or 5 element records were all affected.

## Cause

Bebbo's bbb pass `opt_autoinc` (`-fbbb=i`) turns `(a0)`, `(4,a0)`, `(8,a0)`
into post-increments one instruction at a time. For each one it lowers the
offsets of the other uses of `a0` and the closing `add`/`lea`. After an
instruction is converted, its bookkeeping still shows the old offset until
the next pass. A later search in the same pass sees that instruction as a
plain `(-4,a0)` access and lowers the `add` a second time. Offsets shift too
far and a `lea (4,a0),a0` that must stay is deleted.

In the reproducer below, `a0` advanced 8 bytes per vertex instead of 12, and
`v[2]` was read from `(a0)` instead of `(4,a0)`.

The fix makes `try_auto_inc` stop at an instruction that already
auto-modifies the register. Only GCC-6.50-Dev applies it.

## Wrong

```c
typedef float vec3_t[3];
void uv(const vec3_t *pos, float (*out)[2], int n,
        const float *vx, const float *vy,
        float ox, float oy, float sx, float sy, float k)
{
    int i;
    for (i = 0; i < n; i++) {
        const float *v = pos[i];   /* read twice: two groups of loads */
        out[i][0] = (v[0]*vx[0] + v[1]*vx[1] + v[2]*vx[2] + ox - sx) * k;
        out[i][1] = (v[0]*vy[0] + v[1]*vy[1] + v[2]*vy[2] + oy - sy) * k;
    }
}
```

With `-m68080 -m68881 -ffast-math -fomit-frame-pointer -Ofast
-fexcess-precision=fast -fno-unsafe-math-optimizations`, before the fix:

```text
    fsmove.s (a0)+,fp0
    fsmove.s (a0),fp3       ; v[1] and v[2] both read at (a0)
    fsmove.s (a0),fp2
    ...
    fsmove.s (-8,a0),fp0
    fsmove.s (-4,a0),fp3
    fsmove.s (a0)+,fp2      ; a0 advanced 8 bytes, not 12
```

## Right

Use GCC-6.50-Dev installed on or after 2026-11-24. The same loop then
compiles to:

```text
    fsmove.s (a0)+,fp0
    fsmove.s (a0)+,fp3
    fsmove.s (a0)+,fp2
    fsmove.s (-12,a0),fp0
    fsmove.s (-8,a0),fp3
    fsmove.s (-4,a0),fp2
```

With an older install, GCC-6.50-Stable or GCC-6.50-Base, compile the
affected file with `-fbbb=-`, or reinstall GCC-6.50-Dev.

## Detection

Compile with `-S` and look for an address register that is post-incremented
in one group of loads while other loads of the same record use `(aN)`
without an offset. Compare with the output of `-fbbb=-`: the number of
bytes the pointer advances per iteration must be the record size.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| Two groups of loads on one record, converted in one pass, give wrong offsets and too small a stride; `-fbbb=-` is correct | (SRC) ApolloCrossDev PR #29 | any (compiler output) | Patch description with the reproducer and the wrong `-S` output |
| With the fix, the reproducer gives three post-increments, then `(-12,a0)`, `(-8,a0)`, `(-4,a0)` | (M) 2026-11-25 | any (compiler output) | GCC-6.50-Dev 6.5.0b installed 2026-11-25 08:34, flags above, `-S` |
| Only GCC-6.50-Dev applies the patch | (SRC) | any | `GCC-6.50-Dev-*.sh` and `GCC-6.50-Stable-*.sh`, ApolloCrossDev `c1fba26a4` |
