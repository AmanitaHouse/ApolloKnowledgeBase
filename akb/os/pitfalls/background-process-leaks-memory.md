---
title: Every Run or SystemTags process leaks memory and a lock on AROS-based ApolloOS
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [commands, libraries, general]
applies_to:
  core: "any"
  os: [apolloos-r10]
  mode: [os-friendly]
tags: [memory-leak, lock, progdir, shell, systemtags, run, task-resource, arexx, daemon]
related:
  - os/pitfalls/library-globals-shared-between-tasks.md
sources:
  - "ApolloOS-Port (github.com/ApolloTeam-dev/ApolloOS-Port), commits 6739caa (Shell) and 1766c2e (task.resource), 2026-11-23"
  - "ApolloOS legacy tree (github.com/ApolloTeam-dev/ApolloOS, master 0645ecc): compiler/include/dos/cliinit.h, rom/task/task_execfuncs.c, rom/task/task_support.c"
  - "ApolloOS-Port test/tools/SysAsync.c, RexxSend.c, OpenLib.c (measurements on a V4 with the R10 dev ROM, 2026-11-23)"
---

## Symptom

A program that starts processes in the background, such as a daemon
calling `SystemTags(..., SYS_Asynch, TRUE, ...)`, a script using `Run`,
or RexxMast starting one process per ARexx message, slowly loses free
memory. Each start loses up to about 100 bytes:

- 72 bytes for a lock on SFS when the starting program sits on an SFS
  volume. On RAM: the loss is hidden, because the RAM handler allocates
  from a pool.
- 32 bytes when the started command is a C program.

After a few starts from a program in drawer `X`, that drawer can no longer
be deleted ("object in use"), even though nothing is running in it any more.

Affected: ApolloOS up to R9.x (AROS-based ROM) and R10 ROMs built before
2026-11-23. Fixed in ApolloOS R10. AmigaOS 3.x is not affected; the cause
is AROS code.

## Cause

There are two independent bugs, in two ROM modules.

1. **The Shell drops the inherited PROGDIR: lock.** `CreateNewProc()` gives
   the new process a `DupLock()` of its creator's `pr_HomeDir`.
   `SystemTags()`, `Run` and `NewShell` start a Shell process. The Shell's
   startup macro `AROS_CLI` (in `dos/cliinit.h`) then sets
   `me->pr_HomeDir = BNULL` without unlocking it. One lock on the creator's
   program drawer is lost for every Shell process.
2. **task.resource does not free the hook entry.** The AROS C startup
   (`compiler/startup/startup.c`) calls `InitTaskHooks()` in every C
   program. That call adds a `TaskListHookEntry` to the task's entry in
   task.resource. When the task ends, task.resource frees the task entry
   but not the hook entry: 32 bytes per process that ran a C program. A
   long-running Shell keeps its entry, so running commands one after the
   other from one Shell shows no loss. Only new processes do.

In the same module, the entries for tasks that already exist when
task.resource starts got no `NEWLIST()` of their hook list. In that
state, `InitTaskHooks()` on such a task writes through a zeroed list,
near address 0.

## Wrong

```c
/* compiler/include/dos/cliinit.h, AROS_CLI() startup of the Shell */
type = dp->dp_Type;
me->pr_HomeDir = BNULL;          /* the DupLock from CreateNewProc is lost */
```

```c
/* rom/task: task entry freed, its hook entries are not */
Remove(&taskEntry->tle_Node);
FreeMem(taskEntry, sizeof(struct TaskListEntry));
```

## Right

The OS fix, in ApolloOS R10:

```c
UnLock(me->pr_HomeDir);          /* release the inherited lock first */
me->pr_HomeDir = BNULL;
```

```c
void task_FreeEntry(struct TaskListEntry *taskEntry)
{
    struct TaskListHookEntry *hookType, *tmp;

    if (taskEntry->tle_HookTypes.lh_Head != NULL)
        ForeachNodeSafe(&taskEntry->tle_HookTypes, hookType, tmp)
            FreeMem(hookType, sizeof(struct TaskListHookEntry));
    FreeMem(taskEntry, sizeof(struct TaskListEntry));
}
```

On systems without the fix, a program that starts many background
processes can avoid the lock leak. It clears its own home dir around the
call, so there is nothing to duplicate:

```c
BPTR home = SetProgramDir(BNULL);   /* PROGDIR: unavailable meanwhile */
SystemTags(cmd, SYS_Asynch, TRUE, SYS_Input, NULL, SYS_Output, NULL, TAG_DONE);
SetProgramDir(home);
```

This workaround follows from the source and was not measured. Do not use
PROGDIR: in other tasks of the same process while it is cleared. The
32-byte task.resource loss has no workaround in the application.

## Detection

- Measure `AvailMem(MEMF_ANY)` before and after N background starts,
  after a warm-up start so that libraries and the command are already
  loaded. More than 0 bytes per start means a leak.
- Lock check: put the starting program in a fresh drawer on the card,
  start a few `Run` or `SystemTags` processes from it, delete the program,
  then delete the drawer. "Object in use" means the home-dir lock leaked.
- Split the cost: a minimal HUNK program (`moveq #0,d0; rts`, no C
  startup) costs nothing from task.resource, and a resident command such
  as `Echo` costs nothing either.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| Async start from a starter on SFS: 72 bytes (resident Echo), 104 bytes (C program); from a starter on RAM: 0 / 32 | (M) 2026-11-23 | R10 dev ROM on V4 (core not recorded) | test/tools/SysAsync, 20 or 100 starts, AvailMem difference |
| The starter's drawer stays "in use" after async starts; deletable after a plain `CreateNewProc` | (M) 2026-11-23 | same | fresh drawer on SFS, 3 or 20 starts, then `Delete` |
| Plain `CreateNewProc()` processes leak nothing; a no-startup HUNK program leaks nothing | (M) 2026-11-23 | same | SysAsync PROC mode; hand-made 2-instruction HUNK |
| Shell with the `UnLock`: 0 bytes, drawer deletable | (M) 2026-11-23 | same | fixed Shell made resident, started via `SYS_CustomShell` |
| With both fixes in the ROM: 0 bytes per ARexx message (before ~107) and per async start; 360 parallel RX calls cost 144 bytes (log files) instead of ~40 KB | (M) 2026-11-23 | same | test/tools/RexxSend, three parallel RX loops |
| The legacy ApolloOS tree has the same code | (SRC) | any | ApolloOS master 0645ecc: cliinit.h line 170, rom/task FreeMem sites |
