---
title: "GCC 6.5 bbb pass crashes in schedule_region when it moves a copy out of a loop"
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [toolchain]
applies_to:
  core: "any"
  os: [any]
tags: [gcc, bbb, optimizer, propagate-moves, ice, sched2, lua]
related:
  - toolchain/compiler-variants.md
  - toolchain/pitfalls/gcc-bbb-propagate-moves-loop-exit.md
sources:
  - "github.com/WDrijver/ApolloCrossDev pull request #35 (bbb-propagate-moves-bb-boundary-fix.patch, merged 2026-11-25)"
  - "Lua 5.4.6 lobject.c, luaO_str2num (where it was found)"
  - "Reproduction with GCC-6.50-Dev 6.5.0b, installed 2026-11-25 (this file, Evidence)"
---

## Symptom

The compiler stops with:

```text
internal compiler error: in schedule_region, at sched-rgn.c:3213
```

It was found compiling Lua 5.4.6 `lobject.c` at `-O3 -m68080` and at
`-Ofast -m68080 -m68881`. `-fbbb=-`, and `-fbbb` without `p`, compile the
file.

## Cause

Bebbo's bbb pass `opt_propagate_moves` (`-fbbb=p`) takes a register copy
pair `move src,x ... move x,src` out of a loop. One copy goes in front of
the loop label, the other behind the loop's jump. The pass chose those
places from its own filtered list of instructions, so the place in front of
the loop could be a conditional jump, and the place behind it could be a
label. The copy then landed behind the jump that ends a basic block:

```text
    beq .L221          ; end of the block
    move.l d0,a4       ; the moved copy, still in that block
.L154:                 ; loop label
```

The code would still run correctly, but the scheduler (`sched2`) cannot
place an instruction behind a block's jump, and crashed.

The fix leaves such loops alone, as with `-fbbb=-`. Only GCC-6.50-Dev
applies it.

## Wrong

The reduced case from the patch, with the string-to-number code of Lua
inlined into one function at `-O3`:

```c
#include <stdlib.h>
#include <string.h>
extern const unsigned char ctype_[257];
typedef struct { double n; unsigned char tt; } TValue;

static const char *str2dloc(const char *s, double *result, int mode)
{
    char *endptr;
    *result = (mode == 'x') ? strtod(s, &endptr) : strtod(s, &endptr);
    if (endptr == s) return NULL;
    while (ctype_[(unsigned char)*endptr + 1] & 8) endptr++;
    return *endptr == '\0' ? endptr : NULL;
}

static const char *str2d(const char *s, double *result)
{
    const char *endptr;
    const char *pmode = strpbrk(s, ".xXnN");
    int mode = pmode ? ((unsigned char)*pmode | ('A' ^ 'a')) : 0;
    if (mode == 'n') return NULL;
    endptr = str2dloc(s, result, mode);
    if (endptr == NULL) {
        char buff[201];
        strcpy(buff, s);
        endptr = str2dloc(buff, result, mode);
        if (endptr != NULL) endptr = s + (endptr - buff);
    }
    return endptr;
}

static const char *str2int(const char *s, long long *result)
{
    if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X'))
        for (s += 2; ctype_[(unsigned char)*s + 1] & 16; s++) ;
    while (ctype_[(unsigned char)*s + 1] & 8) s++;
    if (*s != '\0') return NULL;
    *result = 0;
    return s;
}

size_t str2num(const char *s, TValue *o)
{
    long long i; double n; const char *e;
    if ((e = str2int(s, &i)) != NULL) o->tt = 3;
    else if ((e = str2d(s, &n)) != NULL) { o->n = n; o->tt = 19; }
    else return 0;
    return (e - s) + 1;
}
```

## Right

Use GCC-6.50-Dev installed on or after 2026-11-25. With an older install,
compile the affected file with `-fbbb=-`, or reinstall GCC-6.50-Dev. The
code needs no change.

## Detection

The error message itself: an ICE in `schedule_region` at
`sched-rgn.c:3213`. If `-fbbb=-` makes it go away, it is this bug or another
bbb bug.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| ICE at `-O3 -m68080` and `-Ofast -m68080 -m68881`; `-fbbb=-` and `-fbbb` without `p` compile it | (SRC) ApolloCrossDev PR #35 | any (compiler output) | Patch description, Lua 5.4.6 `lobject.c` and the reduced case |
| With the fix the reduced case compiles at `-O3 -m68080` and `-Ofast -m68080 -m68881` | (M) 2026-11-25 | any (compiler output) | GCC-6.50-Dev 6.5.0b installed 2026-11-25 08:34, `-noixemul -S` |
| Only GCC-6.50-Dev applies the patch | (SRC) | any | `GCC-6.50-Dev-*.sh` and `GCC-6.50-Stable-*.sh`, ApolloCrossDev `c1fba26a4` |
