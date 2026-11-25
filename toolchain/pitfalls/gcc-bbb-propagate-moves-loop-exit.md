---
title: GCC 6.5 bbb pass gives an early loop exit the pointer value from before the loop
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [toolchain]
applies_to:
  core: "any"
  os: [any]
tags: [gcc, bbb, optimizer, propagate-moves, autoincrement, miscompile, loop]
related:
  - toolchain/compiler-variants.md
  - toolchain/pitfalls/gcc-bbb-propagate-moves-ice.md
sources:
  - "github.com/WDrijver/ApolloCrossDev issue #36 and pull request #37 (bbb-propagate-moves-addr-exit-fix.patch, merged 2026-11-25)"
  - "Reproduction with GCC-6.50-Dev 6.5.0b, installed 2026-11-25 before pull request #37 (this file, Evidence)"
---

## Symptom

A loop that walks a pointer through a buffer and leaves early, with `break`
or `goto`, sees the pointer's value from before the loop after the exit.
Code after the loop that uses the pointer, such as `p - s`, gets the wrong
result. Leaving the loop at its normal end is correct. There is no warning.
It happens at `-O2` with the default `-fbbb`, for 68020 to 68080.

## Cause

Bebbo's bbb pass `opt_propagate_moves` (`-fbbb=p`) takes a loop with a
register copy pair

```text
.L1:  move.l src,dst  ...  (exit: jcc .Lout)  ...  move.l dst,src  jcc .L1
```

and moves the first copy in front of the loop and the second behind it.
Inside the loop `src` is then no longer updated, so every exit between the
two copies must set `src` from `dst` again. Two bugs broke that:

1. For a post-increment in the source of an instruction, the size was taken
   from the destination. After bbb pass 0 a byte load is a
   `strict_low_part`, which has no size, so the increment counted as 0.
2. With two address registers and no offset to undo, nothing at all was
   emitted at the exit, so `src` kept its value from before the loop.

The fix uses the size of the memory read, and emits `src = dst` when the
offset is 0. Only GCC-6.50-Dev applies it.

## Wrong

```c
long f(const unsigned char *s, unsigned char *d, unsigned char c,
       unsigned char m, const unsigned char *lim, int n, unsigned char *x0,
       unsigned char *x1, unsigned char *x2, unsigned char *x3)
{
    const unsigned char *p = s; long acc = 0; int k = 0;
    while (k < n)
    {
        const unsigned char *q = p;
        if ((*q & m) != 0) goto out;    /* early exit */
        acc += *q++;
        p = q; k++;
    }
out:
    return (long)(p - s) * 3 + acc;
}
```

At `-O2 -m68020`, before the fix, the loop advances `a0`, but the early exit
computes `p - s` from `a1`, which still holds `s`:

```text
    move.l d5,a1           ; a1 = s
    ...
    move.l a1,a0
.L4:
    clr.l d1
    move.b (a0)+,d1        ; p advances in a0 only
    move.b d1,d4
    and.b d3,d4
    jne .L9                ; early exit
    ...
.L9:
    sub.l d5,a1            ; p - s from a1 = s: always 0
```

Every early exit after the first iteration returns `acc` instead of
`3 * (p - s) + acc`.

## Right

Use GCC-6.50-Dev installed on or after 2026-11-25, after pull request #37
(merged at 09:46 UTC). An install from earlier that day still has this bug.
With an older install, GCC-6.50-Stable or GCC-6.50-Base, compile the
affected file with `-fbbb=-`, or reinstall GCC-6.50-Dev.

## Detection

In `-S` output, look for a loop that post-increments one address register
and has an exit label that reads another address register which the loop
never writes. Compare with `-fbbb=-`, where the loop copies the pointer
back (`move.l a0,a1`) inside the loop.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| The early exit at `.L9` computes `p - s` from `a1`, which still holds `s`; `-fbbb=-` copies `a0` to `a1` inside the loop | (M) 2026-11-25 | any (compiler output) | GCC-6.50-Dev 6.5.0b installed 2026-11-25 08:34 (before PR #37), `-O2 -m68020 -S`, with and without `-fbbb=-` |
| Cause: increment size taken from a `strict_low_part` (VOIDmode) destination; no copy emitted for two address registers with offset 0 | (SRC) | any | `bbb-propagate-moves-addr-exit-fix.patch`, ApolloCrossDev issue #36 |
| With the fix, `.L9` uses `a0 - 1`, the same as `-fbbb=-` | (SRC) ApolloCrossDev PR #37 | any (compiler output) | Patch description |
| Only GCC-6.50-Dev applies the patch | (SRC) | any | `GCC-6.50-Dev-*.sh` and `GCC-6.50-Stable-*.sh`, ApolloCrossDev `c1fba26a4` |
