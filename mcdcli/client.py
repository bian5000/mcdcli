"""MCP Streamable HTTP client for McDonald's China MCP Server (https://mcp.mcd.cn).

Implements just enough of the Model Context Protocol (revision 2025-03-26)
for a command-line client: initialize -> notifications/initialized -> tools/list -> tools/call.

The server may answer either with application/json or with a text/event-stream
body; both are handled here.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import requests

DEFAULT_BASE_URL = "https://mcp.mcd.cn"
PROTOCOL_VERSION = "2025-03-26"
CLIENT_INFO = {"name": "mcdcli", "version": "0.1.0"}


class MCPError(RuntimeError):
    """Raised when the MCP server returns a JSON-RPC error or an unusable response."""


def _extract_text(result: dict) -> Any:
    """Unwrap an MCP tool result into its text payload, parsed as JSON when possible."""
    content = result.get("content")
    if isinstance(content, list):
        texts = [
            c.get("text", "")
            for c in content
            if isinstance(c, dict) and c.get("type") == "text"
        ]
        joined = "\n".join(t for t in texts if t)
        try:
            return json.loads(joined)
        except (ValueError, TypeError):
            return joined
    return result


class MCDClient:
    """Minimal synchronous MCP client over Streamable HTTP."""

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: int = 30,
    ) -> None:
        self.token = token or os.environ.get("MCD_TOKEN")
        if not self.token:
            raise MCPError(
                "missing MCP token: pass --token, set MCD_TOKEN, or run `mcdcli config set-token`"
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session_id: Optional[str] = None
        self._req_id = 0
        self._ready = False

    # ------------------------------------------------------------------ RPC

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _post(self, payload: dict, expect_body: bool = True) -> dict:
        resp = self.session.post(
            self.base_url,
            headers=self._headers(),
            data=json.dumps(payload),
            timeout=self.timeout,
            stream=True,
        )
        if resp.status_code == 401:
            raise MCPError("401 unauthorized: MCP token invalid or expired")
        if resp.status_code == 429:
            raise MCPError("429 rate limited (600 req/min); back off and retry")
        if resp.status_code >= 400:
            raise MCPError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self.session_id = sid
        if not expect_body:
            # notifications get a bare 202 with an empty body; nothing to parse.
            return {}
        return self._parse_body(resp)

    @staticmethod
    def _parse_body(resp: requests.Response) -> dict:
        ctype = resp.headers.get("Content-Type", "")
        if "text/event-stream" in ctype:
            for raw in resp.iter_lines(decode_unicode=True):
                if not raw:
                    continue
                line = raw.strip()
                if line.startswith("data:"):
                    data = line[len("data:"):].strip()
                    if data and data != "[DONE]":
                        return json.loads(data)
            raise MCPError("empty SSE response stream")
        body = resp.json()
        if isinstance(body, dict):
            return body
        raise MCPError(f"unexpected response body type: {type(body).__name__}")

    def _rpc(self, method: str, params: Optional[dict] = None, notify: bool = False) -> Optional[dict]:
        payload: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not notify:
            payload["id"] = self._next_id()
        resp = self._post(payload, expect_body=not notify)
        if notify:
            return None
        if resp.get("error"):
            err = resp["error"]
            raise MCPError(f"JSON-RPC error {err.get('code')}: {err.get('message')}")
        return resp.get("result")

    # ------------------------------------------------------------ lifecycle

    def initialize(self) -> dict:
        result = self._rpc(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            },
        )
        self._rpc("notifications/initialized", notify=True)
        self._ready = True
        return result or {}

    def ensure_ready(self) -> None:
        if not self._ready:
            self.initialize()

    # -------------------------------------------------------------- tools

    def list_tools(self) -> list:
        self.ensure_ready()
        result = self._rpc("tools/list", {}) or {}
        return result.get("tools", [])

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> Any:
        self.ensure_ready()
        result = self._rpc("tools/call", {"name": name, "arguments": arguments or {}}) or {}
        if result.get("isError"):
            raise MCPError(_extract_text(result))
        return _extract_text(result)
