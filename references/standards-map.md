# 标准映射总表 / Standards Map

本表回答一个问题：clarify-spec 的每一条规则，从中英文软件工程经典标准的哪一条来，用什么方式检查。规则条目全文见 `references/human-expression-rules.md` 与 `references/agent-artifacts-rules.md`。

## 总表

| 维度 | 规则域 | 英文经典 | 中文经典 | 落地规则 | 检查方式 |
|---|---|---|---|---|---|
| 表达 | 关键词纪律 | RFC 2119 / RFC 8174 | GB/T 9385-2008 §6 | H-A1, H-A2, A-A1 | 模型 + `rfc2119-mixed` |
| 表达 | 一述一义 | ASD-STE100 Issue 9 §7 | GB/T 8567 正文编写要求 | H-A3, H-A4 | 模型 + `zh-long-sentence` |
| 表达 | 量化验收 | IEEE 830 / ISO/IEC/IEEE 29148 | GB/T 9385 §7.4 可验证性 | H-A5, A-A3 | 模型 + `acceptance-no-metric` |
| 表达 | 指称一致 | ASD-STE100 §1 | GB/T 8567 术语一致性 | H-A6, A-A4 | 模型 + `synonym-rotation`, `zh-pronoun-chain` |
| 表达 | 模糊量词 | ASD-STE100 §1 | 科技写作规范（量词限定） | H-A7 | `vague-quantifier` |
| 表达 | 营销词禁令 | ASD-STE100 §9 | GB/T 8567 客观陈述要求 | H-A8, A-A5 | `marketing-word` |
| 表达 | 情态保护 | ASD-STE100 §3 | GB/T 9385 需求强度分级 | R-A1 | linter 自检固定「永不标记」 |
| 表达 | 中文句法 | —（STE 为英文标准，中文规则为类比推导） | GB/T 8567；科技期刊写作规范 | H-A9, A-A6 | `zh-long-sentence`, `zh-semicolon` |
| 表达 | 英文句法 | ASD-STE100 Issue 9 §3–§9 | — | H-A10–H-A14 | `en-*` 系列 |
| 架构 | 文件头契约 | ISO/IEC/IEEE 29119-3 | GB/T 8567-2006 | H-B1 | `kind-contract` |
| 架构 | 状态机 | ISO/IEC/IEEE 12207 | GB/T 8566-2007 | H-B2, H-B3 | 模型 |
| 架构 | 交接三段式 | Diátaxis how-to | PMBOK 沟通模型 | H-B4–B6 | `kind-contract` + 模型 |
| 架构 | ADR | Michael Nygard ADR；arc42 §9 | GB/T 8567 设计文档要求 | H-B7–B9, A-B1 | `kind-contract` + 模型 |
| 架构 | 变更记录 | Keep a Changelog；SemVer | GB/T 8566 配置管理过程 | H-B15, H-B16 | 模型 |
| 性能 | linter 设计 | Twelve-Factor 显式契约哲学 | GB/T 25000.10 可维护性 | 脚本即规范 | `scripts/spec-lint.py` |

## 三个关键解释

**1. STE 不覆盖中文，中文规则从哪来？**

ASD-STE100 是英文受控语言标准。中文规则（句长、分号、指示代词）不是 STE 的翻译。它们是把 STE 的*消歧原理*映射到中文句法上的推导结果：一词一义、一述一义、主语显式、范围闭合。本土化依据为 GB/T 8567 的编写要求。英文句法规则可直接引用 STE 条文号；中文规则引用 GB/T 8567 与科技写作通行规范。

**2. 为什么 RFC 2119 是"表达"规则而不是"过程"规则？**

RFC 2119 定义的是需求关键词的强度语义。Vibe Coding 中人类表达的第一失效模式正是强度漂移：「必须」「应当」「希望」「最好」混用。后果是 Agent 把可选当强制、把强制当建议。因此关键词纪律归入规范对象 A，并由 GB/T 9385（SRS 规范）在中文学语境下背书。

**3. linter 与模型的分工依据是什么？**

机械规则交给确定性脚本：标点、句长、词表命中、字段存在性。脚本零成本、零漂移、可进 CI。语义判断规则交给模型：关键词同义替换、悬空条件、决策质量。脚本假装能查这些规则，只会制造虚假的合规感。这个分工符合 GB/T 25000.10 对可维护性的定义：规则显式、检查可重复、结果可解释。

## 参考文献

- ASD-STE100 Issue 9, *Simplified Technical English*, ASD, 2025-01. https://www.asd-ste100.org/
- S. Bradner, *Key words for use in RFCs to Indicate Requirement Levels*, RFC 2119, 1997.
- B. Leiba, *Ambiguity of Uppercase vs Lowercase in RFC 2119 Key Words*, RFC 8174, 2017.
- IEEE Std 830-1998（已被 ISO/IEC/IEEE 29148:2018 取代）。
- M. Nygard, *Documenting Architecture Decisions*, 2011. https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- *Keep a Changelog*. https://keepachangelog.com/ ；*Semantic Versioning 2.0.0*. https://semver.org/
- GB/T 8567-2006 计算机软件文档编制规范。
- GB/T 8566-2007 信息技术 软件生存周期过程。
- GB/T 9385-2008 计算机软件需求规格说明规范。
- GB/T 25000.10 系统与软件工程 系统与软件质量要求和评价（SQuaRE）。
