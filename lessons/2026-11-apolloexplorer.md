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
  os: [apolloos-r10, amigaos-3.9]
  mode: [os-friendly]
  board: [v4-unicorn]
tags: [network, tcp, bsdsocket, arostcp, amitcp-ng, v4net, mtu, systemtaglist, priority, testing]
related:
  - os/pitfalls/v4net-full-size-frames-lost.md
  - os/pitfalls/v4-rom-modules-and-reset.md
  - guides/testing-on-v4-hardware.md
sources:
  - "WDrijver/ApolloExplorer pull request #9, commits 5d466e9 and 4f4b504 (2026-11-16)"
  - "Test harness tests/aetest.py and tests/mockserver.py in WDrijver/ApolloExplorer"
  - "Measured on a V4 UniCorn, Core 12856, v4net.device 3.0, under ApolloOS R9.6 (AROSTCP) and AmigaOS 3.9 (AmiTCP_NG 4.1.8), 2026-11-16"
  - "ApolloOS source: AROSTCP tcp_usrreq.c, tcp_output.c, kern/uipc_socket.c; rom/dos/systemtaglist.c, createnewproc.c"
  - "AmiTCP_NG source (github.com/MW0MWZ/AmiTCP_NG): src/netinet/tcp_usrreq.c, src/net/ng_ifconfig.c, src/kern/uipc_socket.c"
  - "V4Net source (github.com/ApolloTeam-dev/V4Net) and pull request #1: v4net.device 3.1, MTU 1498 (2026-11-24)"
  - "Measured on a V4 UniCorn, Core 12856, v4net.device 3.0 and 3.1, under ApolloOS R9.9 (AROSTCP bsdsocket.library 4.57), 2026-11-24 and 2026-11-25"
  - "WDrijver/ApolloCrossDev issue #33 (GCC-6.50-Dev internal compiler error in bbb pass i)"
---

## Project

ApolloExplorer (github.com/WDrijver/ApolloExplorer, fork of
ronybeck/ApolloExplorer): a TCP server on the V4 (`ApolloExplorerSrv`) with
PC clients, the GUI, `acp` (copy) and `ash` (remote shell). Reported
problem: `acp` connections were unstable and `ash` mostly did not respond.
Worked on by Claude (AI) with WDrijver on 2026-11-16, first under ApolloOS,
then under AmigaOS 3.9; result: server 1.4.4 in pull request #9, plus
`mtu=1492` in the AmigaOS interface configuration.

Follow-up on 2026-11-24 and 25, once the `v4net.device` source was public
(github.com/ApolloTeam-dev/V4Net): the root cause was found in the driver
and fixed there as `v4net.device` 3.1 (V4Net pull request #1, released as
3.1-beta in ApolloSoftware). Tested under ApolloOS R9.9; ApolloExplorer
1.4.5 then dropped its `TCP_MAXSEG` workaround.

## What went well

- **A protocol-level test harness first.** `tests/aetest.py` speaks the wire
  protocol directly, so a failure points at the server or the network, not
  at the Qt clients. A mock server with fault injection (split messages,
  pings, latency) showed the clients were fine before anyone touched the V4.
- **Narrowing down by size.** Growing a directory listing one entry at a
  time showed replies up to 1435 bytes arrive and 1497 bytes never do; a
  `ping -D -s` binary search then proved it outside the application.
- **Reading the stack and OS sources instead of assuming.** The AROSTCP,
  AmiTCP_NG and DOS sources answered questions that classic Amiga knowledge
  would have answered wrongly or not at all (see the evidence table).
- **Before and after numbers for every fix.** Each fix got a test scenario
  first (`busy`, `churn --op cd`, `fault split-header`), measured on the old
  server, then on the new one, then again under the second OS.
- **Remote configuration without seeing the output.** With large replies
  lost, `Search >NIL:` return codes (0 found, 5 not found) and output-free
  commands (`Copy`, `Echo >>`) were enough to back up, check and change
  `DEVS:NetInterfaces/V4net` on a V4 without a working keyboard.
