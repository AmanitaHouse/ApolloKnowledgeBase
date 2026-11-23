#!/usr/bin/env python3
"""Stdio MCP server for the ApolloKnowledgeBase Cursor plugin.

Exposes read-only tools over the plugin's shipped knowledge articles.
Protocol messages go to stdout as UTF-8 newline-delimited JSON-RPC.
Each message is one JSON object followed by a newline. Diagnostics go to
stderr only.

No network, no credentials. The knowledge root is the plugin directory
that contains this file (…/tools/akb_mcp_server.py → plugin root), or
AKB_PLUGIN_ROOT when that environment variable is set.
"""
from __future__ import annotations

import json
import os
import re
import sys
import traceback
from typing import Any

# Newest revision this server speaks. Clients that send an older supported
# revision get that revision echoed back.
SUPPORTED_PROTOCOL_VERSIONS = (
    "2025-11-25",
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
)
PROTOCOL_VERSION = SUPPORTED_PROTOCOL_VERSIONS[0]
SERVER_NAME = "akb-knowledge"
SERVER_VERSION = "1.0.1"

# Top-level folders that are searchable knowledge (not skills/tools/ops).
SECTIONS = (
    "conventions",
    "core",
    "examples",
    "guides",
    "hardware",
    "lessons",
    "os",
    "sources",
    "toolchain",
)

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
TITLE_RE = re.compile(r"^title:\s*(.+)$", re.MULTILINE)


def plugin_root() -> str:
    env = os.environ.get("AKB_PLUGIN_ROOT", "").strip()
    if env:
        return os.path.abspath(env)
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, ".."))


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr, flush=True)


def read_message() -> dict[str, Any] | None:
    """Read one newline-delimited JSON-RPC message. None means stdin closed."""
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        try:
            text = line.decode("utf-8-sig").strip()
        except UnicodeDecodeError as exc:
            eprint(f"akb-mcp: invalid UTF-8 line: {exc}")
            continue
        if not text:
            continue
        try:
            msg = json.loads(text)
        except json.JSONDecodeError as exc:
            eprint(f"akb-mcp: invalid JSON line: {exc}")
            continue
        if not isinstance(msg, dict):
            eprint("akb-mcp: ignored non-object JSON line")
            continue
        return msg


def write_message(payload: dict[str, Any]) -> None:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if b"\n" in raw or b"\r" in raw:
        raise ValueError("JSON-RPC message must be a single line")
    sys.stdout.buffer.write(raw + b"\n")
    sys.stdout.buffer.flush()


def ok(req_id: Any, result: Any) -> None:
    write_message({"jsonrpc": "2.0", "id": req_id, "result": result})


def err(req_id: Any, code: int, message: str, data: Any = None) -> None:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    write_message({"jsonrpc": "2.0", "id": req_id, "error": error})


def text_result(text: str, is_error: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"content": [{"type": "text", "text": text}]}
    if is_error:
        out["isError"] = True
    return out


def safe_rel_path(raw: str) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = raw.replace("\\", "/").strip().lstrip("/")
    if path.startswith("../") or "/../" in path or path == ".." or os.path.isabs(raw):
        return None
    parts = path.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return None
    return path


def resolve_under_root(rel: str) -> str | None:
    root = plugin_root()
    full = os.path.abspath(os.path.join(root, *rel.split("/")))
    try:
        common = os.path.commonpath([root, full])
    except ValueError:
        return None
    if common != root:
        return None
    return full


def extract_title(text: str, fallback: str) -> str:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return fallback
    tm = TITLE_RE.search(m.group(1))
    if not tm:
        return fallback
    title = tm.group(1).strip().strip("\"'")
    return title or fallback


def iter_markdown() -> list[str]:
    root = plugin_root()
    found: list[str] = []
    for section in SECTIONS:
        base = os.path.join(root, section)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in {"__pycache__", ".git"})
            for name in sorted(filenames):
                if not name.endswith(".md"):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace("\\", "/")
                found.append(rel)
    return found


def tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "name": "akb_get_info",
            "description": (
                "Return ApolloKnowledgeBase plugin MCP metadata: plugin root, "
                "server version, and whether the knowledge sections are present. "
                "Read-only smoke check; no credentials."
            ),
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "akb_list_sections",
            "description": (
                "List knowledge-base sections (top-level folders) available in "
                "the installed AKB plugin, with markdown document counts."
            ),
            "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "akb_search",
            "description": (
                "Search ApolloKnowledgeBase markdown for a case-insensitive "
                "substring. Returns matching paths, titles, and short excerpts. "
                "Read-only."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Substring to find in path or file body.",
                        "minLength": 1,
                    },
                    "section": {
                        "type": "string",
                        "description": "Optional section name to limit the search (e.g. lessons, core).",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum matches to return (default 10, max 50).",
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
        {
            "name": "akb_read_document",
            "description": (
                "Read one knowledge-base markdown document by plugin-relative "
                "path (for example lessons/2026-11-akb-verification.md). "
                "Read-only; refuses paths outside the plugin root."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path relative to the plugin root.",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "Optional truncate length (default 20000, max 100000).",
                        "minimum": 200,
                        "maximum": 100000,
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    ]


def handle_get_info(_args: dict[str, Any]) -> dict[str, Any]:
    root = plugin_root()
    present = [s for s in SECTIONS if os.path.isdir(os.path.join(root, s))]
    payload = {
        "server": SERVER_NAME,
        "version": SERVER_VERSION,
        "protocolVersion": PROTOCOL_VERSION,
        "pluginRoot": root,
        "sectionsPresent": present,
        "documentCount": len(iter_markdown()),
        "auth": "none",
    }
    return text_result(json.dumps(payload, indent=2))


def handle_list_sections(_args: dict[str, Any]) -> dict[str, Any]:
    root = plugin_root()
    rows = []
    for section in SECTIONS:
        base = os.path.join(root, section)
        if not os.path.isdir(base):
            rows.append({"section": section, "present": False, "documents": 0})
            continue
        count = sum(
            1
            for dirpath, _, filenames in os.walk(base)
            for name in filenames
            if name.endswith(".md")
        )
        rows.append({"section": section, "present": True, "documents": count})
    return text_result(json.dumps({"pluginRoot": root, "sections": rows}, indent=2))


def handle_search(args: dict[str, Any]) -> dict[str, Any]:
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return text_result("Invalid arguments: query must be a non-empty string.", is_error=True)
    section = args.get("section")
    if section is not None:
        if not isinstance(section, str) or section not in SECTIONS:
            return text_result(
                f"Invalid arguments: section must be one of {list(SECTIONS)}.",
                is_error=True,
            )
    limit = args.get("limit", 10)
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 50:
        return text_result("Invalid arguments: limit must be an integer from 1 to 50.", is_error=True)

    needle = query.strip().lower()
    root = plugin_root()
    matches = []
    for rel in iter_markdown():
        if section and not rel.startswith(section + "/"):
            continue
        full = resolve_under_root(rel)
        if not full or not os.path.isfile(full):
            continue
        try:
            with open(full, encoding="utf-8") as fh:
                body = fh.read()
        except OSError as exc:
            eprint(f"akb-mcp: skip {rel}: {exc}")
            continue
        hay = (rel + "\n" + body).lower()
        if needle not in hay:
            continue
        title = extract_title(body, os.path.basename(rel))
        idx = hay.find(needle)
        start = max(0, idx - 60)
        excerpt = body[start : start + 160].replace("\n", " ").strip()
        matches.append({"path": rel, "title": title, "excerpt": excerpt})
        if len(matches) >= limit:
            break
    return text_result(json.dumps({"query": query, "count": len(matches), "matches": matches}, indent=2))


def handle_read(args: dict[str, Any]) -> dict[str, Any]:
    rel = safe_rel_path(args.get("path", ""))
    if not rel:
        return text_result(
            "Invalid arguments: path must be a relative plugin path without '..'.",
            is_error=True,
        )
    max_chars = args.get("max_chars", 20000)
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 200 or max_chars > 100000:
        return text_result(
            "Invalid arguments: max_chars must be an integer from 200 to 100000.",
            is_error=True,
        )
    full = resolve_under_root(rel)
    if not full or not os.path.isfile(full):
        return text_result(f"Document not found: {rel}", is_error=True)
    if not rel.endswith(".md"):
        return text_result("Only markdown (.md) documents can be read.", is_error=True)
    try:
        with open(full, encoding="utf-8") as fh:
            body = fh.read()
    except OSError as exc:
        return text_result(f"Failed to read document: {type(exc).__name__}", is_error=True)
    truncated = False
    if len(body) > max_chars:
        body = body[:max_chars] + "\n\n[truncated]\n"
        truncated = True
    title = extract_title(body, os.path.basename(rel))
    payload = {
        "path": rel,
        "title": title,
        "truncated": truncated,
        "content": body,
    }
    return text_result(json.dumps(payload, indent=2))


HANDLERS = {
    "akb_get_info": handle_get_info,
    "akb_list_sections": handle_list_sections,
    "akb_search": handle_search,
    "akb_read_document": handle_read,
}


def dispatch_tool(name: str, arguments: Any) -> dict[str, Any]:
    if name not in HANDLERS:
        return text_result(f"Unknown tool: {name}", is_error=True)
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return text_result("Invalid arguments: expected an object.", is_error=True)
    try:
        return HANDLERS[name](arguments)
    except Exception as exc:  # noqa: BLE001 — surface as tool error, not crash
        eprint(f"akb-mcp: tool {name} failed: {exc}")
        eprint(traceback.format_exc())
        return text_result(f"Tool failed: {type(exc).__name__}", is_error=True)


def handle_request(msg: dict[str, Any]) -> None:
    method = msg.get("method")
    req_id = msg.get("id")
    params = msg.get("params") or {}
    eprint(f"akb-mcp: recv method={method!r} id={req_id!r}")

    # Notifications have no id.
    if req_id is None:
        if method == "notifications/initialized":
            eprint("akb-mcp: initialized")
            return
        if method == "notifications/cancelled":
            return
        eprint(f"akb-mcp: ignored notification {method!r}")
        return

    if method == "initialize":
        # Echo a version we support. Prefer the client's version when it is
        # one of the revisions this server implements.
        client_version = ""
        if isinstance(params, dict):
            client_version = str(params.get("protocolVersion") or "")
        if client_version in SUPPORTED_PROTOCOL_VERSIONS:
            negotiated = client_version
        else:
            negotiated = PROTOCOL_VERSION
        ok(
            req_id,
            {
                "protocolVersion": negotiated,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "Read-only ApolloKnowledgeBase tools. Prefer akb_search then "
                    "akb_read_document. Paths are relative to the plugin root."
                ),
            },
        )
        eprint(f"akb-mcp: initialize ok negotiated={negotiated}")
        return

    if method == "ping":
        ok(req_id, {})
        return

    if method == "tools/list":
        ok(req_id, {"tools": tool_schemas()})
        return

    if method == "tools/call":
        if not isinstance(params, dict):
            err(req_id, -32602, "Invalid params")
            return
        name = params.get("name")
        if not isinstance(name, str) or not name:
            err(req_id, -32602, "Invalid params: name required")
            return
        ok(req_id, dispatch_tool(name, params.get("arguments")))
        return

    err(req_id, -32601, f"Method not found: {method}")


def main() -> int:
    root = plugin_root()
    if not os.path.isdir(root):
        eprint(f"akb-mcp: plugin root does not exist: {root}")
        return 2
    eprint(f"akb-mcp: listening on stdio; pluginRoot={root}")
    while True:
        msg = read_message()
        if msg is None:
            eprint("akb-mcp: stdin closed; shutting down")
            return 0
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            # Malformed; if it has an id, reject; else skip.
            req_id = msg.get("id") if isinstance(msg, dict) else None
            if req_id is not None:
                err(req_id, -32600, "Invalid Request")
            continue
        try:
            handle_request(msg)
        except Exception as exc:  # noqa: BLE001
            eprint(f"akb-mcp: unhandled: {exc}")
            eprint(traceback.format_exc())
            req_id = msg.get("id")
            if req_id is not None:
                err(req_id, -32603, "Internal error")


if __name__ == "__main__":
    sys.exit(main())
