# clarify-spec

本 Skill 面向 Vibe Coding 的三类文本：人类表达、Multi-Agent 过程文件与 Agent 运行时消息。目标是对它们进行消歧与规范化。
A skill for **disambiguating and standardizing** human expression, multi-agent process artifacts, and runtime agent messages during Vibe Coding. Bilingual (中文/EN). Ships two deterministic linters as the executable spec.

> 灵感来源 [asd-ste100-skill][ref-ste]。它把航空维修英语的受控语言纪律移植给 Agent 读者。本项目将其扩展为**中英双语**，并补充**过程文件架构规范**、**运行时消息契约**与**两个确定性 linter**。

## 问题 / The Problem

Vibe Coding 中，三类文本在人与 Agent、Agent 与 Agent 之间传递时产生二义性，而接收方无法追问：

1. **人类表达**：需求陈述、意图描述、验收标准。典型失效：强度漂移（必须/应当/最好混用）。其他失效：验收无量化、一句多义、模糊量词、营销词。
2. **Multi-Agent 过程文件**：PLAN、交接单、ADR、记忆文件、状态报告。典型失效：缺文件头契约、交接三段不全、决策无理由无备选。
3. **Agent 运行时消息**：A2A 消息体、工具调用与返回、错误事件。典型失效：无信封与关联、意图自由文本、错误只写在自然语言里。

Three text kinds circulate between humans and agents with no back-channel. Ambiguity in either is expensive: requirements drift in strength, handoffs omit what the next agent needs, and runtime errors get executed instead of read.

## 设计：三个软件工程维度 / Design: Three SE Dimensions

| 维度 | 设计决策 | 依据 |
|---|---|---|
| **交互** | 触发契约（双语触发词）；输入分类（A/B/C 三类）；双模式；输出契约——默认只返回结果，请求时附规则表 | RFC 2119；Diátaxis |
| **架构** | 三层渐进披露；规则、模板、脚本三者分离；散文 linter 与消息 linter 分离；规则条目编号可追溯 | GB/T 8567；Nygard ADR；arc42 |
| **性能** | SKILL.md < 500 行；机械规则交 stdlib linter（可进 CI）；`--baseline` 渐进采用；大负载外置（C-11）；改写保精度与情态 | ISO/IEC 25010 / GB/T 25000；SemVer |

## 仓库结构 / Repository Structure

```
clarify-spec/
├── SKILL.md                        # 核心工作流与输出契约（<500 行）
├── references/
│   ├── human-expression-rules.md   # A 类：人类表达规则全文（H-A1…H-A14, R-A1）
│   ├── agent-artifacts-rules.md    # B 类：过程文件规则全文（H-B1…H-B18）
│   ├── runtime-message-rules.md    # C 类：运行时消息规则全文（C-1…C-12）
│   ├── standards-map.md            # 中英经典标准映射总表
│   └── templates.md                # PLAN / HANDOFF / ADR / STATUS 最小模板
├── scripts/
│   ├── spec-lint.py                # 散文与过程文件 linter（纯 stdlib）
│   └── msg-lint.py                 # 运行时消息契约 linter（纯 stdlib）
└── examples/
    ├── before-after.md             # 中英对照改写示例
    ├── runtime-messages.md         # 运行时消息改写示例
    └── linter-edge-cases.md        # 边界测试夹具
```

## 安装 / Installation

### Kimi Work / Claude Code（目录拷贝）

```
git clone https://github.com/ctyytc/clarify-spec.git
cp -r clarify-spec ~/.config/agents/skills/clarify-spec   # 用户级
# 或项目级：cp -r clarify-spec <project>/.agents/skills/clarify-spec
```

### 直接使用 linter

两个 linter 均无依赖，任何 Python 3.8+ 环境可直接运行：

```bash
# spec-lint：散文与过程文件
python3 scripts/spec-lint.py docs/                 # 扫描目录（.md/.txt）
python3 scripts/spec-lint.py --json FILE           # CI 结构化输出
python3 scripts/spec-lint.py --baseline 10 docs/   # 存量文档渐进采用
python3 scripts/spec-lint.py --kind handoff HANDOFF.md  # B 类文件头契约检查
python3 scripts/spec-lint.py --selftest            # 内置自检

# msg-lint：JSON 运行时消息
python3 scripts/msg-lint.py msg.json               # 单条消息契约检查
python3 scripts/msg-lint.py --json msgs/           # 目录批量 + CI 输出
python3 scripts/msg-lint.py --selftest             # 内置自检
```

退出码契约（两个 linter 一致）：硬性违规数 > `--baseline`（默认 0）时 exit 1；建议性发现永不导致失败。

## 使用 / Usage

对 Agent 说：

```
消歧这份需求陈述           / disambiguate this requirement
规范这段表达              / standardize this text
审查这份交接单            / review this handoff doc
改写这条验收标准          / rewrite this acceptance criterion
检查这份 PLAN / ADR       / check this PLAN / ADR
检查这条 A2A 消息         / review this A2A message
规范这个工具调用          / standardize this tool call
```

默认只返回改写后的文本或消息体。要求「show the diff / 改了哪些」时返回规则对照表。

## 标准依据 / Standards

**英文标准**：ASD-STE100 Issue 9（2025）、RFC 2119、RFC 8174。以及 RFC 7807、RFC 3339、RFC 9110。另有 W3C Trace Context 与 ISO/IEC/IEEE 29148。以及 Nygard ADR、Keep a Changelog、SemVer。

**中文标准**：GB/T 8567-2006、GB/T 8566-2007。以及 GB/T 9385、GB/T 25000.10、GB/T 7408（ISO 8601）。

完整映射见 [references/standards-map.md](references/standards-map.md)。

## linter 的设计边界 / Linter Boundaries

linter 只检查机械可判定的结构规则：标点、句长、词表命中、字段存在性。需要语义判断的规则由模型执行，例如关键词同义替换、悬空条件、决策质量、上下文自足。

**linter 零违规不等于合格——它是下限检查，不是充分条件。** linter 永不单独处罚情态表达。「可能失败」「may have failed」属于内容，不属于风格。C 类消息要求把置信度字段化为 confidence，但正文中的推测词本身不触发处罚。该行为由两个 linter 的 `--selftest` 固定断言。

本项目不复现 ASD-STE100 受版权保护的约 900 词词典，仅应用其结构与原理。需要认证级合规时，请从 [ASD 官网][ref-asd] 获取标准原文。

## License

MIT — see [LICENSE](LICENSE).

[ref-ste]: https://github.com/danyuchn/asd-ste100-skill
[ref-asd]: https://www.asd-ste100.org/
