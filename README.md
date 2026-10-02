# clarify-spec

对 Vibe Coding 中的人类表达与 Multi-Agent 过程文件进行**消歧与规范化**的 Skill 项目。
A skill for **disambiguating and standardizing** human expression and multi-agent process artifacts during Vibe Coding. Bilingual (中文/EN). Ships a deterministic linter as the executable spec.

> 灵感来源 [asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill)。它把航空维修英语的受控语言纪律移植给 Agent 读者。本项目将其扩展为**中英双语**，并补充了**过程文件架构规范**与**确定性 linter**。

## 问题 / The Problem

Vibe Coding 中，两类文本在人与 Agent、Agent 与 Agent 之间传递时产生二义性，而接收方无法追问：

1. **人类表达**：需求陈述、意图描述、验收标准。典型失效：强度漂移（必须/应当/最好混用）。其他失效：验收无量化、一句多义、模糊量词、营销词。
2. **Multi-Agent 过程文件**：PLAN、交接单、ADR、记忆文件、状态报告。典型失效：缺文件头契约、交接三段不全、决策无理由无备选。

Two text kinds circulate between humans and agents with no back-channel. Ambiguity in either is expensive: requirements drift in strength, acceptance criteria lack numbers, and handoff docs omit what the next agent needs.

## 设计：三个软件工程维度 / Design: Three SE Dimensions

| 维度 | 设计决策 | 依据 |
|---|---|---|
| **交互** | 触发契约（双语触发词）；输入分类（A 表达 / B 过程文件）；双模式；输出契约——默认只返回结果，请求时才附规则表 | RFC 2119；Diátaxis |
| **架构** | 三层渐进披露（frontmatter → SKILL.md → references/）；规则、模板、脚本三者分离；过程文件模板资产化；规则条目编号可追溯（H-A1…H-B18） | GB/T 8567；Nygard ADR；arc42 |
| **性能** | SKILL.md 控制在 500 行内；机械规则交给纯 stdlib linter（可进 CI）；`--baseline` 支持存量文档渐进采用；改写红线保证精度与情态不损失 | ISO/IEC 25010 / GB/T 25000；SemVer |

## 仓库结构 / Repository Structure

```
clarify-spec/
├── SKILL.md                        # 核心工作流与输出契约（<500 行）
├── references/
│   ├── human-expression-rules.md   # A 类：人类表达规则全文（H-A1…H-A14, R-A1）
│   ├── agent-artifacts-rules.md    # B 类：过程文件规则全文（H-B1…H-B18）
│   ├── standards-map.md            # 中英经典标准映射总表
│   └── templates.md                # PLAN / HANDOFF / ADR / STATUS 最小模板
├── scripts/
│   └── spec-lint.py                # 双语确定性 linter（纯 stdlib）
└── examples/
    ├── before-after.md             # 中英对照改写示例
    └── linter-edge-cases.md        # linter 边界测试夹具
```

## 安装 / Installation

### Kimi Work / Claude Code（目录拷贝）

```
git clone https://github.com/ctyytc/clarify-spec.git
cp -r clarify-spec ~/.config/agents/skills/clarify-spec   # 用户级
# 或项目级：cp -r clarify-spec <project>/.agents/skills/clarify-spec
```

### 直接使用 linter

linter 无依赖，任何 Python 3.8+ 环境可直接运行：

```bash
python3 scripts/spec-lint.py docs/                 # 扫描目录（.md/.txt）
python3 scripts/spec-lint.py --json FILE           # CI 结构化输出
python3 scripts/spec-lint.py --baseline 10 docs/   # 存量文档渐进采用
python3 scripts/spec-lint.py --kind handoff HANDOFF.md  # 过程文件头契约检查
python3 scripts/spec-lint.py --selftest            # 内置自检
```

退出码契约：硬性违规数 > `--baseline`（默认 0）时 exit 1；建议性发现永不导致失败。

## 使用 / Usage

对 Agent 说：

```
消歧这份需求陈述           / disambiguate this requirement
规范这段表达              / standardize this text
审查这份交接单            / review this handoff doc
改写这条验收标准          / rewrite this acceptance criterion
检查这份 PLAN / ADR       / check this PLAN / ADR
```

默认只返回改写后的文本。要求「show the diff / 改了哪些」时返回规则对照表。

## 标准依据 / Standards

- **英文**：ASD-STE100 Issue 9（2025）；RFC 2119 / RFC 8174；ISO/IEC/IEEE 29148。
- **英文**：Michael Nygard ADR；Keep a Changelog；SemVer。
- **中文**：GB/T 8567-2006 计算机软件文档编制规范；GB/T 8566-2007 软件生存周期过程。
- **中文**：GB/T 9385-2008 计算机软件需求规格说明规范；GB/T 25000.10。

完整映射见 [references/standards-map.md](references/standards-map.md)。

## linter 的设计边界 / Linter Boundaries

linter 只检查机械可判定的结构规则：分号、句长、词表命中、字段存在性。需要语义判断的规则由模型执行，例如关键词同义替换、悬空条件、决策质量。

**linter 零违规不等于文档合格——它是下限检查，不是充分条件。** linter 永不标记情态表达。「可能失败」「may have failed」属于内容，不属于风格。该行为由 `--selftest` 固定断言。

本项目不复现 ASD-STE100 受版权保护的约 900 词词典，仅应用其结构与原理。需要认证级合规时，请从 [ASD 官网](https://www.asd-ste100.org/) 获取标准原文。

## License

MIT — see [LICENSE](LICENSE).
