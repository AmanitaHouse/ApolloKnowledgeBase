---
title: v4net.device before 3.1 loses full-size Ethernet frames
type: pitfall
owner: WDrijver
status: draft
origin: ai-assisted
basis: [measured, source-code]
components: [devs]
applies_to:
  core: "Core 12856"
  os: [apolloos-r10, amigaos-3.9]
  mode: [os-friendly]
  board: [v4-unicorn]
tags: [network, ethernet, v4net, mtu, mss, tcp, arostcp, amitcp-ng, bsdsocket, stall]
related:
  - os/pitfalls/v4-rom-modules-and-reset.md
  - guides/testing-on-v4-hardware.md
sources:
  - "Measured on a V4 UniCorn, Core 12856, v4net.device 3.0, under ApolloOS R9.6 (AROSTCP) and AmigaOS 3.9 (AmiTCP_NG 4.1.8), 2026-11-16 (ping size sweeps, tests/aetest.py of WDrijver/ApolloExplorer)"
  - "Measured on a V4 UniCorn, Core 12856, v4net.device 3.0 and 3.1, under ApolloOS R9.9 (AROSTCP bsdsocket.library 4.57), 2026-11-24 and 2026-11-25"
  - "V4Net source (github.com/ApolloTeam-dev/V4Net): source/v4net/v4l.c (v4l_TransmitFrame), source/v4net/hwprivate.h, CHANGELOG.txt"
  - "ApolloTeam-dev/V4Net pull request #1 (fix: MTU 1498, v4net.device 3.1)"
  - "ApolloTeam-dev/ApolloSoftware: Drivers/v4net.device/3.1-beta"
  - "ApolloOS source: workbench/network/stacks/AROSTCP/bsdsocket/netinet/tcp_usrreq.c, tcp_output.c"
  - "AmiTCP_NG source (github.com/MW0MWZ/AmiTCP_NG): src/netinet/tcp_usrreq.c, src/net/ng_ifconfig.c"
  - "WDrijver/ApolloExplorer pull request #9"
  - "lessons/2026-11-apolloexplorer.md"
---

## Symptom

A TCP connection from the V4 stalls as soon as the V4 sends more than about
1.4 KB in one go. Small replies keep arriving, and data sent *to* the V4
arrives fine, so the connection looks alive but "unstable". In
ApolloExplorer, every `ash` command with output and every download hung,
while uploads worked. Seen under ApolloOS and under AmigaOS 3.9 alike.

From any other host on the LAN:

```sh
ping -D -s 1470 <v4-ip>     # 1498-byte IP packet: reply
ping -D -s 1472 <v4-ip>     # 1500-byte IP packet: no reply, ever
```

## Cause

`v4net.device` 3.0 does not transmit a 1513- or 1514-byte Ethernet frame
(a 1499- or 1500-byte IP packet); 1512 bytes and smaller work (M). Receiving
full-size frames works (M).

The reason is in the driver (SRC): since 2.97.2, `v4l_TransmitFrame`
declares the TX length rounded up to a longword, the length it actually
pushes into the TX FIFO (a fix for dropped frames on IceDrake cores 11901
and 12205, `CHANGELOG.txt`). A 1513- or 1514-byte frame is then declared as
1516 bytes, 1520 with the CRC: over the 1518-byte Ethernet limit, so the MAC
never sends it.

The driver still reported an MTU of 1500, so the TCP/IP stack built
1500-byte packets: TCP used an MSS of 1460, and every full-size segment was
lost and retransmitted at the same size forever. The same happens under
ApolloOS (AROSTCP) and AmigaOS 3.9 (AmiTCP_NG), so it is the driver, not the
OS or the stack.

**Fixed in `v4net.device` 3.1** (24.11.2026, in ApolloSoftware as
`Drivers/v4net.device/3.1-beta`): the driver reports an MTU of 1498 to every
stack (`S2_DEVICEQUERY`, and the netdev personality) and clamps `MTU=` in
its config to 1498 (SRC: `HW_MAX_MTU` in `source/v4net/hwprivate.h`).

Not yet known: which releases before 2.97.2 are unaffected, and how 3.1
behaves under AmigaOS 3.9 and 3.2 (tested under ApolloOS R9.9 only).

## Wrong

```c
/* Server: accept and send.  With v4net.device 3.0, every reply over
   ~1.4 KB never arrives. */
SOCKET client = accept( listenSocket, (struct sockaddr *)&addr, &addrLen );
send( client, reply, replyLength, 0 );
```

## Right

**Use `v4net.device` 3.1 or later.** Then nothing is needed in the stack
configuration or in the program: the code above works (M). Check with
`Version DEVS:Networks/v4net.device`.

**With an older `v4net.device`**, keep packets at 1498 bytes or below. In
order of preference:

1. **In the driver config, for every stack:** `MTU=1498` in
   `ENVARC:SANA2/v4net.config` (copy it to `ENV:SANA2/` or reboot). The
   driver then reports 1498 to the stack (M, v4net.device 3.0 on ApolloOS
   R9.9).

2. **In the stack's interface file (AmiTCP_NG):** AmiTCP_NG reads `mtu=` from
   `DEVS:NetInterfaces/V4net` (SRC: `src/net/ng_ifconfig.c`; it is clamped to
   the device MTU). Add the line and restart the network (power-cycle the
   V4):

   ```text
   mtu=1492
   ```

   The stack then sends at most 1492-byte packets and uses an MSS of 1452
   (M). The interface file in ApolloSoftware's v4net.device 3.0-beta and
   3.1-beta already has this line. AROSTCP on ApolloOS did not apply it (M,
   R9.9).

