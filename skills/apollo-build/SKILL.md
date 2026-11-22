---
name: apollo-build
description: Build an Apollo V4 program with ApolloCrossDev (GCC 6.5 with 68080 patches, vasm) and fix every error and warning. Use whenever code for the Apollo V4 is compiled, linked or assembled, a Makefile or build command is written or changed, compiler or assembler flags come up, or a build fails or crashes the compiler, even when it looks like an ordinary m68k GCC build, because ApolloCrossDev's variants, flags and known compiler bugs differ. Also use before presenting Apollo V4 code, to prove it builds.
---

# apollo-build

Build an Apollo V4 program the way ApolloKnowledgeBase prescribes, and leave
no error or warning behind.

**The knowledge base (KB).** The installed plugin directory is not the
user's project. Run `KB tools/resolve_kb.py` with the host launch below
and the project folder (the directory that contains the project's
`AGENTS.md`). **KB** paths below are relative to `KB_ROOT`.

**Host launch.** Use this for every `sh` entry point and every Python
program this skill names. Linux, macOS, a shell that is already WSL, and
Git Bash run `sh` on an entry point and `python3` on a program. Git Bash
(`MSYSTEM` set) still re-execs into WSL through `tools/wsl_reexec.sh`.
Do not call `wsl.exe` from those shells.

