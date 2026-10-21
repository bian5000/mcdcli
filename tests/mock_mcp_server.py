"""Local mock of the McDonald's China MCP Server for testing mcdcli.

Endpoints:
  POST /json  - answers every JSON-RPC request with application/json
  POST /sse   - answers with text/event-stream (data: {...} line)
  Any request with "Authorization: Bearer bad" gets a 401.

Also records whether the client sent back the Mcp-Session-Id issued at
initialize time, and exposes it via GET /_state for assertions.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

SESSION_ID = "test-session-123"

TOOLS = [
    {"name": "query-meals", "description": "查询当前可售卖的餐品列表"},
    {"name": "list-nutrition-foods", "description": "餐品营养信息列表"},
    {"name": "query-nearby-stores", "description": "查询附近可用门店"},
    {"name": "query-my-coupons", "description": "查询我的优惠券"},
    {"name": "auto-bind-coupons", "description": "麦麦省一键领券"},
    {"name": "campaign-calendar", "description": "活动日历查询工具"},
    {"name": "query-my-account", "description": "我的积分查询"},
    {"name": "order-list", "description": "查询历史订单"},
]

TOOL_RESULTS = {
    "query-meals": {"categories": [{"categoryName": "主食", "meals": [{"mealCode": "1001", "mealName": "巨无霸"}]}]},
    "list-nutrition-foods": [{"foodName": "麦辣鸡腿堡", "energy": 2014, "protein": 25.5}],
    "query-nearby-stores": {"stores": [{"storeCode": "1234567", "storeName": "中关村餐厅"}]},
    "query-my-coupons": {"coupons": [{"couponName": "脆汁鸡买一送一", "expire": "2026-10-31"}]},
    "auto-bind-coupons": {"claimed": 3, "coupons": ["A", "B", "C"]},
    "campaign-calendar": {"activities": [{"name": "麦乐送满减", "status": "进行中"}]},
    "query-my-account": {"available": 1280, "expiringSoon": 200},
    "order-list": {"orders": [{"orderId": "E123", "amount": 39.5}]},
}

state = {"sessions_seen": [], "last_tool_call": None}


class MockMCP(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # keep test output clean
        pass

    def _reply(self, req_id, result, status=200, extra_headers=None, json_body=True):
        payload = {"jsonrpc": "2.0", "id": req_id, "result": result}
        if json_body:
            body = json.dumps(payload).encode()
            ctype = "application/json"
        else:
            body = f"event: message\ndata: {json.dumps(payload)}\n\n".encode()
            ctype = "text/event-stream"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, json_body):
        if self.headers.get("Authorization") == "Bearer bad":
            self.send_response(401)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(length))
        sid = self.headers.get("Mcp-Session-Id")
        state["sessions_seen"].append(sid)
        method = req.get("method")

        if method == "initialize":
            self._reply(
                req["id"],
                {"protocolVersion": "2025-03-26", "capabilities": {}, "serverInfo": {"name": "mock"}},
                extra_headers={"Mcp-Session-Id": SESSION_ID},
                json_body=json_body,
            )
        elif method == "notifications/initialized":
            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif method == "tools/list":
            self._reply(req["id"], {"tools": TOOLS}, json_body=json_body)
        elif method == "tools/call":
            name = req["params"]["name"]
            state["last_tool_call"] = {"name": name, "arguments": req["params"].get("arguments"), "session_id": sid}
            if name == "boom":
                self._reply(req["id"], {"isError": True, "content": [{"type": "text", "text": "tool exploded"}]}, json_body=json_body)
            elif name == "fail":
                self.send_response(200)
                body = json.dumps({"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32602, "message": "bad params"}}).encode()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                text = json.dumps(TOOL_RESULTS.get(name, {"ok": True}), ensure_ascii=False)
                self._reply(req["id"], {"content": [{"type": "text", "text": text}]}, json_body=json_body)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_POST(self):
        self._handle(json_body=(self.path != "/sse"))

    def do_GET(self):
        if self.path == "/_state":
            body = json.dumps(state).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


def serve(port=8765):
    server = HTTPServer(("127.0.0.1", port), MockMCP)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
