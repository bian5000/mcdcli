"""Sub-command implementations for mcdcli.

Each command maps to one or more McDonald's China MCP tools; see MCP_INTEGRATION.md
for the full tool inventory and call flows.
"""
from __future__ import annotations

import argparse
import json

from .client import MCDClient, MCPError
from .config import resolve_token, save_token


def _print(data) -> None:
    if isinstance(data, str):
        print(data)
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


def _client(args) -> MCDClient:
    token = resolve_token(getattr(args, "token", None))
    if not token:
        raise MCPError("no MCP token found; run `mcdcli config set-token <TOKEN>` first")
    return MCDClient(token=token, base_url=getattr(args, "base_url", "https://mcp.mcd.cn"))


def _parse_kv(pairs) -> dict:
    """Parse repeated --arg key=value options; values may be JSON literals."""
    out = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise MCPError(f"bad --arg {pair!r}; expected key=value (JSON values allowed)")
        key, raw = pair.split("=", 1)
        try:
            out[key] = json.loads(raw)
        except ValueError:
            out[key] = raw
    return out


# --------------------------------------------------------------- commands


def cmd_config(args) -> int:
    if args.action == "set-token":
        save_token(args.value)
        print(f"token saved to ~/.mcdcli/config.json")
        return 0
    if args.action == "show-token":
        token = resolve_token(getattr(args, "token", None))
        print("(no token configured)" if not token else f"token ends with ...{token[-4:]}")
        return 0
    return 1


def cmd_tools(args) -> int:
    tools = _client(args).list_tools()
    for t in tools:
        desc = (t.get("description") or "").splitlines()[0]
        print(f"{t.get('name'):<28} {desc}")
    print(f"\n{len(tools)} tools available")
    return 0


def cmd_call(args) -> int:
    result = _client(args).call_tool(args.tool, _parse_kv(args.arg))
    _print(result)
    return 0


def cmd_menu(args) -> int:
    # query-meals requires storeCode + orderType + beType.
    arguments = {
        "storeCode": args.store_code,
        "orderType": args.order_type,
        "beType": args.be_type,
    }
    _print(_client(args).call_tool("query-meals", arguments))
    return 0


def cmd_nutrition(args) -> int:
    # list-nutrition-foods takes no arguments; it returns the full nutrition
    # table. Pipe through grep to narrow down.
    _print(_client(args).call_tool("list-nutrition-foods", {}))
    return 0


def cmd_stores(args) -> int:
    # query-nearby-stores requires beType + searchType; keyword/city narrow it down.
    arguments = {
        "beType": args.be_type,
        "searchType": args.search_type,
    }
    if args.keyword:
        arguments["keyword"] = args.keyword
    if args.city:
        arguments["city"] = args.city
    _print(_client(args).call_tool("query-nearby-stores", arguments))
    return 0


def cmd_coupons(args) -> int:
    _print(_client(args).call_tool("query-my-coupons", {}))
    return 0


def cmd_claim(args) -> int:
    _print(_client(args).call_tool("auto-bind-coupons", {}))
    return 0


def cmd_campaign(args) -> int:
    _print(_client(args).call_tool("campaign-calendar", {}))
    return 0


def cmd_points(args) -> int:
    _print(_client(args).call_tool("query-my-account", {}))
    return 0


def cmd_orders(args) -> int:
    arguments = {}
    if args.limit:
        arguments["pageSize"] = args.limit
    _print(_client(args).call_tool("order-list", arguments))
    return 0


# --------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcdcli",
        description="McDonald's China MCP command-line client (https://mcp.mcd.cn)",
    )
    parser.add_argument("--version", action="store_true", help="print version and exit")

    # Shared connection options: accepted both before and after the sub-command.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--token", help="MCP token (overrides MCD_TOKEN env and saved config)")
    common.add_argument("--base-url", default="https://mcp.mcd.cn", help="MCP server base URL")

    sub = parser.add_subparsers(dest="command")

    def add(name, **kw):
        kw.setdefault("parents", [])
        kw["parents"] = [*kw["parents"], common]
        return sub.add_parser(name, **kw)

    p = add("config", help="manage local token config")
    p.add_argument("action", choices=["set-token", "show-token"])
    p.add_argument("value", nargs="?", help="token value for set-token")
    p.set_defaults(func=cmd_config)

    p = add("tools", help="list all MCP tools exposed by the server")
    p.set_defaults(func=cmd_tools)

    p = add("call", help="call any MCP tool directly (escape hatch)")
    p.add_argument("tool", help="tool name, e.g. query-meals")
    p.add_argument("--arg", action="append", help="tool argument as key=value (repeatable, JSON values allowed)")
    p.set_defaults(func=cmd_call)

    p = add("menu", help="query sellable meals at a store (query-meals)")
    p.add_argument("--store-code", required=True, help="store code, e.g. from `mcdcli stores`")
    p.add_argument("--order-type", type=int, choices=[1, 2], default=1, help="1=pickup in store, 2=delivery")
    p.add_argument("--be-type", type=int, default=1, help="meal period: 1=all-day, others per server docs")
    p.set_defaults(func=cmd_menu)

    p = add("nutrition", help="full nutrition table for McDonald's items (list-nutrition-foods)")
    p.set_defaults(func=cmd_nutrition)

    p = add("stores", help="find nearby McDonald's restaurants (query-nearby-stores)")
    p.add_argument("--keyword", help="location keyword, e.g. 中关村")
    p.add_argument("--city", help="city name")
    p.add_argument("--be-type", type=int, default=1, help="meal period: 1=all-day, others per server docs")
    p.add_argument("--search-type", type=int, default=2, help="1=favorite restaurants, 2=search by keyword/city (default)")
    p.set_defaults(func=cmd_stores)

    p = add("coupons", help="list my available coupons (query-my-coupons)")
    p.set_defaults(func=cmd_coupons)

    p = add("claim", help="one-click claim all MaiMaiSheng coupons (auto-bind-coupons)")
    p.set_defaults(func=cmd_claim)

    p = add("campaign", help="this month's marketing campaign calendar (campaign-calendar)")
    p.set_defaults(func=cmd_campaign)

    p = add("points", help="my points balance (query-my-account)")
    p.set_defaults(func=cmd_points)

    p = add("orders", help="recent order history (order-list)")
    p.add_argument("--limit", type=int, help="page size")
    p.set_defaults(func=cmd_orders)

    return parser
