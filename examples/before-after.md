# 改写示例 / Before-After Examples

每组示例：原文（含标注的违规规则）→ 改写后 → 说明。本文件中的「❌ 原文」故意保留违规，供 linter 验证；「✅ 改写后」为目标态。

## 示例 1：人类表达 —— 需求陈述（A 类，Strict）

❌ 原文：

> 系统需要尽量支持各种主流数据格式，查询响应应当尽可能快，在保证准确性的前提下为用户提供无缝且强大的检索体验。

违规：H-A1（「需要」替代关键词）、H-A7（尽量/各种/主流）、H-A5（无量化验收）、H-A8（无缝、强大）。

✅ 改写后：

> 系统必须支持两种输入格式：UTF-8 编码的 CSV 与 JSON Lines。单查询响应时间必须不超过 3 秒（P95）。检索结果前 20 条的精确率应当不低于 90%。

说明：把「快」与「准确」落实为数字与单位；「主流」「各种」落地为枚举；营销词全部删除。

## 示例 2：人类表达 —— 英文任务指令（A 类，Strict）

❌ 原文：

> "This tool will attempt to synchronize state across the various backends that have been configured, and if a conflict is detected it may resolve it automatically depending on the strategy that has been set, or otherwise it will surface the conflict for manual review."

违规：en-semicolon 无但一句多义、en-passive、en-long-sentence、vague（various）。

✅ 改写后（继承 ASD-STE100 经典改写）：

> "The tool tries to synchronize state across the configured backends. If it finds a conflict, it reads the configured strategy. If the strategy allows automatic resolution, the tool may resolve the conflict without a user. If the tool does not resolve the conflict, it reports the conflict for manual review."

保留原表述：may resolve —— 「may」承载策略未配置时的不确定性，删除会改变语义。

## 示例 3：人类表达 —— 情态红线（A 类）

❌  tempting rewrite（错误的「简化」）：

> 「请求失败了。」

原文为「请求可能失败了」。把「可能」删掉不是简化，是换了断言。R-A1 红线：情态即内容。

✅ 正确处理：

> 「请求可能失败了。检查客户端版本。」

## 示例 4：过程文件 —— 交接单（B 类，Strict）

❌ 原文：

> 完成了重构，测试都过了。剩下的你看着办，注意几个地方容易出错。

违规：H-B1（无文件头）、H-B5（已完成不可验证）、H-B6（待办无完成条件）、H-B4（无风险段）。

✅ 改写后：

```markdown
# HANDOFF: parser 模块重构

- 目标：交接 parser 模块重构的当前状态
- 状态：active
- 负责人：下游 Agent
- 最后更新：2026-10-02
- 上游：上游 Agent

## 已完成

- 将 parser.py 的 tokenize 函数拆分为 tokenize 与 validate 两个函数（commit a1b2c3d）。
- 全部 42 个单元测试通过（pytest，Python 3.11）。

## 待办

- 为 validate 函数补边界用例 — 待指派 — 完成条件：空输入与非法字符两类用例通过。

## 风险

- 假设：上游调用方只通过 parse() 公共接口访问；若有人直接调用内部函数，拆分将导致 AttributeError。
```

## 示例 5：过程文件 —— ADR 备选方案（B 类）

❌ 原文：

> 决策：用 SQLite 存状态。理由：简单。

违规：H-B8（无背景、无备选）、A-B1（零备选方案通常是先决策后补文档）。

✅ 改写后：

```markdown
# ADR-003: 本地状态存储选型

- 状态：decided
- 负责人：Lex
- 最后更新：2026-10-02

## 背景

Agent 需要在会话间持久化任务状态。约束：单用户桌面环境；无运维预算；状态量小于 10 MB。

## 决策

本地状态存储使用 SQLite。

## 理由

单文件零部署；Python 标准库内置 sqlite3，无新增依赖；事务语义满足并发写入需求。

## 备选方案

1. JSON 文件 — 被否原因：无事务，并发写入会损坏状态。
2. PostgreSQL — 被否原因：引入常驻进程与运维成本，超出单用户场景需求。
```
