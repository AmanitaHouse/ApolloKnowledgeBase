---
title: ApolloExplorer 1.4.4, an "unstable network" that was a driver, and server fixes
type: lesson
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [devs, libraries, general]
applies_to:
  core: "Core 12856"
  os: [apolloos-r10]
  mode: [os-friendly]
  board: [v4-unicorn]
tags: [network, tcp, bsdsocket, arostcp, v4net, mtu, systemtaglist, priority, testing]
related:
  - os/pitfalls/v4net-full-size-frames-lost.md
  - os/pitfalls/v4-rom-modules-and-reset.md
sources:
  - "WDrijver/ApolloExplorer pull request #9, commits 5d466e9 and 4f4b504 (2026-11-16)"
  - "Test harness tests/aetest.py and tests/mockserver.py in WDrijver/ApolloExplorer"
  - "Measured on a V4 UniCorn, Core 12856, ApolloOS R9.6, v4net.device 3.0, 2026-11-16"
  - "ApolloOS source: AROSTCP tcp_usrreq.c, tcp_output.c, kern/uipc_socket.c; rom/dos/systemtaglist.c, createnewproc.c"
---

## Project

ApolloExplorer (github.com/WDrijver/ApolloExplorer, fork of
ronybeck/ApolloExplorer): a TCP server on the V4 (`ApolloExplorerSrv`) with
PC clients, the GUI, `acp` (copy) and `ash` (remote shell). Reported
problem: `acp` connections were unstable and `ash` mostly did not respond.
Worked on by Claude (AI) with WDrijver on 2026-11-16; result: server 1.4.4
in pull request #9.

## What went well

- **A protocol-level test harness first.** `tests/aetest.py` speaks the wire
  protocol directly, so a failure points at the server or the network, not
  at the Qt clients. A mock server with fault injection (split messages,
  pings, latency) showed the clients were fine before anyone touched the V4.
- **Narrowing down by size.** Growing a directory listing one entry at a
  time showed replies up to 1435 bytes arrive and 1497 bytes never do; a
  `ping -D -s` binary search then proved it outside the application.
- **Reading the ApolloOS source instead of assuming.** The AROSTCP and DOS
  sources answered three questions that classic Amiga knowledge would have
  answered wrongly or not at all (see the evidence table).
- **Before and after numbers for every fix.** Each fix got a test scenario
  first (`busy`, `churn --op cd`, `fault split-header`), measured on the old
  server, then on the new one.

## What went wrong

- Two earlier server fixes were reverted without a recorded reason. One of
  them set `NP_Priority` in the `SystemTagList()` tags, which does nothing on
  ApolloOS (below), so it could not have worked as intended.
- Server threads stuck sending to the V4's lost packets could not be shut
  down; switching server versions needed power cycles. A soft reset was
  avoided because of `os/pitfalls/v4-rom-modules-and-reset.md`.
- Each failed test left a stuck session on the old server until it was
  restarted.

## What the AI got wrong

- **Blamed the server code first.** From the code review alone, the AI
  ranked five server bugs as the likely causes. They were real, but the main
  cause was the V4's Ethernet driver (`os/pitfalls/v4net-full-size-frames-lost.md`).
  Only measuring on the V4 found it.
- **Misread a test failure.** A download that failed with "0 of 12 header
  bytes" was first read as the server not sending its 16-byte
  acknowledgement. Reading the server code showed the acknowledgement was
  sent; what never arrived was the next, larger message.
- **Took the OS version from the conversation instead of the machine.** The
  developer said ApolloOS R10; the server's discovery reply said R9.6. The AI
  first wrote "R10" in a code comment.
- **Proposed an ApolloOS issue for the driver.** `v4net.device` is not in the
  ApolloOS repository; it lives in the apollo-core SVN
  (`apollo_software/net/V4Net`) and also runs on AmigaOS.
- **Got a protocol constant wrong in its own test tool.** It treated 0 as
  success for `PMT_MKDIR`; the server answers `AT_OK` (1).

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| The V4 never sends a 1500-byte IP packet; 1498 bytes works; receiving 1500 works | (M) | Core 12856 | `ping -D -s` binary search, size sweep 0 to 1470, TCP upload; v4net.device 3.0, ApolloOS R9.6 |
| `TCP_MAXSEG` 1400 on the accepted socket fixes large replies | (M) | Core 12856 | `tests/aetest.py smoke/shell/transfer`: all timed out before, all pass after |
| `TCP_MAXSEG` can only lower the MSS a connection negotiated, so it must be set after `accept()`/`connect()` | (SRC) | any | AROSTCP `netinet/tcp_usrreq.c` |
| AROSTCP supports `SO_RCVTIMEO`/`SO_SNDTIMEO`; non-blocking only via `FIONBIO` (no `MSG_DONTWAIT`) | (SRC) | any | AROSTCP `kern/uipc_socket.c` |
| `NP_Priority` in `SystemTagList()` tags is ignored: its own `NP_Priority` (the caller's) comes first and `CreateNewProc()` uses the first match | (SRC) | any | ApolloOS `rom/dos/systemtaglist.c` (`TAG_MORE` after its defaults), `createnewproc.c` (`ApplyTagChanges`) |
| A shell command started from a priority-8 task starves AROSTCP: no new connection for 9.5 s during `List SYS: ALL` | (M) | Core 12856 | `tests/aetest.py busy`; with `SetTaskPri(0)` around `SystemTagList()`: 46 replies, median 56 ms |
| A finished session left its server thread alive ~60 s: 30 sessions held 4.6 MB, all back after 90 s | (M) | Core 12856 | `tests/aetest.py churn --avail`; after the fix -19 KB |
| A header split with a 200 ms gap dropped the connection (50 `FIONREAD` polls without waiting) | (M) | Core 12856 | `tests/aetest.py fault split-header`, before and after |

## Candidates for distillation

- `os/pitfalls/v4net-full-size-frames-lost.md`: added together with this
  lesson. Deprecate it once a fixed `v4net.device` is released.
- **`SystemTagList()` ignores `NP_Priority`.** First check AmigaOS 3.x: if it
  honours the tag, this is an ApolloOS bug for an issue in
  ApolloTeam-dev/ApolloOS.R10 (CONTRIBUTING.md section 2); if it does not,
  it becomes an `os/pitfalls/` file for `os: [any]`. Either way: lower the
  calling task with `SetTaskPri()` while the command runs.
- **A reference file for bsdsocket on V4** (`os/libraries/`): which TCP/IP
  stack each OS uses, the AROSTCP socket options above, and that the
  knowledge base has nothing on networking yet.
- **A guide for testing network services on V4** (`guides/`): a
  protocol-level harness separate from the client, a mock server for the
  client side, ping size sweeps, and before/after numbers per fix.
