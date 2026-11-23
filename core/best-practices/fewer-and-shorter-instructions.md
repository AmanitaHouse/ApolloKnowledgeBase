---
title: Use fewer instructions, then shorter encodings
type: best-practice
owner: WDrijver
status: reviewed
origin: ai-assisted
basis: [core-developer]
components: [cpu-68080]
applies_to:
  core: "any"
  os: [any]
tags: [68080, code-size, encoding, immediates, addressing-modes]
related:
  - core/cpu-68080/execution-units.md
  - core/best-practices/code-size-and-placement.md
  - core/cpu-68080/prm/integer/moviw.md
  - core/cpu-68080/prm/integer/addiw.md
  - core/cpu-68080/prm/integer/cmpiw.md
sources:
  - "Gunnar (core developer), Simply 68080 coding guidelines, draft (2026-11-03), coding rules 1 and 2"
  - "Gunnar (core developer), Simply 68080 coding guidelines, version of 2026-11-23, coding rules 1 and 2"
---

## Goal

Speed and code size: each instruction takes a slot in a group, and a group
is at most 16 bytes. Fewer instructions fill fewer slots; shorter encodings
fit more instructions in a group and in the I-cache.

## Technique

1. **Do it with fewer instructions, even if one is longer** (G).

   ```asm
       add.l   #9,d0           ; good: one instruction
   ```

   is better than

   ```asm
       addq.l  #8,d0           ; two dependent instructions
       addq.l  #1,d0
   ```

2. **Then use the shortest encoding available** (G):

   | Instruction | Size | Immediate range | Destination |
   |---|---|---|---|
   | `move.l #imm,<ea>` | 6 bytes | any 32-bit value | any |
   | `moviw.l #imm,<ea>` | 4 bytes | sign-extended 16-bit | any |
   | `moveq #imm,Dn` | 2 bytes | sign-extended 8-bit | data registers only |
   | `addi.l #imm,<ea>` | 6 bytes | any 32-bit value | any |
   | `addiw.l #imm,<ea>` | 4 bytes | sign-extended 16-bit | any |
   | `addq.l #imm,<ea>` | 2 bytes | 1–8 | any |
   | `cmpi.l #imm,<ea>` | 6 bytes | any 32-bit value | any |
   | `cmpiw.l #imm,<ea>` | 4 bytes | sign-extended 16-bit | any |

   Walking memory: `(An)+` is often better than `d16(An)`.

   `(An)+` is shorter, and the EA unit updates the pointer for free.

See [prm/integer/moviw.md](../cpu-68080/prm/integer/moviw.md) (don't use its
LineA encoding), [prm/integer/addiw.md](../cpu-68080/prm/integer/addiw.md)
and [prm/integer/cmpiw.md](../cpu-68080/prm/integer/cmpiw.md).

## Evidence

| Variant | Measurement | Core | Test setup |
|---|---|---|---|
| `add.l #9,d0` against `addq.l #8,d0` + `addq.l #1,d0` | The single instruction is better | any | Statement (G) |

No measurement in the knowledge base yet.

## When not to use

- When the shorter form needs an extra instruction (rule 1 comes first).
- `(An)+` changes the pointer: when the code reads the same fields again,
  `d16(An)` can be the better choice.
