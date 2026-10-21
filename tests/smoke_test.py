"""End-to-end smoke test: runs the real CLI against the local mock MCP server.

Covers: --help/--version, JSON responses, SSE responses, session-id propagation,
tool-call argument passing, isError handling, JSON-RPC error handling, 401 handling.

Usage: python tests/smoke_test.py
"""
import json
import os
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.mock_mcp_server import serve, SESSION_ID  # noqa: E402

ENV = dict(os.environ, MCD_TOKEN="test-token", HOME="/tmp/mcdcli-test-home")
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS, FAIL = [], []


def run(args, env=None, base=None):
    cmd = [sys.executable, "-m", "mcdcli", *args]
    if base:
        cmd += ["--base-url", base]
    p = subprocess.run(cmd, cwd=PROJECT, capture_output=True, text=True, env=env or ENV)
    return p.returncode, p.stdout, p.stderr


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not cond else ""))


def mock_state():
    with urllib.request.urlopen("http://127.0.0.1:8765/_state") as r:
        return json.loads(r.read())


server = serve(8765)
JSON_URL = "http://127.0.0.1:8765/json"
SSE_URL = "http://127.0.0.1:8765/sse"

print("== 1. offline paths (no server needed) ==")
rc, out, _ = run(["--help"])
check("--help exits 0 and prints usage", rc == 0 and "usage: mcdcli" in out)
rc, out, _ = run(["--version"])
check("--version prints 0.1.0", rc == 0 and "0.1.0" in out)
rc, out, err = run(["tools"], env=dict(ENV, MCD_TOKEN=""), base=JSON_URL)
check("missing token -> clean error, exit 2", rc == 2 and "token" in err)

print("== 2. JSON response mode ==")
rc, out, _ = run(["tools"], base=JSON_URL)
check("tools lists 8 mock tools", rc == 0 and "auto-bind-coupons" in out and "8 tools" in out)

rc, out, _ = run(["claim"], base=JSON_URL)
check("claim -> auto-bind-coupons parsed", rc == 0 and '"claimed": 3' in out)

rc, out, _ = run(["menu", "--store-code", "1234567"], base=JSON_URL)
check("menu -> query-meals parsed", rc == 0 and "巨无霸" in out)

rc, out, _ = run(["nutrition"], base=JSON_URL)
check("nutrition -> full table returned", rc == 0 and "麦辣鸡腿堡" in out)

rc, out, _ = run(["call", "campaign-calendar"], base=JSON_URL)
check("call escape hatch works", rc == 0 and "麦乐送满减" in out)

rc, out, _ = run(["call", "query-my-prizes", "--arg", "pageNo=1", "--arg", "pageSize=5"], base=JSON_URL)
st = mock_state()
check("call --arg JSON literals forwarded", st["last_tool_call"]["arguments"] == {"pageNo": 1, "pageSize": 5})

print("== 3. session management ==")
st = mock_state()
check("Mcp-Session-Id issued by server", st["sessions_seen"][0] is None)
check("Mcp-Session-Id echoed on later calls", st["last_tool_call"]["session_id"] == SESSION_ID)

print("== 4. SSE response mode ==")
rc, out, _ = run(["campaign"], base=SSE_URL)
check("SSE data: line parsed", rc == 0 and "麦乐送满减" in out)

print("== 5. error handling ==")
rc, out, err = run(["tools"], env=dict(os.environ, MCD_TOKEN="bad"), base=JSON_URL)
check("401 -> 'unauthorized' message, exit 2", rc == 2 and "401" in err)

rc, out, err = run(["call", "boom"], base=JSON_URL)
check("isError result -> MCPError, exit 2", rc == 2 and "tool exploded" in err)

rc, out, err = run(["call", "fail"], base=JSON_URL)
check("JSON-RPC error -> code+message, exit 2", rc == 2 and "-32602" in err)

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
