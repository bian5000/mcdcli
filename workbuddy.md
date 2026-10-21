# workbuddy.md — WorkBuddy 开发对话上下文导出

> 本文档由 WorkBuddy 会话导出，记录 mcdcli 项目从创意构思、开发调试到真实环境验证的完整对话上下文，用于麦当劳程序员节创意开发大赛 WorkBuddy 专项奖励核验。

## 项目信息

| 项 | 值 |
|---|---|
| 项目名称 | mcdcli — 麦当劳 MCP 命令行客户端 |
| 开发工具 | **WorkBuddy**（全程使用，含创意构思、代码生成、测试、调试、文档撰写） |
| 项目仓库 | https://github.com/bian5000/mcdcli |
| 开发周期 | 2026-10-20 ~ 2026-10-21（2 天，报名截止前） |
| 参赛方向 | 基于麦当劳中国 MCP Server 的终端命令行 Skill |

## 对话时间线

### 2026-10-20 创意构思阶段

1. **需求输入**：用户提供大赛仓库（M-China/mcd-developer-innovation-challenge），要求分析活动信息。
2. **信息分析**：WorkBuddy 抓取并解析了大赛 README、RANKING.md 排行榜、麦当劳 MCP Server 工具清单，输出活动规则摘要：报名窗口 2026-10-09 ~ 10-25，按 Star 排名，前 100 名获奖。
3. **机会评估**：用户询问「5 天时间还有机会吗？有什么参赛方向？」。WorkBuddy 基于排行榜数据（第 100 名门槛 18 星、头部 705 星）给出分层结论：前 100 名可行、前三不现实；识别出榜单最大特征为「省钱/优惠券类同质化严重」（前 12 名中 6 个）。
4. **方向决策**：WorkBuddy 给出 4 个差异化方向（终端 CLI / 深夜营养决策 / 趣味盲盒 / 活动日历管家），用户确认选择**终端 CLI 方向**（依据：用户自身工具类项目经验复用 + 榜单已验证开发者受众，mcd-terminal 77 星、mcctl 29 星存在超车空间）。

### 2026-10-20 ~ 21 开发阶段

5. **仓库骨架搭建**：WorkBuddy 生成完整项目结构——三个参赛必需文档（README.md、CONTEST_DECLARATION.md 官方原文精确复制、MCP_INTEGRATION.md）+ Python 源码（client.py 协议核心 / commands.py 命令层 / cli.py 入口 / config.py 配置）。
6. **协议实现**：以纯 `requests` 单依赖实现 MCP Streamable HTTP 传输（initialize → notifications/initialized → tools/list → tools/call），覆盖 JSON 与 SSE 双响应解析、Mcp-Session-Id 会话管理、401/429 错误分支。

### 2026-10-21 调试与真实验证阶段

7. **Mock 冒烟测试**：WorkBuddy 编写本地 mock MCP server（tests/mock_mcp_server.py）+ 15 项断言冒烟测试（tests/smoke_test.py），首轮运行 3 个命令全部失败。
8. **Bug 修复（3 个，全部经运行时验证）**：
   - 缺 `__main__.py` 导致 `python -m mcdcli` 无法执行 → 补上
   - `--base-url`/`--token` 仅支持全局位置 → 改为 argparse parents 共享，前后置均可
   - **`notifications/initialized` 的 202 空响应体被强行 `json()` 解析导致 CLI 崩溃** → notify 请求跳过 body 解析
9. **真实 Token 接入与安全处理**：用户提供真实 MCP Token。WorkBuddy 将其存入 `~/.mcdcli/config.json`（项目目录外），三重 grep 确认项目文件、git 提交、打包 zip 内均零泄露，符合 CONTEST_DECLARATION.md 信息安全声明。
10. **真实 server 实测**：连接 `https://mcp.mcd.cn` 实测，纠正 4 处与文档不符的实现：
    - 线上实开 **35 个 Tool**（官方文档写 33，多 query-promotions、query-survey-coupon）
    - `list-nutrition-foods` 不接受任何参数（原 --keyword 被服务端静默忽略）→ 移除参数改为 grep 过滤
    - `query-meals` 必填 storeCode/orderType/beType → 补全 CLI 必填参数
    - `query-nearby-stores` 的 searchType=1 是收藏列表而非搜索 → 默认值改为 2
    - 发现真实响应三种形态（纯 JSON / Markdown / LLM 描述型文本），客户端「JSON 失败则原样透出」策略全部正确处理
11. **回归验证**：修正后重跑冒烟测试 15/15 通过（含测试环境隔离 HOME 防止读到本地 token 的修复）。
12. **交付与推送**：git 初始化提交（commit 0d2f86f）；用户经桌面端下载 zip、解压、GitHub 网页上传完成仓库发布。
13. **报名 Issue 排错**：首个报名 Issue #957 被系统机器人驳回（「报名信息未通过校验」）。WorkBuddy 对比官方模板定位根因：字段间未按「每行一个」格式（项目名称与项目地址挤在一行导致校验正则无法提取），指导用户按标准模板重新提交。
14. **邮箱验证**：指导用户完成 GitHub 注册邮箱验证（Primary + Verified），确保获奖通知可达。

## WorkBuddy 在本项目中的使用方式

- **创意构思**：基于排行榜数据的竞争格局分析、差异化方向推荐
- **代码生成**：MCP 协议客户端、CLI 命令层、mock server、冒烟测试共约 635 行
- **调试排错**：运行时验证驱动（禁止静态检查），3 个协议层 bug 全部经真实执行捕获
- **文档撰写**：README、MCP_INTEGRATION、本导出文档
- **外部集成**：GitHub API 查询仓库/Issue 状态、WebFetch 抓取大赛规则与排行榜

## 技术栈

Python 3.11 · requests（唯一依赖）· argparse · MCP Streamable HTTP (protocol 2025-03-26)
