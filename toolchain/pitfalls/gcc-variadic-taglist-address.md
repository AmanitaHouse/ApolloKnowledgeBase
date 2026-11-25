---
title: "&tag1 as a tag list breaks when GCC inlines or clones a variadic function"
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured]
components: [toolchain]
applies_to:
  core: "any"
  os: [any]
tags: [gcc, varargs, variadic, taglist, stack-tags, inline, ipa-cp, constprop]
related:
  - toolchain/pitfalls/gcc-misc-traps.md
  - toolchain/compiler-variants.md
sources:
  - "ApolloOS R10 port (ApolloOS-Port), 2026-11-25: Prefs/IControl ChunkyImageOrSpace(), fixed in commit b5fd0c5c"
  - "Reproduction with GCC-6.50-Dev m68k-amigaos-gcc 6.5.0b, -m68080 -fomit-frame-pointer, -O1/-O2/-Os/-O3 (this file, Detection)"
---

## Symptom

A small helper of the classic Amiga form `f(Tag tag1, ...)` passes
`(struct TagItem *)&tag1` to a `...A()` function (`NewObjectA`,
`MUI_NewObjectA`, `SetAttrsA`). The called function sees none of the tags,
or garbage after the first one. Objects come up with default attributes,
`OM_NEW` or `MUIM_Setup` fails, and a window does not open. No warning is
given.

In ApolloOS R10, IControl's preferences window never opened under AROS
Zune. Serial debug in ChunkyImage showed width 0, height 0, 0 colours and
no pixels, although the caller passed all of them.

## Cause

Reading the variadic arguments through the address of the last named
parameter was never valid C. It works only while the function is an
ordinary out-of-line function whose named and variadic arguments lie next
to each other on the stack, which is the classic m68k stack calling
convention. GCC is free to break that, and GCC 6.5 (ApolloCrossDev) does:

- **Inlining.** A variadic function that never calls `va_start` can be
  inlined. At the call site GCC then does not push the variadic arguments
  at all. `&tag1` becomes the address of a local copy of `tag1`, followed
  by whatever lies in the frame. This happens to a `static` helper at
  `-O1`, `-O2`, `-Os` and `-O3`. It also happens to a non-static helper
  called from the same file; only calls from other files still work.
- **Interprocedural constant propagation.** When every call passes the
  same constant first argument (for example `TAG_IGNORE`), GCC makes a
  specialised clone (`f.constprop.N` in the symbol table) without that
  parameter. Inside the clone `&tag1` again points at a local copy, not
  at the stack slot before the variadic arguments. `__attribute__((noinline))`
  alone does not stop this.

## Wrong

```c
static Object *ChunkyImageOrSpace(Tag tag1, ...)
{
    struct TagItem *tags = (struct TagItem *)&tag1;   /* not the caller's tags */
    Object *o = MUI_NewObjectA(MUIC_ChunkyImage, tags);
    ...
}

ChunkyImageOrSpace(TAG_IGNORE, 0,
    MUIA_ChunkyImage_Pixels, (IPTR)pixels, MUIA_Bitmap_Width, 128, TAG_DONE);
```

## Right

Copy the tags with `va_arg`. This is valid C and stays correct when GCC
clones the function: the clone still reads the caller's arguments.

```c
#include <stdarg.h>

#define MAXTAGS 16
static Object *ChunkyImageOrSpace(Tag tag1, ...)
{
    struct TagItem tags[MAXTAGS + 1];
    Tag tag = tag1;
    va_list ap;
    int n = 0;

    va_start(ap, tag1);
    while (tag != TAG_DONE && n < MAXTAGS)
    {
        tags[n].ti_Tag  = tag;
        tags[n].ti_Data = va_arg(ap, IPTR);   /* ULONG on AmigaOS headers */
        n++;
        tag = va_arg(ap, Tag);
    }
    va_end(ap);
    tags[n].ti_Tag = TAG_DONE;
    tags[n].ti_Data = 0;

    return MUI_NewObjectA(MUIC_ChunkyImage, tags);
}
```

On AROS and ApolloOS sources, `AROS_SLOWSTACKTAGS_PRE` /
`AROS_SLOWSTACKTAGS_ARG` / `AROS_SLOWSTACKTAGS_POST` (`<utility/tagitem.h>`)
do the same. If the `&tag1` form must stay, mark the function
`__attribute__((noinline, noclone))`. Both attributes are needed.

## Detection

- Review: search for `(struct TagItem *)&` in your own code. Every hit in
  a function without `va_start` is a candidate. The `vastubs.c` files of
  NList and BetterString use the form too, but they are compiled only for
  non-AROS compilers and are called from other files.
- Build: `m68k-amigaos-objdump -t file.o | grep constprop` lists cloned
  functions. A variadic helper that is missing from the symbol table was
  inlined.
- Reproduction (GCC-6.50-Dev, `-m68080 -fomit-frame-pointer -O2`): a
  static `wrong(Tag tag1, ...)` that returns `use_tags((struct TagItem
  *)&tag1)`, called twice as `wrong(TAG_IGNORE, 0, 0x80001234, 42,
  TAG_DONE)`. The caller's code contains no push of `0x80001234` at all,
  and `use_tags` receives the address of a local holding 1.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| A static variadic helper using `&tag1` is inlined and the variadic arguments are not pushed, at -O1, -O2, -Os and -O3 | (M) 2026-11-25 | any (compiler output) | GCC-6.50-Dev 6.5.0b, `-m68080 -fomit-frame-pointer`, objdump of the reproduction |
| A non-static helper is inlined the same way at a call site in the same file | (M) 2026-11-25 | any | same; `extern` variant |
| `noinline` alone gives a `.constprop` clone without the constant first parameter; `noinline, noclone` keeps the stack layout | (M) 2026-11-25 | any | same; `noinline` and `noinline, noclone` variants |
| The `va_arg` copy is also cloned, but reads the caller's arguments from the stack | (M) 2026-11-25 | any | same; disassembly of `wrong.constprop.0` (`lea 84(sp),a0`) |
| IControl's ChunkyImage objects got no attributes and the window did not open; with the `va_arg` copy all four images are built and the window opens | (M) 2026-11-25 | Core 12856 | ApolloOS R10 dev card, AROS master Zune muimaster.library with serial debug in ChunkyImage/Bitmap setup |
