# linter 边界测试夹具 / Linter Edge Cases

本文件**故意不合规**，是 spec-lint.py 的人工验证夹具（`--selftest` 之外的补充）。下文中的英文分号、营销词、模糊量词、短语动词、名词化、超长句均为有意植入；代码围栏内的同名内容必须被豁免。

## 期望结果（人工核对用）

| 规则 | 期望 |
|---|---|
| `en-semicolon` | 围栏外每行最多报告 1 处；围栏内 0 处 |
| `marketing-word` | 围栏外每个违禁词报告 1 处；围栏内 0 处 |
| `vague-quantifier` | 围栏外每个违禁词报告 1 处 |
| `en-phrasal-verb` | 围栏外报告（每行最多 1 个） |
| `en-nominalization` | 围栏外报告 |
| 围栏豁免 | 围栏内任何规则 0 报告 |

精确的计数断言由 `--selftest` 负责，本文件负责「人眼看着对」。

---

Do A; then do B with seamless robust power.

等等，还有各种格式需要支持。

Please reach out to the team and kick off the review; we will perform an analysis of the results.

```text
Do A; then do B with seamless robust power and reach out and kick off everything.
```

支持等等各种相关格式，体验无缝且强大。