- **Workarounds first, the structural fix in the right place later.** The
  workarounds made ApolloExplorer usable the same day; the developer then
  waited for the driver source instead of piling up more. Reading
  `v4l_TransmitFrame` explained the exact limit (1512 bytes works, 1513
  does not), and a driver that reports MTU 1498 fixes every stack and every
  program at once.
- **The same test harness proved the driver fix.** ApolloExplorerSrv 1.4.2,
  which has no workaround, was the test client: with v4net.device 3.0 it
  hung, with 3.1 and no configuration every scenario passed.

## What went wrong

- Two earlier server fixes were reverted without a recorded reason. One of
  them set `NP_Priority` in the `SystemTagList()` tags, which does nothing on
  ApolloOS (below), so it could not have worked as intended.
- Server threads stuck sending to the V4's lost packets could not be shut
  down; switching server versions needed power cycles. A soft reset was
  avoided because of `os/pitfalls/v4-rom-modules-and-reset.md`.
- Each failed test left a stuck session on the old server until it was
  restarted.
- The fix that passed every test under ApolloOS failed under AmigaOS, because
  it depended on a socket option one stack has and the other lacks.
- ApolloExplorerSrv does not start at boot on the test V4, so after a power
  cycle no remote work is possible until someone starts it by hand.
- The driver did not build with the current GCC-6.50-Dev: an internal
  compiler error in bebbo's bbb pass `i` on unchanged code, still present
  after a reinstall. Worked around with `-fbbb=-` for that one file and
  reported as ApolloCrossDev issue #33.

## What the AI got wrong

- **Blamed the server code first.** From the code review alone, the AI
  ranked five server bugs as the likely causes. They were real, but the main
  cause was the V4's Ethernet driver (`os/pitfalls/v4net-full-size-frames-lost.md`).
  Only measuring on the V4 found it.
- **Assumed `TCP_MAXSEG` works on every stack.** It read the AROSTCP source
  and stopped there; the server also ignored the `setsockopt()` result.
  AmiTCP_NG does not implement the option, so under AmigaOS 3.9 the fix did
  nothing and failed silently.
- **Blamed the driver for loss it did not cause.** Under ApolloOS, about one
  packet per 4 MB was lost in bursts; the AI attributed that to the driver.
  Under AmigaOS 3.9 with the same driver and core, 4 MB downloads showed no
  loss at all, so it is not the driver alone. The cause is still unknown.
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
- **Waited 3 minutes after a power cycle.** The V4 is up in 15 to 35 s
  (`guides/testing-on-v4-hardware.md`); a timeout should be based on that.
- **Got a protocol constant wrong in its own test tool.** It treated 0 as
  success for `PMT_MKDIR`; the server answers `AT_OK` (1).
- **Took the OS from the discovery reply again.** The second test V4
  answered discovery with "AmigaOS / ApolloOS -", and the AI wrote
  "AmigaOS" into a pull request; it was ApolloOS R9.9. Check `Version` and
  the TCP/IP stack's files on the machine instead.