Windows PowerShell does not have `sh`. Its `python` and `python3`
commands are often Windows Store aliases and do not run Python. From
that shell, translate each Windows path and run `wsl.exe -e sh` for an
entry point or `wsl.exe -e python3` for a program. A path that starts
with `/` is unchanged. `X:\a\b` and `X:/a/b` become `/mnt/x/a/b`:
lowercase the drive letter and replace `\` with `/`. In PowerShell, pass
each translated path as one single-quoted argument. A single quote that
belongs to the path is written twice, so spaces and quotation marks stay
inside the argument. The plugin directory is the directory that contains
`.cursor-plugin/plugin.json` beside the loaded skill. Do not hard-code a
user name, a project location, or a drive letter. The same contract is
[Host launch](../../docs/cursor-plugin.md#host-launch).

1. `KB_SOURCE=submodule`: the project's `ApolloKnowledgeBase/` checkout.
   Its pinned commit is authoritative. Use it.
2. `KB_SOURCE=plugin`: there is no project submodule. Use the knowledge
   base bundled with the installed plugin (the repository that contains
   this skill, whether Claude Code or Cursor loaded it).
3. `PROBLEM=`: neither is accessible, or the submodule is present but not
   initialized. Stop, quote the `PROBLEM=` and `RECOVERY=` lines, and do
   not build from memory.

Pass that same project folder to `scripts/find-acd.sh`. Honour
`APOLLOCROSSDEV` when it is set: the script looks there first.

## 1. Know the target

Read the project's `AGENTS.md`: target OS, execution mode, languages. If it
is missing, ask; don't guess the target OS, it decides the headers.

## 2. Check the toolchain

Run `scripts/find-acd.sh` with the host launch, passing `--offline` only
when a network check must be skipped, then the project folder. On
PowerShell that is `wsl.exe -e sh` and translated paths. On Linux, macOS,
WSL, and Git Bash it is `sh`.

It prints `ACD_ROOT`, `PREFIX`, `GCC`, `BUILT`, the template and project
Makefile versions, `BUILD=`, `BUILD_DETAIL=`, NDK status lines when a
requirement is established (`NDK=`, `NDK_PATH=`, `NDK_COMPILER=`,
`NDK_STATUS=`), `PROBLEM=`, `NOTE=` and `UPDATE=` lines (`--offline` skips
the check on GitHub). `UPDATE=compiler` also comes from the local checkout
alone: a compiler built before the install script or patches there last
changed, for example after a `git pull` without a reinstall. `UPDATE=` is not
permission to update ApolloCrossDev.

Documented NDK directories are taken from `KB toolchain/target-os-headers.md`:
`m68k-amigaos/ndk39-include` (NDK 3.9) and
`m68k-amigaos/ndk32-include/Include_H` (NDK 3.2), under the effective
compiler `PREFIX` when that location can be established from the Makefile
without evaluating Make. Recognised shapes are
`PREFIX=$(ACD_ROOT)/Compilers/GCC-6.50-Dev|Stable|Base` when `ACD_ROOT`
resolves (set `APOLLOCROSSDEV`, or a project two levels under
ApolloCrossDev), and the v1.0 form
`PREFIX=$(PWD)/../../Compilers/GCC-6.50-...` only when the project is two
levels under ApolloCrossDev. A Dev/Stable/Base label alone is not a path.
`PREFIX=` from find-acd.sh itself remains the GCC-6.50-Dev completeness
check and is not proof that the project Makefile uses Dev. An active NDK
requirement needs an uncommented `C_INCL_NDK` that names a documented path
and is shown to feed flags through `C_INCL_ALL` and `C_FLAGS` (the template
shape); without a Makefile, a concrete `Target OS` in `AGENTS.md`
(AmigaOS 3.9 → NDK 3.9; AmigaOS 3.2 or ApolloOS R10 → NDK 3.2). If the
compiler location or NDK requirement cannot be established, the script
prints `NOTE=` uncertainty and does not invent a selection. It never treats
`m68k-amigaos/ndk-include` as a documented NDK.

- Fix every `PROBLEM` before building, with the user: a missing toolchain
  means installing ApolloCrossDev (`KB toolchain/index.md`, section
  Install), a wrong `APOLLOCROSSDEV` means correcting it, and a missing
  documented NDK directory means restoring that NDK under the reported
  `NDK_COMPILER=` path. Do not point the build at `ndk-include` or any
  other undocumented tree and call it the NDK.
- A `BUILD=` line does not override an unresolved `PROBLEM=` (including a
  missing required NDK). Do not compile until that `PROBLEM=` is resolved.
- Act on the `NOTE=` lines. A `NOTE=` that a documented NDK directory is
  absent without an established requirement is informational; do not block
  on an NDK the active configuration does not use.
- `UPDATE=` lines don't block the build. Mention them once per session and
  let the user decide: `UPDATE=checkout` is a quick `git pull` (mind
  `LOCAL_CHANGES=`), `UPDATE=compiler` a reinstall of about 30 minutes that
  the user runs. Do not run `sudo`, do not edit shell startup files, and do
  not `git pull` ApolloCrossDev unless the user agrees.

A checkout of ApolloCrossDev is not the compiler you are about to run.
`m68k-btst-mem-offset-fix.patch` (pull request #26) and
`reload-ind-equiv-offset-fix.patch` (pull request #28) are applied by the
GCC-6.50-Dev and GCC-6.50-Stable install scripts, Linux and macOS. The Base
scripts do not apply them. The binary includes a fix only when that install
built it. `UPDATE=compiler`, or a `NOTE=` that those patch files are absent
from the checkout, means the installed GCC-6.50-Dev binary is unverified
for that fix. Say so. Do not reinstall unless the user asks.

Before trusting code built with the standard flags, read:

- `toolchain/pitfalls/gcc-btst-memory-bit-number.md`
- `toolchain/pitfalls/gcc-double-indirect-stack-slot.md`
- `toolchain/compiler-variants.md`
- `toolchain/c-compiler-options.md`

The variants article is the reviewed list of which install is current. Its
bug table does not yet name these two defects; the pitfalls do, and they
are draft. The standard flags stay the ones in `toolchain/c-compiler-options.md`.
Do not add `-mno-bitfield` or `-fno-double-indirect` to that set. Those are
the workarounds the pitfalls document for an unverified binary. Name them
and let the user decide. Do not present a build with the standard flags on
an unverified binary as free of these defects.

Confirmed means the installed binary, not the checkout. Use the install
log that applied the patch, or assembly of the pitfall's reproduction.
Compiling without an error is not confirmation. For the stack-slot defect,
read the operand after the call: `add.l d2,([76,sp])` is the corrected
form in pull request #28, and `add.l d2,([56,sp])` while that call's 20
bytes are still pushed is the bug. An older binary that keeps the pointer
in a register and never emits `([N,sp])` for that update has not been
shown to contain the reload fix.

## 3. Build

The project's Makefile comes from ApolloCrossDev's template
(`Projects/_makefiles/Makefile`, see `KB toolchain/project-makefile.md`).
`scripts/find-acd.sh` classifies that Makefile with
`KB tools/classify_build.py`. It does not run make. The classifier is the
only build-command policy: do not keep a second one.

| find-acd.sh line | What you do |
|---|---|
| `BUILD=make compile` or `BUILD=make cleanbefore build` | Run that command. `BUILD_DETAIL=` says why it was classified as non-uploading. |
| `NOTE=` that no Make command can be recommended | Do not run make. Do not invent `make compile` or `make cleanbefore build`. |
| no project Makefile | Use the flags in `KB toolchain/c-compiler-options.md` exactly, and the NDK from step 4. |

- A `BUILD=` line is the only Make command this skill runs on its own.
  `make` and `make debug` upload on the documented templates. Run them only
  when the user asks.
- Do not treat a missing `compile` target, a recipe that never mentions
  `acp`, or an `UPDATE=` line as permission to choose a target or to update
  ApolloCrossDev. The user decides about `UPDATE=`.
- The classifier walks the selected target's prerequisites, expanded
  variables, included Makefiles, and recursive make that stays in the same
  file. It recognizes the documented ApolloCrossDev template shape. An
  unsupported or ambiguous construct is unverified, and then there is no
  `BUILD=` line.
- The Makefile hides compiler stdout; errors and warnings arrive on stderr.
  Read all of it.
- Without a Makefile (a quick test), use the flags from
  `KB toolchain/c-compiler-options.md` exactly, and the NDK from step 4.
  If that NDK path is not on disk, say so. Do not substitute another
  include directory and call it the documented NDK.

## 4. Settings: take them from the KB, never from memory

| Setting | Rule | KB file |
|---|---|---|
| Compiler variant | GCC-6.50-Dev; GCC-6.50-Stable only to test a suspected compiler bug; never GCC 13/15 | `toolchain/compiler-variants.md` |
| C/C++ flags | `-O2 -m68080 -m68881 -ffast-math -fomit-frame-pointer`, libnix (`-noixemul`) | `toolchain/c-compiler-options.md` |
| NDK headers | NDK 3.2 for AmigaOS 3.2 and ApolloOS R10; NDK 3.9 as soon as AmigaOS 3.9 is a target | `toolchain/target-os-headers.md` |
| Assembler | vasm, `-Fhunk -m68080 -m68881` | `toolchain/vasm-assembler.md` |
| ApolloLib | compiled from its sources by the template (`APOLLOLIB`) | `toolchain/apollolib/index.md` |

Don't add `-m68060`, `-m68040` or `-mtune=68060`, don't drop `-m68881` from
code that uses floats, and don't mix libnix and clib2 objects. Don't invent
flags: if the KB doesn't document one, say so. Don't add the section 2
workarounds to the standard flags.

## 5. Fix errors and warnings

Fix the cause in the code, not by silencing the warning. Before you change
code around a symptom, check whether it is a known trap:

| Symptom | Read in the KB |
|---|---|
| Internal compiler error, or wrong code that looks like a compiler bug | First an `UPDATE=compiler` from step 2: the fix may only need a reinstall. Then `toolchain/compiler-variants.md` (bug table: fixed only in a reinstalled GCC-6.50-Dev) and the pitfall it names |
| `btst` on memory with a bit number outside 0 to 7 | `toolchain/pitfalls/gcc-btst-memory-bit-number.md`. Section 2: the binary is fixed only when it was built with pull request #26 |
| A pointer argument updated through `([N,sp])` after a call | `toolchain/pitfalls/gcc-double-indirect-stack-slot.md`. Section 2: the reload fix is pull request #28, and the standard flags are the affected configuration on an unreinstalled GCC-6.50-Dev |
| Floats wrong, or link errors about float functions | `toolchain/pitfalls/float-settings-mismatch.md` |
| `sprintf`, headers or libnix surprises | `toolchain/pitfalls/libnix-and-header-traps.md` |
| Other GCC oddities | `toolchain/pitfalls/gcc-misc-traps.md` |
| C calling assembler, registers lost | `toolchain/pitfalls/calling-assembler-from-gcc.md` |
| vasm rejects or mis-encodes a 68080 instruction | `toolchain/pitfalls/vasm-68080-encoding-issues.md`, `toolchain/pitfalls/vasm-pc-relative-destination.md` |
| A function missing on one target OS | `toolchain/target-os-headers.md` (build against the oldest target's NDK) |
| ApolloLib misbehaves | `toolchain/pitfalls/apollolib-known-bugs.md` |

Other files in `KB toolchain/pitfalls/` cover single GCC bugs; list the
folder when a symptom doesn't match the table.

## 6. Report

Say which command you ran, the variant and Makefile version, and that the
build ended with no errors and no warnings, or what is left and why. Never
claim a successful build unless that command actually ran and exited with
no errors and no warnings. If the KB was wrong or missing something on the
way, tell the user and offer a lesson (the akb-lesson skill) or a KB change.
