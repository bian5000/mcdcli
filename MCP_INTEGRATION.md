# MCP_INTEGRATION.md

## 使用的麦当劳 MCP Server

| 项 | 值 |
|---|---|
| 服务名称 | 麦当劳中国 MCP Server（mcd-mcp） |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP（POST + JSON-RPC 2.0，支持 `application/json` 与 `text/event-stream` 两种响应） |
| 认证方式 | 请求头 `Authorization: Bearer <MCP_TOKEN>` |
| 会话管理 | 握手阶段读取响应头 `Mcp-Session-Id`，后续请求携带 |
| 协议版本 | `2025-03-26` |
| 限流 | 600 次/分钟（超限返回 429，客户端已做明确错误提示） |

本仓库 `mcdcli/client.py` 用标准库之外的唯一依赖 `requests` 实现了上述协议的精简子集：
`initialize` → `notifications/initialized` → `tools/list` / `tools/call`，
覆盖 JSON 与 SSE 两种响应体解析、JSON-RPC 错误透传、401/429 状态码识别。

## 实际调用的 Tool 清单

截至 2026-10-21 对线上 server `tools/list` 的实测，共开放 **35 个 Tool**（官方 GitHub 文档列 33 个，线上另有 `query-promotions`、`query-survey-coupon`）。本 CLI 封装了其中 9 个高频只读/领券工具：

| CLI 命令 | MCP Tool | 关键参数（实测 inputSchema） |
|---|---|---|
| `mcdcli tools` | `tools/list` | — |
| `mcdcli call <tool>` | `tools/call` | 任意工具，`--arg k=v` 透传 |
| `mcdcli menu` | `query-meals` | 必填 `storeCode` / `orderType`(1=到店自取, 2=外送) / `beType` |
| `mcdcli nutrition` | `list-nutrition-foods` | **无参数**，返回全量表；过滤请在客户端 grep |
| `mcdcli stores` | `query-nearby-stores` | 必填 `beType` / `searchType`(1=收藏列表, **2=关键词搜索**)，可选 `keyword` / `city` |
| `mcdcli coupons` | `query-my-coupons` | — |
| `mcdcli claim` | `auto-bind-coupons` | — |
| `mcdcli campaign` | `campaign-calendar` | 可选 `specifiedDate` |
| `mcdcli points` | `query-my-account` | — |
| `mcdcli orders` | `order-list` | — |

## 调用流程

以 `mcdcli claim`（麦麦省一键领券）为例：

```
用户执行 mcdcli claim
  └─ MCDClient.call_tool("auto-bind-coupons")
       ├─ ensure_ready()
       │    ├─ POST initialize {protocolVersion, capabilities, clientInfo}
       │    ├─ 记录响应头 Mcp-Session-Id
       │    └─ POST notifications/initialized
       └─ POST tools/call {name: "auto-bind-coupons", arguments: {}}
            └─ 解析 content[].text → JSON → 终端输出
```

Token 解析优先级：`--token` 参数 > 环境变量 `MCD_TOKEN` > `~/.mcdcli/config.json`。
项目不内置任何真实凭证（见 `CONTEST_DECLARATION.md` 信息安全声明）。

## 真实 server 响应形态（实测）

对线上 `https://mcp.mcd.cn` 的实测发现，`tools/call` 返回的 `content[].text` 有三种形态，客户端的「先尝试 JSON 解析、失败原样透出」策略均正确处理：

1. **纯 JSON 字符串**：`query-nearby-stores`、`query-my-coupons` 等（可被 `json.loads` 还原为结构化数据）
2. **Markdown 文本**：`campaign-calendar` 返回带标题/列表的活动日历，`auto-bind-coupons` 返回领券结果说明
3. **LLM 描述型文本**：部分工具（如 `query-my-account`、`query-meals`）返回「API Response Information + 字段说明 + Original Response」的复合文本，原始 JSON 嵌在文末

验证方式：`tests/mock_mcp_server.py` 以标准库实现 MCP 协议 mock（含 JSON/SSE 双模式、session 管理、错误分支），`tests/smoke_test.py` 15 项断言全通过；线上链路另已实测 `tools` / `campaign` / `points` / `nutrition` / `stores` / `menu` 六个命令。

## 业务价值

1. **脚本化接入官方能力**：把需要图形界面的 MCP 能力（点餐、领券、活动日历）变成可组合的 Unix 命令，支持管道、cron 定时任务和 CI 场景。
2. **终端原生的实时数据**：所有输出直接来自 MCP Server，无本地缓存、无硬编码餐品数据，避免信息过期。
3. **开发者友好**：单一依赖、~300 行核心代码，可作为其他语言/框架接入麦当劳 MCP 的参考实现；`mcdcli call` 逃生舱让任意新上线的 Tool 立即可用，无需等待 CLI 更新。