3. **In one program: `TCP_MAXSEG` on the connected socket.** AROSTCP
   (ApolloOS) only lets `TCP_MAXSEG` lower the MSS a connection has
   negotiated (SRC: `tcp_usrreq.c` accepts a value only when it is
   `<= tp->t_maxseg`). On a listen socket `t_maxseg` is still the 512-byte
   default, so 1400 is refused there with `EINVAL`. `tcp_output.c` caps every
   segment at `t_maxseg` (SRC). AmiTCP_NG 4.1.8 does not implement
   `TCP_MAXSEG` at all: setting it returns `EINVAL` ("not yet", SRC:
   `src/netinet/tcp_usrreq.c`), so check the result.

   ```c
   /* Server: after accept().  A client: after connect(). */
   SOCKET client = accept( listenSocket, (struct sockaddr *)&addr, &addrLen );
   int maxSegmentSize = 1400;      /* 1400 + 40 bytes headers + TCP options < 1498 */
   if( setsockopt( client, IPPROTO_TCP, TCP_MAXSEG, &maxSegmentSize, sizeof( maxSegmentSize ) ) < 0 )
   {
       /* Not supported by this stack (AmiTCP_NG): large sends will stall
          unless the MTU is lowered in the driver or interface config. */
   }
   send( client, reply, replyLength, 0 );
   ```

   `TCP_MAXSEG` is `0x02` in the ApolloCrossDev NDK header (`netinet/tcp.h`),
   AROSTCP and AmiTCP_NG. Don't build this into a program for new drivers:
   ApolloExplorer 1.4.5 drops it again now that 3.1 is out.

## Detection

- `ping -D -s 1472 <v4-ip>` from another host gets no reply, while
  `ping -D -s 1470` does. This fails with every driver, also 3.1: the
  1500-byte reply must be fragmented and `-D` forbids that. The useful test
  is `ping -s 3000 <v4-ip>` (fragmented): a reply with 3.1 or with an MTU
  workaround, none with 3.0 and no workaround (M).
- Check the driver version: `Version DEVS:Networks/v4net.device`.
- A TCP service on the V4 whose small replies work but whose large ones
  never arrive (the client receives not even the first byte).

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| A 1500-byte IP packet from the V4 never arrives; 1498 bytes does | (M) | Core 12856 | `ping -D -s` binary search from a Mac on the same gigabit LAN, v4net.device 3.0, ApolloOS R9.6 and AmigaOS 3.9 |
| Every payload size 0 to 1470 bytes gets a reply | (M) | Core 12856 | One ping per size, spaced out, ApolloOS R9.6 |
| The V4 receives 1500-byte packets | (M) | Core 12856 | TCP upload with 1460-byte segments, 200 KB in 0.33 to 0.36 s, both OSes |
| Other hosts on the same LAN send 1500-byte packets fine | (M) | n/a | `ping -D -s 1472` to three other hosts |
| TCP replies up to 1435 bytes arrive, 1497 bytes never | (M) | Core 12856 | Directory listing grown one entry at a time, both OSes |
| Since 2.97.2 the declared TX length is rounded up to a longword: 1513/1514 bytes become 1516, 1520 with CRC | (SRC) | any | V4Net `v4l_TransmitFrame`, `CHANGELOG.txt` 2.97.2 |
| `MTU=1498` in v4net.config fixes it with v4net.device 3.0 | (M) | Core 12856 | ApolloOS R9.9, ApolloExplorerSrv 1.4.2 (no workaround): fragmented pings to 8000 bytes, TCP replies to 3771 bytes, `tests/aetest.py` smoke, shell, transfer, concurrent pass |
| v4net.device 3.1 fixes it without any config | (M) | Core 12856 | ApolloOS R9.9, no v4net.config: same tests with ApolloExplorerSrv 1.4.2 pass; with 1.4.4 also 4 × 200 short sessions, 20 transfers up to 10 MB (3.6 MB/s up, 1.4 MB/s down) and 6 parallel clients, 0 failures |
| `TCP_MAXSEG` 1400 on the accepted socket makes large replies arrive under AROSTCP | (M) | Core 12856 | ApolloExplorer 1.4.4 on ApolloOS R9.6: shell output, 1 MB transfers and parallel sessions pass |
| `TCP_MAXSEG` has no effect under AmiTCP_NG 4.1.8 | (M) | Core 12856 | ApolloExplorer 1.4.4 on AmigaOS 3.9: replies over 1435 bytes still lost |
| `mtu=1492` in `DEVS:NetInterfaces/V4net` fixes it under AmiTCP_NG | (M) | Core 12856 | AmigaOS 3.9: replies up to 3771 bytes arrive; all ApolloExplorer tests pass; 4 MB downloads at 4.2 MB/s |
| `mtu=1492` in `DEVS:NetInterfaces/V4Net` has no effect under AROSTCP | (M) | Core 12856 | ApolloOS R9.9 with v4net.device 3.0: large replies still lost with the line present |
| `TCP_MAXSEG` can only lower `t_maxseg`; `tcp_output()` caps segments at it | (SRC) | any | AROSTCP `tcp_usrreq.c`, `tcp_output.c` |
| AmiTCP_NG rejects `TCP_MAXSEG` with `EINVAL`; reads `mtu=` per interface | (SRC) | any | AmiTCP_NG `src/netinet/tcp_usrreq.c`, `src/net/ng_ifconfig.c` |
