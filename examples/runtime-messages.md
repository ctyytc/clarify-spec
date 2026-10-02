# 运行时消息示例 / Runtime Message Examples

规范对象 C 的改写示例：A2A 委托消息、错误事件、工具返回。JSON 块中的「❌ 原文」故意不合规，供 msg-lint 验证；「✅ 改写后」为目标态。

验证方式：

```bash
python3 scripts/msg-lint.py --selftest   # 计数断言
# 对单条消息人工验证：把 ✅ 版本写入 msg.json 后运行
python3 scripts/msg-lint.py msg.json     # 期望 0 hard
```

## 示例 1：A2A 委托消息

❌ 原文：

```json
{
  "from": "planner",
  "text": "帮我把 parser 那块搞一下，尽快，可能有点复杂，做完告诉我",
  "task": "parser"
}
```

违规：无信封（C-1）、意图自由文本（C-2）、相对时间「尽快」（C-10）、推测词未字段化（C-5）、实体未锚定（C-4）。

✅ 改写后：

```json
{
  "message_id": "m-9f3a",
  "sender": "planner",
  "recipient": "coder",
  "timestamp": "2026-10-02T08:00:00Z",
  "correlation_id": "c-77",
  "intent": "delegate",
  "schema_version": "1.0.0",
  "ack_required": "response",
  "timeout_seconds": 1800,
  "confidence": "inferred",
  "assumption": "parser 模块指 src/parser.py（commit a1b2c3d）中的实现",
  "task_ref": "TASK-014",
  "message": "重构 parser 模块的 tokenize 函数。完成条件：42 个单元测试全部通过。",
  "due": "2026-10-02T09:00:00Z"
}
```

说明：每个违规对应一个修复。信封六字段齐全，意图入枚举。「尽快」落实为绝对 due。「可能有点复杂」落实为 confidence 加 assumption。「parser 那块」落实为 task_ref 加假设锚定。

## 示例 2：错误事件

❌ 原文：

```json
{
  "error": "调用外部翻译服务的时候出错了，可能是网络问题，你稍后再试吧"
}
```

违规：错误只在自然语言里（C-6）、推测词未字段化（C-5）、相对时间（C-10）、无信封（C-1）。

✅ 改写后：

```json
{
  "message_id": "m-9f3b",
  "sender": "translator-agent",
  "recipient": "planner",
  "timestamp": "2026-10-02T08:05:12Z",
  "correlation_id": "c-77",
  "intent": "report",
  "schema_version": "1.0.0",
  "ack_required": "ack",
  "confidence": "inferred",
  "error": {
    "error_code": "UPSTREAM_TIMEOUT",
    "message": "翻译服务调用超时。",
    "retryable": true,
    "recovery_hint": "等待 30 秒后重试；重试 3 次仍失败则降级为原文输出并标记待人工处理。"
  }
}
```

说明：error_code 是稳定枚举，下游可机读分支。retryable 让下游无需解析文案即可决定重试。recovery_hint 是指令句。

## 示例 3：工具返回 —— 部分失败显式化

❌ 原文：

```json
{
  "status": "ok",
  "results": [
    {"file": "a.csv", "rows": 120},
    {"file": "b.csv", "error": "编码不支持"}
  ]
}
```

违规：整体静默成功（C-8）——status 是 ok，但 b.csv 实际失败；下游读到 results 才会发现，且「编码不支持」无 error_code（C-6）。

✅ 改写后：

```json
{
  "tool": "batch_convert",
  "partial": true,
  "succeeded": [{"file": "a.csv", "rows": 120}],
  "failed": [
    {
      "file": "b.csv",
      "error_code": "UNSUPPORTED_ENCODING",
      "message": "文件不是 UTF-8 编码。",
      "retryable": false,
      "recovery_hint": "用 iconv 转码后重试该文件。"
    }
  ]
}
```

说明：partial: true 让调用方一开始就知道要检查 failed 列表；每个失败项带机器可读四字段。
