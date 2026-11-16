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
  os: [apolloos-r10]
  mode: [os-friendly]
  board: [v4-unicorn]
tags: [network, ethernet, v4net, mtu, mss, tcp, arostcp, bsdsocket, stall]
related:
  - os/pitfalls/v4-rom-modules-and-reset.md
sources:
  - "Measured on a V4 UniCorn, Core 12856, ApolloOS R9.6, v4net.device 3.0, 2026-11-16 (ping size sweep, tests/aetest.py of WDrijver/ApolloExplorer)"
  - "ApolloOS source: workbench/network/stacks/AROSTCP/bsdsocket/netinet/tcp_usrreq.c, tcp_output.c"
  - "WDrijver/ApolloExplorer pull request #9"
  - "lessons/2026-11-apolloexplorer.md"
---

## Symptom

A TCP connection from the V4 stalls as soon as the V4 sends more than about
1.4 KB in one go. Small replies keep arriving, and data sent *to* the V4
arrives fine, so the connection looks alive but "unstable". In
ApolloExplorer, every `ash` command with output and every download hung,
while uploads worked.

From any other host on the LAN:

```sh
ping -D -s 1470 <v4-ip>     # 1498-byte IP packet: reply
ping -D -s 1472 <v4-ip>     # 1500-byte IP packet: no reply, ever
```

## Cause

`v4net.device` 3.0 (beta) does not transmit a 1514-byte Ethernet frame
(a 1500-byte IP packet); 1512 bytes and smaller work (M). It still reports
an MTU of 1500, so AROSTCP builds 1500-byte packets: TCP uses an MSS of
1460, and every full-size segment is lost and retransmitted at the same size
forever. Receiving full-size frames works (M).

Below that size the driver also loses about one packet per few thousand in
back-to-back bursts (M), so each TCP connection sees an occasional 1.2 to
1.5 s retransmission timeout.

Not yet known: whether `v4net.device` 2.991 and older behave the same, and
whether the driver behaves the same under AmigaOS 3.x. The fix belongs in
the driver; this pitfall stops applying once a fixed version is released.

## Wrong

```c
/* Server: accept and send.  Every reply over ~1.4 KB never arrives. */
SOCKET client = accept( listenSocket, (struct sockaddr *)&addr, &addrLen );
send( client, reply, replyLength, 0 );
```

## Right

Clamp the segment size on the **connected** socket. AROSTCP only lets
`TCP_MAXSEG` lower the MSS a connection has negotiated (SRC: `tcp_usrreq.c`
accepts a value only when it is `<= tp->t_maxseg`). On a listen socket
`t_maxseg` is still the 512-byte default, so 1400 is refused there with
`EINVAL`. `tcp_output.c` caps every segment at `t_maxseg` (SRC).

```c
/* Server: after accept().  A client: after connect(). */
SOCKET client = accept( listenSocket, (struct sockaddr *)&addr, &addrLen );
int maxSegmentSize = 1400;      /* 1400 + 40 bytes headers + TCP options < 1498 */
setsockopt( client, IPPROTO_TCP, TCP_MAXSEG, &maxSegmentSize, sizeof( maxSegmentSize ) );
send( client, reply, replyLength, 0 );
```

`TCP_MAXSEG` is `0x02` both in the ApolloCrossDev NDK header
(`netinet/tcp.h`) and in AROSTCP.

This only protects your own connections. Other programs, and ICMP, still
send full-size packets.

## Detection

- `ping -D -s 1472 <v4-ip>` from another host gets no reply, while
  `ping -D -s 1470` does.
- Check the driver version: `Version DEVS:Networks/v4net.device`.
- A TCP service on the V4 whose small replies work but whose large ones
  never arrive (the client receives not even the first byte).

## Evidence

| Claim | Source | Core | Method |
|---|---|---|---|
| A 1500-byte IP packet from the V4 never arrives; 1498 bytes does | (M) | Core 12856 | `ping -D -s` binary search from a Mac on the same gigabit LAN, ApolloOS R9.6, v4net.device 3.0 |
| Every payload size 0 to 1470 bytes gets a reply | (M) | Core 12856 | One ping per size, spaced out |
| The V4 receives 1500-byte packets | (M) | Core 12856 | TCP upload with 1460-byte segments, 200 KB in 0.36 s |
| Other hosts on the same LAN send 1500-byte packets fine | (M) | n/a | `ping -D -s 1472` to three other hosts |
| AROSTCP builds 1500-byte packets: the interface sets no MTU, so the driver's value is used | (M) | Core 12856 | `net0 DEV=DEVS:networks/v4net.device UNIT=0 IP=DHCP NETMASK=255.255.255.0 UP` in `SYS:System/Network/AROSTCP/db/interfaces`; replies over ~1.4 KB lost |
| About one loss per 4 MB in back-to-back bursts, costing 1.2 to 1.5 s | (M) | Core 12856 | Per-chunk arrival times of 4 MB downloads, TCP_MAXSEG 1400 |
| `TCP_MAXSEG` 1400 on the accepted socket makes large replies arrive | (M) | Core 12856 | ApolloExplorer 1.4.4: shell output, 1 MB transfers and parallel sessions pass |
| `TCP_MAXSEG` can only lower `t_maxseg`; `tcp_output()` caps segments at it | (SRC) | any | AROSTCP `tcp_usrreq.c`, `tcp_output.c` |
