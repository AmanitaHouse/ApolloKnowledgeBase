---
title: "GCC 6.5 bbb pass crashes with \"insn does not satisfy its constraints\" after an auto-increment"
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [toolchain]
applies_to:
  core: "any"
  os: [any]
tags: [gcc, bbb, optimizer, autoincrement, ice, volatile]
related:
  - toolchain/compiler-variants.md
  - toolchain/pitfalls/gcc-bbb-autoinc-converted-insn.md
sources:
  - "github.com/WDrijver/ApolloCrossDev issue #33 and pull request #34 (bbb-autoinc-fixup-constraints-fix.patch, merged 2026-11-24)"
  - "ApolloTeam-dev/V4Net, source/v4net/netdev.c, drv_dma_alloc (where it was found)"
  - "Reproduction with GCC-6.50-Dev 6.5.0b, installed 2026-11-25 (this file, Evidence)"
---

## Symptom

The compiler stops with an internal compiler error:

```text
error: insn does not satisfy its constraints:
(insn 84 ... (set (reg:SI 8 a0)
        (plus:SI (mem/v:SI (plus:SI (reg/v/f:SI 11 a3) (const_int 11054)))
            (const_int 1))))  {*addsi3_internal}
internal compiler error: in final_scan_insn, at final.c:2943
```

It was found building `v4net.device` at `-O2` with `-m68020` or `-m68080`.
The trigger was a `volatile ULONG` increment at a large struct offset between
`Forbid()` and `Permit()`, with `SysBase` read through a struct pointer.
`-fbbb=-` compiles the file.

## Cause

Bebbo's bbb pass `opt_autoinc` (`-fbbb=i`) turns `move.l (a3),a2` into
`move.l (a3)+,a2` and lowers the offsets of the later uses of `a3`. Each
changed instruction is emitted again and recognized anew, and GCC takes the
first pattern whose operand types match. That need not be the pattern the
instruction had. `lea ([11054,a3],1),a0` came back with offset 11050 as
`*addsi3_internal`, which does not allow a memory source with an address
register as destination. Nothing checked this, so `final` crashed.

The fix tries each fixup on a copy first and gives up the auto-increment
when the copy is not a valid instruction. That spot then compiles as with
`-fbbb=-`. Only GCC-6.50-Dev applies it.

## Wrong

The reduced case from ApolloCrossDev issue #33:

```c
#include <exec/types.h>
#include <exec/memory.h>
struct Db { UBYTE pad[34]; struct Library *db_SysBase; };
#include <proto/exec.h>
#define SysBase db->db_SysBase
struct Nd { struct Db *nd_Db; UBYTE pad[11050]; volatile ULONG cnt; };

APTR f(APTR ctx, ULONG size, ULONG align)
{
    struct Nd *nd = ctx;
    struct Db *db = nd->nd_Db;
    UBYTE *raw;
    APTR *p;
    if (align < 4) align = 4;
    raw = AllocVec(size + align + 4, MEMF_PUBLIC);
    if (raw == NULL) return NULL;
    p = (APTR *)(((ULONG)raw + 4 + align - 1) & ~(align - 1));
    p[-1] = raw;
    Forbid();
    nd->cnt++;          /* volatile increment at offset 11054 */
    Permit();
    return p;
}
```

## Right

Use GCC-6.50-Dev installed on or after 2026-11-25 (pull request #34 was
merged late on 2026-11-24). With an older install, compile the affected
file with `-fbbb=-`, or reinstall GCC-6.50-Dev. The code needs no change.

## Detection

The error message itself: `insn does not satisfy its constraints` with a
`mem` operand and an address register destination, in `final_scan_insn`.
If `-fbbb=-` makes it go away, it is this bug or another bbb bug.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| ICE with default flags and with `-fbbb=i`; `-fbbb=-` compiles | (M) 2026-11-24 | any (compiler output) | ApolloCrossDev issue #33, GCC-6.50-Dev built 2026-11-24 15:15 UTC, `-noixemul -O2 -m68020 -fomit-frame-pointer -msoft-float` |
| With the fix the reproducer compiles with `-m68020` and with `-m68080` | (M) 2026-11-25 | any (compiler output) | GCC-6.50-Dev 6.5.0b installed 2026-11-25 08:34, same flags, NDK 3.2 headers |
| Cause: the re-emitted insn is recognized as `*addsi3_internal` without a constraint check | (SRC) | any | `bbb-autoinc-fixup-constraints-fix.patch`, `bbb-opts.c` |
| Only GCC-6.50-Dev applies the patch | (SRC) | any | `GCC-6.50-Dev-*.sh` and `GCC-6.50-Stable-*.sh`, ApolloCrossDev `c1fba26a4` |
