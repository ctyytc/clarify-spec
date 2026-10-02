# 协议对齐映射 / Protocol Mapping

本文件把 C 类规则逐字段映射到 A2A 协议与 MCP，标明三类判定：

- **原生**：协议已提供该字段或等价语义。直接用协议字段，不另造。
- **部分**：协议覆盖部分语义，剩余以增强字段补充。
- **增强**：协议无此概念。放入协议预留扩展点（A2A `metadata` / MCP `_meta`），建议加 `clarify.` 前缀避免冲突。

## 一、定位

协议管「能送达」，clarify-spec 管「送达后不被误读」。两者是叠加关系，不是替代关系：

- A2A 与 MCP 的 JSON Schema 层保证结构合法（syntax）。
- C 类规则保证语义唯一（semantics）：意图、置信度、错误的可恢复性。
- 适配器职责：发送前把 C 类字段映射或注入协议消息；接收后提取增强字段并校验。

msg-lint 自 v0.3.0 起提供 `--profile` 把映射表固化为可执行检查（见第四节）。

## 二、总表

| C 类规则 | clarify-spec 字段 | A2A 对应 | MCP 对应 | 判定 |
|---|---|---|---|---|
| C-1 信封 | `message_id` | `Message.messageId` | JSON-RPC `id` | 原生 |
| C-1 信封 | `sender` | `Message.role`（仅 user/agent） | 连接方向 | 部分 |
| C-1 信封 | `recipient` | 传输层寻址，信封内无 | 连接端点 | 增强 |
| C-1 信封 | `timestamp` | 仅 `TaskStatus.timestamp` 有 | 无原生 | 部分 |
| C-1 信封 | `correlation_id` | `contextId` 加 `taskId` | JSON-RPC `id` | 部分 |
| C-2 意图 | `intent` | 无原生字段 | `method` 封闭方法集 | MCP 原生 / A2A 增强 |
| C-3 一消息一意图 | —（语义规则） | 一 Message 多 parts | 单 method 单调用 | 见分节 |
| C-4 实体锚定 | 不可变标识符 | `referenceTaskIds` / `artifactId` | `toolUseId` / `id` | 原生 |
| C-5 情态字段化 | `confidence` | 无原生 | 无原生 | 增强 |
| C-6 错误 | `error_code` | 无原生（failed 仅带消息） | JSON-RPC `error.code` | 部分 |
| C-6 错误 | `retryable` | 无原生 | `isError` 近似 | 增强 |
| C-6 错误 | `recovery_hint` | 无原生 | `data` 字段部分承载 | 增强 |
| C-7 交付语义 | `ack_required` | 无原生（REST 隐式） | 请求-响应即 ack | MCP 原生 / A2A 增强 |
| C-7 交付语义 | `timeout_seconds` | 无原生 | 无原生 | 增强 |
| C-8 工具契约 | 参数声明 | `AgentCard` 能力描述部分 | `inputSchema` / `outputSchema` | MCP 原生 / A2A 部分 |
| C-9 上下文自足 | —（语义规则） | `contextId` 机制部分依赖服务端 | 协议明确无状态、自足 | MCP 原生 / A2A 部分 |
| C-10 时间绝对化 | 绝对 UTC | `TaskStatus.timestamp` 为 ISO 8601 | 无强制 | A2A 原生 / MCP 增强 |
| C-11 大负载外置 | `artifact_ref` | `Artifact`（artifactId 加 parts） | `resource_link` 内容块 | 原生 |
| C-12 版本协商 | `schema_version` | 规范级版本加能力协商 | `protocolVersion` 初始化协商 | 部分 |

## 三、分协议落地

### 3.1 A2A

信封映射：

| C 类字段 | A2A 字段 | 说明 |
|---|---|---|
| `message_id` | `Message.messageId` | 直接对应，UUID |
| `sender` | `Message.role` | 仅 ROLE_USER / ROLE_AGENT 两值，粒度粗 |
| `correlation_id` | `contextId`（会话组）加 `taskId`（单任务） | contextId 是分组语义，非因果链；任务级追踪用 taskId |
| `timestamp` | 信封内无 | 只有 `TaskStatus.timestamp`；时间戳需放 `metadata` |
| `intent` | 无原生 | role 与任务状态机仅部分承载意图 |

A2A 的两个原生强项直接满足 C 类要求：

- 实体锚定：`referenceTaskIds`、`artifactId`、`taskId` 提供不可变标识符（C-4）。
- 大负载外置：`Artifact` 对象即「消息传引用」的原生实现（C-11）。

