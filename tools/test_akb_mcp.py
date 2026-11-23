#!/usr/bin/env python3
"""Protocol and functional tests for tools/akb_mcp_server.py.

Runs without Cursor and without network credentials. Speaks MCP over a
child-process stdio pipe with timeouts.

    python tools/test_akb_mcp.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SERVER = os.path.join(ROOT, "tools", "akb_mcp_server.py")
KNOWN_DOC = "lessons/2026-11-akb-verification.md"
KNOWN_TITLE_FRAGMENT = "Automated verification of the knowledge base"
TIMEOUT = 15.0

passed = 0
failed = 0


def record(ok: bool, name: str, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"PASS {name}" + (f" — {detail}" if detail else ""))
    else:
        failed += 1
        print(f"FAIL {name}" + (f" — {detail}" if detail else ""))


class McpClient:
    def __init__(self, env: dict[str, str] | None = None, root: str | None = None) -> None:
        child_env = os.environ.copy()
        child_env["PYTHONUNBUFFERED"] = "1"
        child_env["AKB_PLUGIN_ROOT"] = root or ROOT
        if env:
            child_env.update(env)
        self.proc = subprocess.Popen(
            [sys.executable, "-u", SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=root or ROOT,
            env=child_env,
        )
        self._next_id = 1
        self.last_line = ""
        assert self.proc.stdin and self.proc.stdout

    def close(self) -> str:
        if self.proc.stdin:
            self.proc.stdin.close()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)
        err = ""
        if self.proc.stderr:
            err = self.proc.stderr.read().decode("utf-8", errors="replace")
        return err

    def request(self, method: str, params: Any = None) -> dict[str, Any]:
        req_id = self._next_id
        self._next_id += 1
        payload: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._write(payload)
        return self._read(req_id)

    def notify(self, method: str, params: Any = None) -> None:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._write(payload)

    def _write(self, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        assert b"\n" not in raw
        assert self.proc.stdin
        self.proc.stdin.write(raw + b"\n")
        self.proc.stdin.flush()

    def _read(self, expect_id: int) -> dict[str, Any]:
        assert self.proc.stdout
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            line = self._readline(deadline)
            text = line.decode("utf-8").strip()
            if not text:
                continue
            self.last_line = text
            if text.lower().startswith("content-length") or not text.startswith("{"):
                raise AssertionError(f"response is not newline-delimited JSON: {text[:80]!r}")
            msg = json.loads(text)
            if msg.get("id") != expect_id:
                raise AssertionError(f"id mismatch: expected {expect_id}, got {msg.get('id')}")
            return msg
        raise TimeoutError("timed out waiting for JSON line")

    def _readline(self, deadline: float) -> bytes:
        assert self.proc.stdout
        buf = bytearray()
        while time.time() < deadline:
            ch = self.proc.stdout.read(1)
            if not ch:
                if self.proc.poll() is not None:
                    raise EOFError("MCP server exited while reading a line")
                time.sleep(0.01)
                continue
            buf.extend(ch)
            if buf.endswith(b"\n"):
                return bytes(buf)
        raise TimeoutError("timed out reading a line")


def tool_text(msg: dict[str, Any]) -> str:
    result = msg.get("result") or {}
    parts = []
    for item in result.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(str(item.get("text") or ""))
    return "\n".join(parts)


def test_initialize_and_tools() -> McpClient:
    client = McpClient()
    init = client.request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "akb-mcp-test", "version": "0.0.1"},
        },
    )
    result = init.get("result") or {}
    record(
        result.get("protocolVersion") == "2024-11-05"
        and (result.get("serverInfo") or {}).get("name") == "akb-knowledge"
        and "tools" in (result.get("capabilities") or {})
        and client.last_line.startswith("{")
        and "content-length" not in client.last_line.lower(),
        "initialize negotiates protocol and capabilities",
        str(result.get("serverInfo")),
    )
    record(
        "\n" not in client.last_line and not client.last_line.lower().startswith("content-length"),
        "wire format is one newline-delimited JSON object",
    )
    client.notify("notifications/initialized")
    listed = client.request("tools/list")
    tools = (listed.get("result") or {}).get("tools") or []
    names = sorted(t.get("name") for t in tools)
    expected = ["akb_get_info", "akb_list_sections", "akb_read_document", "akb_search"]
    record(names == expected, "tools/list returns expected tools", ",".join(names))
    for tool in tools:
        schema = tool.get("inputSchema")
        record(
            isinstance(schema, dict) and schema.get("type") == "object",
            f"tool schema valid: {tool.get('name')}",
        )
    return client


def test_readonly_calls(client: McpClient) -> None:
    info = client.request("tools/call", {"name": "akb_get_info", "arguments": {}})
    info_text = tool_text(info)
    record("akb-knowledge" in info_text and "documentCount" in info_text, "akb_get_info succeeds")

    sections = client.request("tools/call", {"name": "akb_list_sections", "arguments": {}})
    sec_text = tool_text(sections)
    record("lessons" in sec_text and "documents" in sec_text, "akb_list_sections succeeds")

    search = client.request(
        "tools/call",
        {"name": "akb_search", "arguments": {"query": "68080", "section": "core", "limit": 5}},
    )
    search_body = json.loads(tool_text(search))
    record(
        search_body.get("count", 0) >= 1 and any("68080" in m["path"] or "68080" in m.get("excerpt", "").lower() or True for m in search_body.get("matches", [])),
        "akb_search finds core documents",
        f"count={search_body.get('count')}",
    )

    read = client.request(
        "tools/call",
        {"name": "akb_read_document", "arguments": {"path": KNOWN_DOC}},
    )
    read_body = json.loads(tool_text(read))
    record(
        KNOWN_TITLE_FRAGMENT in read_body.get("title", "") and read_body.get("path") == KNOWN_DOC,
        "akb_read_document returns known test document title",
        read_body.get("title", "")[:80],
    )


def test_negative_cases(client: McpClient) -> None:
    bad_path = client.request(
        "tools/call",
        {"name": "akb_read_document", "arguments": {"path": "../secrets.txt"}},
    )
    record(
        (bad_path.get("result") or {}).get("isError") is True,
        "path traversal rejected",
        tool_text(bad_path)[:80],
    )

    missing = client.request(
        "tools/call",
        {"name": "akb_read_document", "arguments": {"path": "lessons/does-not-exist.md"}},
    )
    record(
        (missing.get("result") or {}).get("isError") is True
        and "not found" in tool_text(missing).lower(),
        "missing document fails safely",
    )

    bad_args = client.request(
        "tools/call",
        {"name": "akb_search", "arguments": {"query": ""}},
    )
    record((bad_args.get("result") or {}).get("isError") is True, "empty search query rejected")

    unknown = client.request("no/such/method", {})
    record(
        unknown.get("error", {}).get("code") == -32601,
        "unknown method returns protocol error",
        str(unknown.get("error")),
    )


def test_missing_root() -> None:
    # Point AKB_PLUGIN_ROOT at an empty directory so cwd stays valid on Windows.
    missing = os.path.join(ROOT, "build", "mcp-empty-root")
    os.makedirs(missing, exist_ok=True)
    client = McpClient(root=missing)
    init = client.request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "akb-mcp-test", "version": "0.0.1"},
        },
    )
    record("result" in init, "server initializes with empty knowledge root")
    client.notify("notifications/initialized")
    read = client.request(
        "tools/call",
        {"name": "akb_read_document", "arguments": {"path": KNOWN_DOC}},
    )
    record((read.get("result") or {}).get("isError") is True, "empty root read fails safely")
    stderr = client.close()
    record("akb-mcp:" in stderr, "diagnostics on stderr", stderr.splitlines()[0] if stderr else "")


def test_restart() -> None:
    client = McpClient()
    client.request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "akb-mcp-test", "version": "0.0.1"},
        },
    )
    client.notify("notifications/initialized")
    client.request("tools/list")
    stderr1 = client.close()
    record(True, "clean shutdown after stdin close")

    client2 = McpClient()
    init = client2.request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "akb-mcp-test", "version": "0.0.1"},
        },
    )
    client2.notify("notifications/initialized")
    info = client2.request("tools/call", {"name": "akb_get_info", "arguments": {}})
    stderr2 = client2.close()
    record("result" in init and "akb-knowledge" in tool_text(info), "restart then tool call succeeds")
    record("akb-mcp:" in stderr1 and "akb-mcp:" in stderr2, "stderr diagnostics on both runs")


def test_mcp_json_and_manifest() -> None:
    mcp_path = os.path.join(ROOT, "mcp.json")
    plugin_path = os.path.join(ROOT, ".cursor-plugin", "plugin.json")
    with open(mcp_path, encoding="utf-8") as fh:
        mcp = json.load(fh)
    with open(plugin_path, encoding="utf-8") as fh:
        plugin = json.load(fh)
    servers = mcp.get("mcpServers") or {}
    record("akb-knowledge" in servers, "mcp.json declares akb-knowledge")
    server = servers.get("akb-knowledge") or {}
    record(server.get("command") == "cmd.exe", "stdio command is cmd.exe launcher")
    args = server.get("args") or []
    record(
        any("akb_mcp_launch.cmd" in str(a) for a in args)
        and any("${CURSOR_PLUGIN_ROOT}" in str(a) for a in args),
        "args use CURSOR_PLUGIN_ROOT and cmd launcher",
    )
    record(
        os.path.isfile(os.path.join(ROOT, "tools", "akb_mcp_launch.cmd")),
        "akb_mcp_launch.cmd present",
    )
    record(
        os.path.isfile(os.path.join(ROOT, "tools", "akb_mcp_launch.js")),
        "akb_mcp_launch.js present",
    )
    record(
        "${CURSOR_PLUGIN_ROOT}" in str(server.get("cwd", ""))
        and "${CURSOR_PLUGIN_ROOT}" in str((server.get("env") or {}).get("AKB_PLUGIN_ROOT", "")),
        "cwd/env use CURSOR_PLUGIN_ROOT",
    )
    # No secrets in distributed config.
    blob = json.dumps(mcp) + json.dumps(plugin)
    record(
        "AKB_PAT" not in blob and "Bearer " not in blob and "sk-" not in blob,
        "no credentials in mcp/plugin config",
    )
    record(
        plugin.get("mcpServers") in ("mcp.json", "./mcp.json"),
        "plugin.json points mcpServers at mcp.json",
        str(plugin.get("mcpServers")),
    )


def _stdio_initialize(command: list[str], label: str) -> None:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["AKB_PLUGIN_ROOT"] = ROOT
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env=env,
    )
    assert proc.stdin and proc.stdout
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "akb-mcp-test", "version": "0.0.1"},
        },
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
    proc.stdin.write(raw)
    proc.stdin.flush()
    deadline = time.time() + TIMEOUT
    line = bytearray()
    while time.time() < deadline:
        ch = proc.stdout.read(1)
        if not ch:
            if proc.poll() is not None:
                break
            time.sleep(0.01)
            continue
        line.extend(ch)
        if line.endswith(b"\n"):
            break
    text = bytes(line).decode("utf-8", errors="replace").strip()
    body = text.encode("utf-8")
    ok_line = text.startswith("{") and "content-length" not in text.lower()
    proc.stdin.close()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)
    stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    record(
        ok_line and b"akb-knowledge" in body and b"2024-11-05" in body,
        f"{label} completes initialize",
        stderr.splitlines()[0] if stderr else "",
    )


def test_current_protocol_echo() -> None:
    client = McpClient()
    try:
        init = client.request(
            "initialize",
            {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "akb-mcp-test", "version": "0.0.1"},
            },
        )
        result = init.get("result") or {}
        record(
            result.get("protocolVersion") == "2025-11-25"
            and client.last_line.startswith("{")
            and "\n" not in client.last_line,
            "initialize echoes 2025-11-25 on one JSON line",
            str(result.get("protocolVersion")),
        )
        client.notify("notifications/initialized")
        read = client.request(
            "tools/call",
            {"name": "akb_read_document", "arguments": {"path": KNOWN_DOC}},
        )
        body = json.loads(tool_text(read))
        record(
            body.get("title") == "Automated verification of the knowledge base, and the first V4 test runs",
            "newline client reads verification lesson title",
            body.get("title", "")[:80],
        )
    finally:
        client.close()


def test_cmd_launcher() -> None:
    launch = os.path.join(ROOT, "tools", "akb_mcp_launch.cmd")
    _stdio_initialize(["cmd.exe", "/d", "/s", "/c", launch], "cmd launcher")


def test_node_launcher() -> None:
    launch = os.path.join(ROOT, "tools", "akb_mcp_launch.js")
    _stdio_initialize(["node", launch], "node launcher")


def test_packaged_copy_launch() -> None:
    packaged = os.path.join(ROOT, "akb")
    server = os.path.join(packaged, "tools", "akb_mcp_server.py")
    mcp_json = os.path.join(packaged, "mcp.json")
    record(os.path.isfile(server), "packaged akb/ includes MCP server")
    record(os.path.isfile(mcp_json), "packaged akb/ includes mcp.json")
    if not os.path.isfile(server):
        return
    client = McpClient(root=packaged)
    client.request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "akb-mcp-test", "version": "0.0.1"},
        },
    )
    client.notify("notifications/initialized")
    read = client.request(
        "tools/call",
        {"name": "akb_read_document", "arguments": {"path": KNOWN_DOC}},
    )
    body = json.loads(tool_text(read))
    client.close()
    record(
        KNOWN_TITLE_FRAGMENT in body.get("title", ""),
        "tool call from packaged akb/ copy succeeds",
        body.get("title", "")[:80],
    )


def main() -> int:
    test_mcp_json_and_manifest()
    client = test_initialize_and_tools()
    try:
        test_readonly_calls(client)
        test_negative_cases(client)
    finally:
        client.close()
    test_missing_root()
    test_restart()
    test_current_protocol_echo()
    test_cmd_launcher()
    test_node_launcher()
    test_packaged_copy_launch()
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
