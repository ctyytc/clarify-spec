# clarify-spec

[![ci](https://github.com/ctyytc/clarify-spec/actions/workflows/ci.yml/badge.svg)](https://github.com/ctyytc/clarify-spec/actions/workflows/ci.yml)

本仓库提供两个互补的 Skill，按**信道**拆分 Vibe Coding 的消歧规范。`clarify-spec` 面向人向 Agent 下达的文本。`clarify-runtime` 面向 Agent 之间传递的指令与运行时消息。与人交互的 Agent 只需安装前者，不加载 A2A 规则。
Two complementary skills for **disambiguating and standardizing** Vibe Coding texts, split by channel: `clarify-spec` for human-to-agent expression, `clarify-runtime` for agent-to-agent instructions and runtime messages. Bilingual (中文/EN). Ships deterministic linters as the executable spec.

> 灵感来源 [asd-ste100-skill][ref-ste]。它把航空维修英语的受控语言纪律移植给 Agent 读者。本项目将其扩展为**中英双语**，并补充**过程文件架构规范**、**运行时消息契约**与**确定性 linter**。

## 问题 / The Problem

Vibe Coding 中，文本在两条信道上传递时产生二义性，而接收方无法追问：

1. **人 → Agent**（`clarify-spec`）：需求陈述、意图描述、验收标准。典型失效：强度漂移（必须/应当/最好混用）、验收无量化、一句多义、模糊量词、营销词。过程文件（PLAN、交接单、ADR、记忆文件、状态报告）同在此信道：它们由 Agent 撰写、由人评审。
2. **Agent → Agent**（`clarify-runtime`）：主 Agent 向 sub agent 或编排层派发的自然语言指令。还包括 A2A 消息体、工具调用与返回、错误事件。典型失效：无信封与关联、意图自由文本、错误只写在自然语言里、相对时间。

Ambiguity in either channel is expensive: requirements drift in strength, handoffs omit what the next agent needs, and runtime errors get executed instead of read.

## 设计：三个软件工程维度 / Design: Three SE Dimensions

| 维度 | 设计决策 | 依据 |
|---|---|---|
| **交互** | 按信道拆分为两个 Skill；触发契约（双语触发词）；双姿态（预检/校验只报告不静默改写，改写/构造只输出结果）；双模式；输出契约 | RFC 2119；Diátaxis |
| **架构** | 三层渐进披露；规则、模板、脚本三者分离；散文 linter 与消息 linter 分离。规则条目编号可追溯；跨 Skill 复制文件由 CI 一致性门禁锁定 | GB/T 8567；Nygard ADR；arc42 |
| **性能** | 每个 SKILL.md < 500 行；机械规则交 stdlib linter（可进 CI）；`--baseline` 渐进采用；大负载外置（C-11）；改写保精度与情态 | ISO/IEC 25010 / GB/T 25000；SemVer |

## 仓库结构 / Repository Structure

```
clarify-spec/
├── skills/
│   ├── clarify-spec/                 # Skill 1：人 → Agent 信道（A 类表达 + B 类过程文件）
│   │   ├── SKILL.md                  # 预检与改写两个姿态；输出契约（<500 行）
│   │   ├── references/
│   │   │   ├── human-expression-rules.md   # A 类规则全文（H-A1…H-A14, R-A1）
│   │   │   ├── agent-artifacts-rules.md    # B 类规则全文（H-B1…H-B18）
│   │   │   ├── standards-map.md            # 中英经典标准映射总表
│   │   │   └── templates.md                # PLAN / HANDOFF / ADR / STATUS 最小模板
│   │   ├── scripts/
│   │   │   ├── clarify_config.py           # 项目级配置加载（受限 YAML，单一事实源）
│   │   │   └── spec-lint.py                # 散文与过程文件 linter（纯 stdlib）
│   │   ├── examples/                       # 中英对照改写示例 + 边界测试夹具
│   │   └── tests/fixtures/config/          # 项目级配置夹具
│   └── clarify-runtime/              # Skill 2：Agent → Agent 信道（派发指令 + C 类运行时消息）
│       ├── SKILL.md                  # 接收侧旁路校验与发起侧构造两个姿态（<500 行）
│       ├── references/
│       │   ├── runtime-message-rules.md    # C 类规则全文（C-1…C-12）
│       │   ├── protocol-mapping.md         # C 类字段与 A2A / MCP 的逐字段映射
│       │   └── human-expression-rules.md   # 派发指令适用的表达规则（与 Skill 1 同源）
│       ├── scripts/
│       │   ├── msg-lint.py                 # 运行时消息契约 linter（含 --profile 协议适配）
│       │   ├── spec-lint.py                # 派发指令 linter（与 Skill 1 同源）
│       │   └── clarify_config.py           # 与 Skill 1 同源
│       ├── examples/runtime-messages.md    # 运行时消息改写示例
│       └── tests/fixtures/                 # 消息契约夹具（independent / a2a 两套）
└── .github/workflows/ci.yml          # 双 Skill 自检 + 零违规门禁 + 负向测试 + 复制件一致性门禁
```

标注「同源」的文件在两个 Skill 中各持有一份副本，保证每个 Skill 自包含；CI 的 `diff` 门禁强制副本逐字节一致，防止漂移。

## 安装 / Installation

### Kimi Work / Claude Code（目录拷贝）

```
git clone https://github.com/ctyytc/clarify-spec.git
# 与人交互的 Agent：
cp -r clarify-spec/skills/clarify-spec ~/.config/agents/skills/clarify-spec
# 多 Agent 编排 / 运行时环境（按需两个都装）：
cp -r clarify-spec/skills/clarify-runtime ~/.config/agents/skills/clarify-runtime
# 项目级：cp -r clarify-spec/skills/<name> <project>/.agents/skills/<name>
```

### 直接使用 linter

所有 linter 均无依赖，任何 Python 3.8+ 环境可直接运行：

```bash
# spec-lint：散文、过程文件与派发指令（两个 Skill 各有一份，行为一致）
python3 skills/clarify-spec/scripts/spec-lint.py docs/                 # 扫描目录（.md/.txt）
python3 skills/clarify-spec/scripts/spec-lint.py --json FILE           # CI 结构化输出
python3 skills/clarify-spec/scripts/spec-lint.py --baseline 10 docs/   # 存量文档渐进采用
python3 skills/clarify-spec/scripts/spec-lint.py --kind handoff HANDOFF.md  # B 类文件头契约检查
python3 skills/clarify-spec/scripts/spec-lint.py --selftest            # 内置自检

# msg-lint：JSON 运行时消息
python3 skills/clarify-runtime/scripts/msg-lint.py msg.json               # 单条消息契约检查
python3 skills/clarify-runtime/scripts/msg-lint.py --json msgs/           # 目录批量 + CI 输出
python3 skills/clarify-runtime/scripts/msg-lint.py --profile a2a msg.json # A2A 协议适配（另有 mcp-request / mcp-result）
python3 skills/clarify-runtime/scripts/msg-lint.py --selftest             # 内置自检
```

退出码契约（两个 linter 一致）：硬性违规数 > `--baseline`（默认 0）时 exit 1；建议性发现永不导致失败。配置损坏（`--config` 文件语法或语义非法）时 exit 2 —— fail-loud，绝不静默回退内置默认。

## 项目级配置 / Project-Level Configuration

团队可在工作目录（项目根）放置 `.clarify-spec.yml`，对词表与阈值做差异覆盖。两个 linter 默认自输入文件所在目录**向上逐级查找**该文件，也可用 `--config PATH` 显式指定。文本输出与 `--json` 均报告生效配置来源与内容摘要（sha256 前 12 位），保证 CI 可精确复现。

```yaml
# .clarify-spec.yml —— 受限 YAML 子集：仅 extends / override / add / remove 四个顶层键
extends: default          # 唯一合法值；基线永远是内置默认

override:
  zh_sentence_limit: 80   # 阈值只可覆盖（可覆盖键见 clarify_config.THRESHOLDS）

add:
  vague_quantifier_zh: [差不多]   # 词表只可扩充…
  intent_enum:                   # …或按块列表书写
    - escalate

remove:
  vague_quantifier_zh: [相关]    # 也可移除默认条目
```

配置语义（锁定项）：

1. **词表只增删**：默认词表不可整体替换，`add` 追加、`remove` 移除条目，其余默认条目保留。
2. **阈值只覆盖**：仅 `clarify_config.THRESHOLDS` 中的五个键可被 `override`，且必须为整数。
3. **分级与退出码不可配置**：规则 HARD/ADVISORY 分级、`exit 1` / `exit 2` 契约由 linter 锁定。
4. **fail-loud**：任何语法或语义错误（未知键、未知词表或阈值、非整数值等）都以 exit 2 退出。诊断信息带行号，绝不静默回退到内置默认。

Project-level configuration: drop a `.clarify-spec.yml` at the project root to extend or trim wordlists and override thresholds. Wordlists can only be appended to or trimmed. Thresholds can only be overridden. Rule severity and the exit-code contract are locked. A malformed config fails loudly with exit 2 — never a silent fallback.

## 使用 / Usage

对与人交互的 Agent 说（`clarify-spec`）：

```
检查这条指令有没有歧义     / pre-flight check this instruction
消歧这份需求陈述           / disambiguate this requirement
规范这段表达              / standardize this text
审查这份交接单            / review this handoff doc
改写这条验收标准          / rewrite this acceptance criterion
检查这份 PLAN / ADR       / check this PLAN / ADR
```

对编排层或接收侧 Agent 说（`clarify-runtime`）：

```
校验收到的这条指令         / validate this incoming instruction
派发任务前自检            / pre-flight check before delegation
检查这条 A2A 消息         / review this A2A message
规范这个工具调用          / standardize this tool call
```

预检与校验姿态只报告违规与建议，绝不静默改写他人指令。改写与构造姿态默认只返回结果本身；要求「show the diff / 改了哪些」时返回规则对照表。

## 标准依据 / Standards

**英文标准**：ASD-STE100 Issue 9（2025）、RFC 2119、RFC 8174。以及 RFC 7807、RFC 3339、RFC 9110。另有 W3C Trace Context 与 ISO/IEC/IEEE 29148。以及 Nygard ADR、Keep a Changelog、SemVer。

**中文标准**：GB/T 8567-2006、GB/T 8566-2007。以及 GB/T 9385、GB/T 25000.10、GB/T 7408（ISO 8601）。

完整映射见 [skills/clarify-spec/references/standards-map.md](skills/clarify-spec/references/standards-map.md)。

## linter 的设计边界 / Linter Boundaries

linter 只检查机械可判定的结构规则：标点、句长、词表命中、字段存在性。需要语义判断的规则由模型执行，例如关键词同义替换、悬空条件、决策质量、上下文自足。

**linter 零违规不等于合格——它是下限检查，不是充分条件。** linter 永不单独处罚情态表达。「可能失败」「may have failed」属于内容，不属于风格。C 类消息要求把置信度字段化为 confidence，但正文中的推测词本身不触发处罚。该行为由两个 linter 的 `--selftest` 固定断言。

本项目不复现 ASD-STE100 受版权保护的约 900 词词典，仅应用其结构与原理。需要认证级合规时，请从 [ASD 官网][ref-asd] 获取标准原文。

## License

MIT — see [LICENSE](LICENSE).

[ref-ste]: https://github.com/danyuchn/asd-ste100-skill
[ref-asd]: https://www.asd-ste100.org/
