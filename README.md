# mcdcli 🍔

> 麦当劳中国 MCP 的命令行客户端 —— 在终端里查菜单、查营养、领麦麦省券、看活动日历、查积分和历史订单。

基于麦当劳中国官方 MCP Server（`https://mcp.mcd.cn`）当前开放的 **35 个 Tool** 构建。**零硬编码数据**，所有餐品、价格、活动、优惠券均实时从官方接口获取；**单一依赖**（`requests`），核心客户端约 300 行。

## 为什么做这个

MCP 客户端大多长在图形界面里——Chat 窗口、IDE 侧边栏。但开发者的世界是终端：
`cron` 每天早上 8 点帮你领走当天所有麦麦省券；周五下午一行命令看看这周营销活动有什么值得薅；
健身前查一下巨无霸的热量再决定吃不吃。`mcdcli` 把官方 MCP 能力变成可组合的 Unix 命令，
支持管道、定时任务和脚本编排。

## 安装

```bash
git clone https://github.com/<you>/mcdcli.git
cd mcdcli
pip install -r requirements.txt
pip install -e .   # 可选，提供 mcdcli 命令；不装也可以用 python -m mcdcli
```

## 快速开始

```bash
# 1. 配置 MCP Token（在 https://open.mcd.cn/mcp 用手机号验证免费申请）
export MCD_TOKEN="your-token"                    # 环境变量方式
# 或：mcdcli config set-token your-token        # 持久化到 ~/.mcdcli/config.json

# 2. 看看服务端开放了哪些工具
mcdcli tools

# 3. 常用命令
mcdcli menu --store-code 1950640               # 查门店在售餐品（先 mcdcli stores 拿门店编码）
mcdcli nutrition                               # 全量营养成分表（服务端不过滤，本地 grep：| grep 麦辣）
mcdcli stores --keyword 中关村 --city 北京       # 按城市+关键词搜附近门店
mcdcli claim                                   # 一键领取全部麦麦省券
mcdcli coupons                                # 我的可用优惠券
mcdcli campaign                               # 当月营销活动日历
mcdcli points                                 # 我的积分
mcdcli orders --limit 10                      # 最近 10 笔订单

# 4. 逃生舱：任何已上线的 MCP 工具都能直接调用，无需等 CLI 更新
mcdcli call campaign-calendar
mcdcli call query-my-prizes --arg pageNo=1 --arg pageSize=5
```

典型输出（`mcdcli nutrition | grep 麦辣鸡腿堡`）：

```
  麦辣鸡腿汉堡,null,2029,485,24,24,42,1208,154
```

字段依次为：餐品名、备注、能量 kJ、能量 kcal、蛋白质 g、脂肪 g、碳水 g、钠 mg、钙 mg。

## 目标用户

- **终端原教旨主义者**：能用一行命令解决的事绝不打开网页
- **脚本玩家**：想用 cron / CI / shell 管道编排麦当劳能力的开发者
- **接入参考者**：需要为其他语言或框架实现麦当劳 MCP Streamable HTTP 接入的工程师（`client.py` 约 300 行，含 JSON/SSE 双响应解析、会话管理、错误处理）

## 项目结构

```
mcdcli/
├── mcdcli/
│   ├── client.py     # MCP Streamable HTTP 客户端（协议核心）
│   ├── commands.py   # 子命令实现，每个命令对应 1 个 MCP Tool
│   ├── cli.py        # argparse 入口
│   └── config.py     # Token 解析：flag > 环境变量 > 配置文件
├── tests/            # mock MCP server + 15 项冒烟测试（python tests/smoke_test.py）
├── MCP_INTEGRATION.md   # MCP Server / Tool 清单 / 调用流程 / 业务价值
├── CONTEST_DECLARATION.md
├── requirements.txt
└── pyproject.toml
```

## 开发

```bash
python -m mcdcli --help
python -m mcdcli tools --base-url http://127.0.0.1:8765   # 指向自建 mock server 调试
```

协议实现参考：[Model Context Protocol - Streamable HTTP 传输](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports)，
工具能力参考：[麦当劳 MCP Server GitHub](https://github.com/M-China/mcd-mcp-server)。

## 声明

本项目为麦当劳程序员节创意开发大赛参赛作品，非麦当劳官方产品，输出仅供参考。
使用即表示同意麦当劳中国《使用条款》及《麦当劳 MCP 服务规则》。请勿泄露你的 MCP Token。
