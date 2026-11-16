---
title: v4net.device 3.0-beta loses full-size Ethernet frames
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

`v4net.device` 3.0 (beta) does not transmit a 1514-byte Ethernet frame
(a 1500-byte IP packet); 1512 bytes and smaller work (M). It still reports
an MTU of 1500, so the TCP/IP stack builds 1500-byte packets: TCP uses an
MSS of 1460, and every full-size segment is lost and retransmitted at the
same size forever. Receiving full-size frames works (M). The same happens
under ApolloOS (AROSTCP) and AmigaOS 3.9 (AmiTCP_NG), so it is the driver,
not the OS or the stack.

Not yet known: whether `v4net.device` 2.991 and older behave the same, and
AmigaOS 3.2. The fix belongs in the driver; this pitfall stops applying once
a fixed version is released.

## Wrong

```c
/* Server: accept and send.  Every reply over ~1.4 KB never arrives. */
SOCKET client = accept( listenSocket, (struct sockaddr *)&addr, &addrLen );
send( client, reply, replyLength, 0 );
```

## Right

Keep packets below 1500 bytes. How depends on the TCP/IP stack.

**Every program at once, by configuration (preferred where supported).**
AmiTCP_NG reads `mtu=` from the interface file (SRC: `src/net/ng_ifconfig.c`;
it is clamped to the device MTU). Add a line to `DEVS:NetInterfaces/V4net`
and restart the network (power-cycle the V4):

```text
mtu=1492
```

The stack then sends at most 1492-byte packets and uses an MSS of 1452 (M).

**One program, in code: `TCP_MAXSEG` on the connected socket.** AROSTCP
(ApolloOS) only lets `TCP_MAXSEG` lower the MSS a connection has negotiated
(SRC: `tcp_usrreq.c` accepts a value only when it is `<= tp->t_maxseg`). On a
listen socket `t_maxseg` is still the 512-byte default, so 1400 is refused
there with `EINVAL`. `tcp_output.c` caps every segment at `t_maxseg` (SRC).
AmiTCP_NG 4.1.8 does not implement `TCP_MAXSEG` at all: setting it returns
`EINVAL` ("not yet", SRC: `src/netinet/tcp_usrreq.c`), so check the result
and fall back to the configuration above.

```c
/* Server: after accept().  A client: after connect(). */
SOCKET client = accept( listenSocket, (struct sockaddr *)&addr, &addrLen );
int maxSegmentSize = 1400;      /* 1400 + 40 bytes headers + TCP options < 1498 */
if( setsockopt( client, IPPROTO_TCP, TCP_MAXSEG, &maxSegmentSize, sizeof( maxSegmentSize ) ) < 0 )
{
    /* Not supported by this stack (AmiTCP_NG): large sends will stall
       unless the interface MTU is lowered. */
}
send( client, reply, replyLength, 0 );
```

`TCP_MAXSEG` is `0x02` in the ApolloCrossDev NDK header (`netinet/tcp.h`),
AROSTCP and AmiTCP_NG.

## Detection

- `ping -D -s 1472 <v4-ip>` from another host gets no reply, while
  `ping -D -s 1470` does. With `mtu=1492` set this test still fails (the
  V4 must then fragment its reply); test with TCP instead.
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
| `TCP_MAXSEG` 1400 on the accepted socket makes large replies arrive under AROSTCP | (M) | Core 12856 | ApolloExplorer 1.4.4 on ApolloOS R9.6: shell output, 1 MB transfers and parallel sessions pass |
| `TCP_MAXSEG` has no effect under AmiTCP_NG 4.1.8 | (M) | Core 12856 | ApolloExplorer 1.4.4 on AmigaOS 3.9: replies over 1435 bytes still lost |
| `mtu=1492` in `DEVS:NetInterfaces/V4net` fixes it under AmiTCP_NG | (M) | Core 12856 | AmigaOS 3.9: replies up to 3771 bytes arrive; all ApolloExplorer tests pass; 4 MB downloads at 4.2 MB/s |
| `TCP_MAXSEG` can only lower `t_maxseg`; `tcp_output()` caps segments at it | (SRC) | any | AROSTCP `tcp_usrreq.c`, `tcp_output.c` |
| AmiTCP_NG rejects `TCP_MAXSEG` with `EINVAL`; reads `mtu=` per interface | (SRC) | any | AmiTCP_NG `src/netinet/tcp_usrreq.c`, `src/net/ng_ifconfig.c` |