- **Left the version number to someone else without looking.** The AI kept
  the driver fix at version 3.0 as "unreleased". ApolloSoftware already
  had 3.0-beta released, so the fix was 3.1; the binaries it built could not
  be told apart from 3.0 with `Version`.

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| The V4 never sends a 1500-byte IP packet; 1498 bytes works; receiving 1500 works | (M) | Core 12856 | `ping -D -s` binary search, size sweep 0 to 1470, TCP upload; v4net.device 3.0, ApolloOS R9.6 and AmigaOS 3.9 |
| `TCP_MAXSEG` 1400 on the accepted socket fixes large replies under AROSTCP | (M) | Core 12856 | `tests/aetest.py smoke/shell/transfer` on ApolloOS R9.6: all timed out before, all pass after |
| `TCP_MAXSEG` can only lower the MSS a connection negotiated, so it must be set after `accept()`/`connect()` | (SRC) | any | AROSTCP `netinet/tcp_usrreq.c` |
| AmiTCP_NG 4.1.8 rejects `TCP_MAXSEG` with `EINVAL`; it reads `mtu=` from the interface file | (SRC) | any | AmiTCP_NG `src/netinet/tcp_usrreq.c` ("not yet"), `src/net/ng_ifconfig.c` |
| `mtu=1492` in `DEVS:NetInterfaces/V4net` fixes large replies under AmiTCP_NG | (M) | Core 12856 | AmigaOS 3.9: replies up to 3771 bytes arrive; every `tests/aetest.py` scenario passes |
| AROSTCP and AmiTCP_NG both support `SO_RCVTIMEO`/`SO_SNDTIMEO`; non-blocking only via `FIONBIO` (no `MSG_DONTWAIT`) | (SRC) | any | AROSTCP and AmiTCP_NG `kern/uipc_socket.c` |
| `NP_Priority` in `SystemTagList()` tags is ignored: its own `NP_Priority` (the caller's) comes first and `CreateNewProc()` uses the first match | (SRC) | any | ApolloOS `rom/dos/systemtaglist.c` (`TAG_MORE` after its defaults), `createnewproc.c` (`ApplyTagChanges`) |
| A shell command started from a priority-8 task starves AROSTCP: no new connection for 9.5 s during `List SYS: ALL` | (M) | Core 12856 | `tests/aetest.py busy` on ApolloOS R9.6; with `SetTaskPri(0)` around `SystemTagList()`: 46 replies, median 56 ms; on AmigaOS 3.9: 89 replies, median 36 ms |
| A finished session left its server thread alive ~60 s: 30 sessions held 4.6 MB, all back after 90 s | (M) | Core 12856 | `tests/aetest.py churn --avail`; after the fix -19 KB (ApolloOS), -15 KB (AmigaOS) |
| A header split with a 200 ms gap dropped the connection (50 `FIONREAD` polls without waiting) | (M) | Core 12856 | `tests/aetest.py fault split-header`, before and after |
| Since 2.97.2 `v4l_TransmitFrame` declares the TX length rounded up to a longword: a 1513/1514-byte frame becomes 1516, 1520 with CRC, over the 1518-byte limit | (SRC) | any | V4Net `source/v4net/v4l.c`, `CHANGELOG.txt` |
| v4net.device 3.1 (MTU 1498) fixes large replies with no configuration and no application workaround | (M) | Core 12856 | ApolloOS R9.9, ApolloExplorerSrv 1.4.2: `tests/aetest.py` smoke, shell, transfer, concurrent pass; with 3.0 they hang. With 1.4.4: 4 × 200 sessions, 20 transfers up to 10 MB, 6 parallel clients, 0 failures |
| About one lost packet per 4 MB (1.2 to 1.5 s stall) under ApolloOS; none under AmigaOS | (M) | Core 12856 | Per-chunk arrival times of 4 MB downloads: ApolloOS R9.6 with `TCP_MAXSEG` 1400, 1.1 to 1.25 MB/s; AmigaOS 3.9 with `mtu=1492`, 4.2 to 4.3 MB/s, largest gap 15 ms |

## Candidates for distillation

- `os/pitfalls/v4net-full-size-frames-lost.md`: added together with this
  lesson, updated for the fix in v4net.device 3.1. Deprecate it once 3.1
  is the regular release (out of beta) and tested under AmigaOS.
- **`SystemTagList()` ignores `NP_Priority`.** First check AmigaOS 3.x: if it
  honours the tag, this is an ApolloOS bug for an issue in
  ApolloTeam-dev/ApolloOS.R10 (CONTRIBUTING.md section 2); if it does not,
  it becomes an `os/pitfalls/` file for `os: [any]`. Either way: lower the
  calling task with `SetTaskPri()` while the command runs.
- **A reference file for bsdsocket on V4** (`os/libraries/`): which TCP/IP
  stack each OS uses (AROSTCP on ApolloOS, AmiTCP_NG or Roadshow on
  AmigaOS), which socket options each supports, and the interface
  configuration keywords such as `mtu=`. The knowledge base has nothing on
  networking yet.
- **The lost packets under ApolloOS.** Not the driver alone (none under
  AmigaOS with the same driver). Compare AROSTCP and AmiTCP_NG at the same
  MSS before filing anything.
- **A guide for testing network services on V4** (`guides/`): a
  protocol-level harness separate from the client, a mock server for the
  client side, ping size sweeps, `Search >NIL:` return codes when output
  cannot come back, and before/after numbers per fix.