增强字段放 `metadata` 示例：

```json
"metadata": {
  "clarify.intent": "delegate",
  "clarify.timestamp": "2026-10-02T08:00:00Z",
  "clarify.confidence": "inferred",
  "clarify.error_code": "UPSTREAM_TIMEOUT",
  "clarify.retryable": true
}
```

关键 gap：A2A 任务失败时只有 `state: failed` 与人读 `status.message`。因此 failed 任务的 message 必须受 A 类规则约束。error_code 与 retryable 必须显式放入 metadata。这正是 msg-lint 在 a2a profile 下检查增强字段的原因。

### 3.2 MCP

MCP 与 C 类的同构度高于 A2A，体现在三处：

1. **意图枚举是原生的**：MCP 的 `method` 本身就是封闭方法集（`tools/call`、`resources/read`、`prompts/get`……），这是 C-2 思想的协议级实现。映射建议：`tools/call` → delegate，`resources/read` 与 `prompts/get` → query，`elicitation/*` → clarify，`notifications/*` → report。
2. **双层错误与 C-6 同构**：协议区分协议级错误（JSON-RPC `error.code`，如 -32602 未知工具）与执行级错误（结果中 `isError: true`，供模型自我纠正重试）。对照表：

| C-6 字段 | 协议级错误载体 | 执行级错误载体 |
|---|---|---|
| `error_code` | `error.code` | 增强：`_meta.clarify.error_code` |
| `message` | `error.message` | `content[0].text`（受 A 类约束） |
| `retryable` | 增强（code 隐含） | 增强：`_meta.clarify.retryable` |
| `recovery_hint` | `error.data`（部分） | 增强：`_meta.clarify.recovery_hint` |

3. **上下文自足是原生原则**：MCP 规范明确「无状态、自足请求」。原文表述为 stateless, self-contained requests。与 C-9 完全一致。

增强字段放 `_meta` 示例：

```json
{
  "isError": true,
  "_meta": {
    "clarify.error_code": "UNSUPPORTED_ENCODING",
    "clarify.retryable": false,
    "clarify.recovery_hint": "用 iconv 转码后重试该文件。"
  }
}
```

MCP 的两个 gap：

- 信封内无时间戳：C-10 依赖 `params._meta.clarify.timestamp` 增强。
- `isError` 是布尔，无语义分级：retryable 需增强字段。

## 四、可执行映射：msg-lint --profile

msg-lint 自 v0.3.0 起提供协议适配模式，把上表固化为运行时检查：

```bash
python3 scripts/msg-lint.py --profile independent msg.json   # 默认：中立信封
python3 scripts/msg-lint.py --profile a2a msg.json           # A2A Message/Task
python3 scripts/msg-lint.py --profile mcp-request msg.json   # MCP JSON-RPC 请求
python3 scripts/msg-lint.py --profile mcp-result msg.json    # MCP JSON-RPC 响应
```

各 profile 的规范化规则：

| profile | message_id | sender | timestamp | correlation_id | intent |
|---|---|---|---|---|---|
| independent | 原样 | 原样 | 原样 | 原样 | 原样 |
| a2a | `messageId` | `role` | `metadata.clarify.timestamp` | `contextId` 或 `taskId` | `metadata.clarify.intent` |
| mcp-request | `id` | 固定 client | `params._meta.clarify.timestamp` | `id` | method 映射表 |
| mcp-result | `id` | 跳过 | 跳过 | `id` | respond |

跳过的字段不参与该 profile 的缺失检查。规范化之后，C-2 / C-5 / C-6 / C-10 与建议性检查照常执行。示例见 `tests/fixtures/a2a-message.json` 与 CI 的 messages job。

**边界**：profile 只做字段映射，不做协议完整性校验。A2A 的 contextId 与 taskId 一致性规则属于协议层：不匹配必须拒绝。MCP 的能力协商同理。两者由协议栈执行，不在 msg-lint 范围内。

## 五、参考

- A2A Protocol Specification. https://a2a-protocol.org/latest/specification/
- A2A, Life of a Task. https://a2a-protocol.org/latest/topics/life-of-a-task/
- MCP Schema Reference（2025-11-25 / 2026-07-28）. https://modelcontextprotocol.io/specification/2025-11-25/schema
- MCP Tools（双层错误机制）. https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- MCP Specification（无状态自足原则、协议版本协商）. https://modelcontextprotocol.io/specification/2026-07-28
