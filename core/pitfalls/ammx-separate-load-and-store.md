---
title: AMMX code with a separate LOAD or STORE where the operand can be memory
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [core-developer, official, source-code]
components: [cpu-68080, toolchain]
applies_to:
  core: "any"
  os: [any]
tags: [68080, ammx, load, store, vea, immediate, packuswb, pack3216, loadi, storei]
related:
  - core/cpu-68080/prm/ammx/ammx-format.md
  - core/cpu-68080/prm/ammx/load.md
  - core/cpu-68080/prm/ammx/store.md
  - core/cpu-68080/prm/ammx/packuswb.md
  - core/cpu-68080/prm/ammx/pack3216.md
  - core/cpu-68080/prm/ammx/loadi.md
  - core/cpu-68080/prm/ammx/storei.md
  - core/pitfalls/ammx-pc-relative-source.md
  - core/best-practices/ammx-where-it-wins.md
  - core/best-practices/fewer-and-shorter-instructions.md
  - toolchain/pitfalls/vasm-68080-encoding-issues.md
sources:
  - "Gunnar (core developer), AMMX operand forms, 2026-11-24"
  - "Apollo 68080 PRM (sources/official/AC68080PRM.odt), AMMX format page"
  - "vasm 2.0g (ApolloCrossDev GCC-6.50-Dev), test assembly of the forms below, 2026-11-24"
---

## Symptom

AMMX code that loads every operand with `load` before the operation, or
packs into a register and then stores it with `store`. It runs and gives the
right result, but uses more instructions and more slots of the one AMMX unit
than needed. Gunnar sees this "again and again" in AI-written code (G).

## Cause

AMMX instructions have two forms (G, official):

- **Operations** take their first operand from an effective address:
  `op <vea>,b,d`. `<vea>` can be a register (D0–D7, E0–E23), any memory mode
  (`(An)`, `(An)+`, `-(An)`, `d16(An)`, `d8(An,Xn)`, absolute) or an
  immediate. The result always goes to the register `d`.
- **Store instructions** have the effective address on the right and write
  to memory: `store b,<vea>`, `storem b,mask,<vea>`, `storec b,count,<vea>`,
  `storeilm b,mask,<vea>`, `storem3 b,#mode,<vea>`, and the pack
  instructions `packuswb b,d,<vea>` and `pack3216 b,d,<vea>`.

So a separate `load` is not needed when the value is used once, and a pack
needs no `store` after it. There is one AMMX unit; the second pipe accepts
AMMX stores only (M, see
[superscalar-issue.md](../cpu-68080/superscalar-issue.md)), so every extra
`load` takes a slot on that unit.

Other AMMX operations have no form that writes to memory: the PRM's
"write to memory (b,d,vea)" mode is marked future, and vasm 2.0g rejects
`paddw d1,d2,(a0)`. Their results still need a `store`.

## Wrong

```asm
.loop:
    load     (a0)+,d0
    paddusb  d0,d1,d2           ; d1 + source, saturated
    packuswb d2,d3,d4
    store    d4,(a1)+
    dbra.l   d7,.loop
```

## Right

```asm
.loop:
    paddusb  (a0)+,d1,d2        ; memory source, no load
    packuswb d2,d3,(a1)+        ; packs straight to memory, no store
    dbra.l   d7,.loop
```

An immediate is an operand too:

```asm
    paddb.w  #$0101,d1,d2       ; the word $0101 repeated: +1 in every byte lane
```

### Exceptions

- **A value used by several instructions:** load it once into a register.
- **PC-relative sources** read 2 bytes early on Core 12841 (see
  [ammx-pc-relative-source.md](ammx-pc-relative-source.md)): use
  `lea .k(pc),a0` and an `(a0)` source.
- **Immediates in vasm 2.0g:** the PRM's short form `#imm.W` (a word
  repeated into all four words, 6-byte instruction) is written with a `.w`
  suffix on the mnemonic: `paddb.w #$0101,d1,d2`. Without the suffix,
  `paddb #$0101,d1,d2` assembles silently to a 64-bit immediate
  `$0000000000000101` (12-byte instruction), so only the lowest lanes get
  the value. `paddb #$0101.w,d1,d2` does the same, with a "trailing garbage"
  warning. Gunnar suggests `#imm.w` as the syntax (G); vasm does not
  support it.
- **Names:** Gunnar calls the store instructions VSTORE, VSTOREM,
  VSTOREC, VSTOREM2 and VSTOREM3. vasm accepts only the PRM names `store`,
  `storem`, `storec`, `storeilm` (the PRM: "also called storem2") and
  `storem3`, and `pack3216` (not "PACK3116").

### Don't use LOADI and STOREI

Gunnar (G, 2026-11-24): `loadi` and `storei`, the indexed variants that
take the register number from another register, are extremely dangerous to
use and esoteric in their use cases. Don't use them. He would remove them
from the instruction list. Their PRM pages
([loadi.md](../cpu-68080/prm/ammx/loadi.md),
[storei.md](../cpu-68080/prm/ammx/storei.md)) are generated from the PRM
and still describe them.

## Detection

- A `load` whose register is read by exactly one AMMX operation.
- A `store` of a register that a `packuswb` or `pack3216` just wrote.
- An AMMX immediate without a `.w` suffix whose value fits in a word.
- Any `loadi` or `storei`.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| Operations take `(EA)` on the left; store and pack instructions have it on the right; agents add needless `load`/`store` | (G) | any | Statement, 2026-11-24 |
| `#imm.W` is a word repeated to a quad | (official) | any | PRM AMMX format page |
| The general write-to-memory mode (M=1) is future | (official) | any | PRM AMMX format page |
| `paddw (a0)+,d1,d2`, `paddw 8(a0),d1,d2`, `paddw (a0),e1,e2`, `pmull (a0)+,d1,d2`, `packuswb d1,d2,(a0)+`, `pack3216 d1,d2,(a0)+` assemble; `paddw d1,d2,(a0)` is rejected | (SRC) | any | vasm 2.0g, 2026-11-24 |
| `paddb.w #$0101` → `ff3c 1210 0101`; `paddb #$0101` → `fe3c 1210` + 8-byte immediate `0000000000000101` | (SRC) | any | vasm 2.0g, 2026-11-24 |
| Don't use `loadi`/`storei` | (G) | any | Statement, 2026-11-24 |
| Cost of a memory source against a register source | Not measured | | To be measured on Core 13000+ (G) |
