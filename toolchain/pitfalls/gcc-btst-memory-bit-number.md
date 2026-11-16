---
title: GCC 6.5 tests the wrong byte with btst on a value in memory
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [toolchain]
applies_to:
  core: "any"
  os: [any]
tags: [gcc, btst, bitfield, miscompile, m68k-backend]
related:
  - toolchain/compiler-variants.md
  - toolchain/c-compiler-options.md
  - toolchain/pitfalls/gcc-bbb-shift-wrong-code.md
sources:
  - "github.com/WDrijver/ApolloCrossDev pull request #26 (m68k-btst-mem-offset-fix.patch)"
  - "github.com/WDrijver/gcc gcc-stable, gcc/config/m68k/m68k.md: *tst_bftst_mem, *tst_bftst_mem1, *tst_bftst_mem2"
  - "ApolloOS R10 port (ApolloOS-Port), 2026-11-16: Regina REXX, exec stdAllocReverse, reqtools"
---

## Symptom

A test of one bit of an `int` or `short` in memory takes the wrong branch,
without any warning, at `-O1` and up, for 68020 to 68080:

- `if (flags[i] & 2)` in a loop is never true (or always true).
- `if (*req & MEMF_CLEAR)` is ignored.

The emitted code has a `btst` with a bit number below 0 or above 7 on a
memory operand:

```asm
    btst    #-23,(a3)       ; meant: bit 1 of the long at (a3)
```

Seen in ApolloOS R10: exec's `stdAllocReverse` never cleared
`MEMF_REVERSE|MEMF_CLEAR` memory, Regina REXX found no built-in function
written in lower case, and a reqtools flag test went wrong.

## Cause

The m68k back end of the ApolloCrossDev GCC (bebbo's fork) turns such a test
into a one-bit field test. The patterns `*tst_bftst_mem`,
`*tst_bftst_mem1` and `*tst_bftst_mem2` (SImode, HImode and QImode memory)
emit it as `btst` with bit number `7 - POS` on the operand's first byte.
POS counts from the most significant bit of the whole operand (0 to 31 for
a long), so for a bit in the low 24 bits of a long the number goes below 0.

`btst` on memory works on one byte and uses only the low three bits of the
bit number: `btst #-23,(a3)` tests bit 1 of the byte at `(a3)`, the most
significant byte of the long. The right instruction is `btst #1,(3,a3)`.

Upstream GCC has a QImode operand in these patterns; the SImode and HImode
variants are the fork's. It is not the bbb pass: `-fbbb=-` does not change
it.

The fix, `m68k-btst-mem-offset-fix.patch` (ApolloCrossDev pull request #26),
tests bit `7 - POS % 8` of byte `POS / 8`. GCC-6.50-Dev and GCC-6.50-Stable
apply it; GCC-6.50-Base does not.

## Wrong

```c
unsigned info[257];
unsigned char tab[256];

void loop(const unsigned char *lower)
{
    int i;

    for (i = 0; i < 256; i++)
        if (info[i] & 2)        /* btst #-23,(a3): wrong byte */
            tab[lower[i]] = i;
}
```

## Right

DO use GCC-6.50-Dev or GCC-6.50-Stable installed with pull request #26.

DO, with GCC-6.50-Base or an older install, compile with `-mno-bitfield`.
GCC then tests the bit with `and.l` and the result is right. The flag also
stops GCC from using the 68020 bit-field instructions (`bfextu`, `bftst`,
...) elsewhere in the file.

CI checks that GCC-6.50-Dev emits no bit number below 0 for the example
above:

```c
// kb:compile
// kb:expect-not btst #-
unsigned info[257];
unsigned char tab[256];

void loop(const unsigned char *lower)
{
    int i;

    for (i = 0; i < 256; i++)
        if (info[i] & 2)
            tab[lower[i]] = i;
}
```

## Detection

Compile with `-S` and search the assembly for a bit instruction on memory
with a bit number outside 0 to 7. Any such instruction is wrong:

```sh
grep -nE 'b(tst|set|clr|chg)(\.b)?[[:space:]]+#(-[0-9]+|[0-9]{2,}|[89]),[^d%]' *.s
```

DON'T scan object files with a disassembler instead: data in code sections
decodes as such instructions too and gives false alarms.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| The example compiles to `btst #-23,(a3)`; `btst #1,(3,a3)` with the fix | (SRC) | any | `m68k-amigaos-gcc -m68080 -O2 -S`, GCC 6.5.0b with and without the patch; also `-m68020`, `-m68060` |
| ApolloOS R10 (7662 C files) has 4 such instructions; with the fix 0, and the assembly is otherwise identical | (SRC) | any | `-S` output of the whole build with and without the patch, compared file by file |
| Regina REXX on R10: lower-case built-ins not found before the fix, found after (also ARexx file I/O) | (M) | Core 12856 | Scripts run with `rx` on a V4, regina.library built with each compiler |
| `-mno-bitfield` avoids the bug | (SRC) | any | `-S` output of the example and of a pointer-to-flags test |
