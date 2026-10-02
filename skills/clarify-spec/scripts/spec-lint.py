#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spec-lint.py — 对人类表达与 Multi-Agent 过程文件进行确定性消歧检查（中英双语）。

设计原则（与 SKILL.md 的契约一致）：
1. 只检查机械可判定的结构规则；需要判断力的规则交给模型，本脚本不假装能查。
2. 硬性违规（HARD）数量超过 --baseline 时 exit 1；建议性发现（ADVISORY）永不导致失败。
3. 永不标记情态与置信表达："may have failed"、"可能失败了" 属于内容，不属于风格。

用法：
    python3 spec-lint.py FILE [FILE ...]
    cat doc.md | python3 spec-lint.py -
    python3 spec-lint.py --json docs/
    python3 spec-lint.py --baseline 5 --disable en-passive,zh-semicolon FILE
    python3 spec-lint.py --kind handoff HANDOFF.md     # 过程文件头契约检查
    python3 spec-lint.py --config .clarify-spec.yml .  # 项目级词表/阈值配置
    python3 spec-lint.py --selftest                    # 内置自检

配置语义（与 clarify_config.py 一致，单一事实源）：
1. 词表只可扩充（add）或移除条目（remove），默认词表不可整体替换；
2. 阈值只可覆盖（override），键名见 clarify_config.THRESHOLDS；
3. 规则分级（HARD/ADVISORY）与退出码契约锁定，不可配置；
4. 配置损坏时 fail-loud：stderr 说明并以 exit 2 退出，绝不静默回退默认。
"""

import argparse
import json
import os
import re
import sys

import clarify_config

VERSION = "0.4.0"

# ---------------------------------------------------------------------------
# 编译型规则模式（词表类规则见 clarify_config.py 的 WORDLISTS，可在项目级
# .clarify-spec.yml 中扩充；此处只保留不可配置的编译型模式）
# ---------------------------------------------------------------------------

EN_NOMINALIZATION = re.compile(
    r"\b(?:make|perform|provide|do|conduct|carry out)\s+(?:a|an|the)\s+"
    r"(analysis|assessment|decision|implementation|validation|confirmation|"
    r"review|update|inspection|evaluation)\b",
    re.IGNORECASE,
)

EN_PASSIVE = re.compile(
    r"\b(?:is|are|was|were|be|been|being)\s+(?:\w+\s+){0,3}\w+ed\b",
    re.IGNORECASE,
)
EN_PERFECT = re.compile(r"\b(?:has|have|had)\s+\w+ed\b", re.IGNORECASE)

ZH_PRONOUN = re.compile(r"(其|该|此|上述|前者|后者)")

# 同义词轮换：同一文档中对同一概念使用多个名称，读者无法判断是同一物还是多物
SYNONYM_GROUPS = [
    ["user", "customer", "client"],
    ["agent", "assistant", "bot", "worker"],
    ["config", "configuration", "setting"],
    ["task", "job", "assignment"],
]

ZH_KEYWORDS_2119 = ["必须", "应当", "不得", "禁止", "可以"]
EN_KEYWORDS_2119 = ["MUST", "SHALL", "SHOULD", "MUST NOT", "SHOULD NOT", "MAY"]

# 过程文件头契约：--kind 触发；字段缺失为硬性违规
KIND_REQUIRED_FIELDS = {
    "plan":    ["目标", "状态", "最后更新"],
    "handoff": ["已完成", "待办", "风险"],
    "adr":     ["状态", "决策", "备选"],
    "status":  ["进展", "阻塞", "下一步"],
}

HARD = "HARD"
ADVISORY = "ADVISORY"


# ---------------------------------------------------------------------------
# 扫描器
# ---------------------------------------------------------------------------

class Finding:
    __slots__ = ("file", "line", "rule", "severity", "message")

    def __init__(self, file, line, rule, severity, message):
        self.file = file
        self.line = line
        self.rule = rule
        self.severity = severity
        self.message = message

    def to_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


def strip_fenced(text):
    """返回 (行列表, 行号列表)，剔除代码围栏内的内容。"""
    kept, kept_no = [], []
    in_fence = False
    for no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if not in_fence:
            kept.append(line)
            kept_no.append(no)
    return kept, kept_no


def split_sentences(paragraph):
    """按英中文句末标点切句；返回句子与其在段落中的偏移列表。"""
    parts = []
    buf = ""
    for ch in paragraph:
        buf += ch
        if ch in ".!?。！？":
            parts.append(buf.strip())
            buf = ""
    if buf.strip():
        parts.append(buf.strip())
    return parts


def word_count(sentence):
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'\-]*", sentence))


def char_count(sentence):
    """中文字数：剔除空白与标点后的字符数。"""
    return len(re.sub(r"[\s，、；：""''（）《》〈〉,.;:!?。！？·—-]", "", sentence))


def has_cjk(sentence):
    return bool(re.search(r"[\u4e00-\u9fff]", sentence))


def strip_frontmatter(text):
    """剔除 YAML frontmatter：首行为 --- 时，剔除到闭合的 --- 为止。"""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[i + 1:], i + 2  # (内容行, 首个内容行的原始行号)
    return lines, 1


INLINE_CODE = re.compile(r"`[^`\n]*`")


def strip_inline_code(line):
    """剔除行内代码跨：规则文档引用违禁词时用反引号包裹即可豁免。"""
    return INLINE_CODE.sub("", line)


LIST_MARKER = re.compile(r"^\s*(?:[-*+] |\d+[.)] )")


def build_segments(lines, line_nos):
    """句级检查单元：列表项与表格单元格独立成段，散文段落跨行聚合。

    不拆分会把整列列表或整张表拼成一个超长「句子」，造成句长误报。
    """
    segs = []
    para, para_no = [], None

    def flush():
        nonlocal para, para_no
        if para:
            segs.append((para_no, " ".join(para)))
            para, para_no = [], None

    for line, no in zip(lines, line_nos):
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if LIST_MARKER.match(stripped):
            flush()
            segs.append((no, stripped))
        elif stripped.startswith("|"):
            flush()
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                for c in cells:
                    if c:
                        segs.append((no, c))
        else:
            if para_no is None:
                para_no = no
            para.append(stripped)
    flush()
    return segs


def scan_text(text, filename, disabled, settings=None):
    if settings is None:
        settings = clarify_config.Settings.built_in()
    zh_sent_limit = settings.threshold("zh_sentence_limit")
    en_sent_limit = settings.threshold("en_sentence_limit")
    zh_pronoun_para_limit = settings.threshold("zh_pronoun_paragraph_limit")
    marketing_words = (settings.wordlist("marketing_en")
                       + settings.wordlist("marketing_zh"))
    vague_quantifiers = settings.wordlist("vague_quantifier_zh")
    phrasal_verbs = settings.wordlist("phrasal_verb_en")
    findings = []
    raw_lines, first_no = strip_frontmatter(text)
    lines, line_nos = strip_fenced("\n".join(raw_lines))
    line_nos = [n + first_no - 1 for n in line_nos]
    disabled = set(disabled)

    def add(no, rule, severity, message):
        if rule not in disabled:
            findings.append(Finding(filename, no, rule, severity, message))

    # --- 行级检查（剔除行内代码跨后匹配词表）---
    for line, no in zip(lines, line_nos):
        line = strip_inline_code(line)
        if ";" in line:
            add(no, "en-semicolon", HARD,
                "英文分号；STE 禁止该标点，拆为独立句 / semicolon; split into separate sentences")
        if "；" in line:
            add(no, "zh-semicolon", ADVISORY,
                "中文分号；并列分句建议拆句或改为列表 / consider splitting the clause")
        for w in marketing_words:
            if re.search(re.escape(w), line, re.IGNORECASE if w.isascii() else 0):
                add(no, "marketing-word", HARD,
                    f"营销词「{w}」：声称质量而不给出度量，删除或改为度量值 / marketing adjective; delete or cite the metric")
        for w in vague_quantifiers:
            if w in line:
                add(no, "vague-quantifier", HARD,
                    f"模糊量词「{w}」造成范围二义；枚举全部项或给出确切范围 / vague quantifier; enumerate or quantify")
        m = EN_NOMINALIZATION.search(line)
        if m:
            add(no, "en-nominalization", HARD,
                f"名词化动作「{m.group(0)}」：改用动词使动作与执行者显式 / use the verb form instead")
        for pv in phrasal_verbs:
            if re.search(r"\b" + re.escape(pv) + r"\b", line, re.IGNORECASE):
                add(no, "en-phrasal-verb", HARD,
                    f"短语动词「{pv}」语义不可由部件推知；改用单一动词 / replace with a single plain verb")
                break
        m = EN_PASSIVE.search(line)
        if m:
            add(no, "en-passive", ADVISORY,
                f"疑似被动语态「{m.group(0)}」：确认执行者是否应当显式 / possible passive voice")
        m = EN_PERFECT.search(line)
        if m:
            add(no, "en-present-perfect", ADVISORY,
                f"完成时「{m.group(0)}」：若简单式损失「当前相关性」信息则保留，否则改用简单式 / compound tense; keep only if it carries meaning the simple form cannot")

    # --- 句级检查（列表项/表格单元独立成段）---
    for base_no, seg in build_segments(lines, line_nos):
        clean = strip_inline_code(seg)
        for sent in split_sentences(clean):
            if has_cjk(sent):
                n = char_count(sent)
                if n > zh_sent_limit:
                    add(base_no, "zh-long-sentence", HARD,
                        f"中文句长 {n} 字（上限 {zh_sent_limit}）；一述一义，拆为多单句 / split into one-claim sentences")
            else:
                n = word_count(sent)
                if n > en_sent_limit:
                    add(base_no, "en-long-sentence", HARD,
                        f"英文句长 {n} 词（上限 {en_sent_limit}）；一述一义，拆为多单句 / split into one-claim sentences")
        zh_pron = ZH_PRONOUN.findall(clean)
        if len(zh_pron) > zh_pronoun_para_limit:
            add(base_no, "zh-pronoun-chain", ADVISORY,
                f"段落内指示代词 ×{len(zh_pron)}（其/该/此/上述…）；就近还原名词以消歧 / restore the noun near its use")

    # --- 文档级检查 ---
    joined = "\n".join(lines)
    lowered = joined.lower()

    for group in SYNONYM_GROUPS:
        present = [w for w in group if re.search(r"\b" + re.escape(w) + r"\b", lowered)]
        if len(present) >= 2:
            add(line_nos[0] if line_nos else 1, "synonym-rotation", ADVISORY,
                f"同义轮换：{ '/'.join(present) } 在文中指代同一概念时请固定其一 / pick one name and reuse it")

    has_zh_kw = any(k in joined for k in ZH_KEYWORDS_2119)
    has_en_kw = any(re.search(r"\b" + k + r"\b", joined) for k in EN_KEYWORDS_2119)
    if has_zh_kw and has_en_kw:
        add(line_nos[0] if line_nos else 1, "rfc2119-mixed", ADVISORY,
            "RFC 2119 关键词中英混用；同一文档保持一套关键词体系 / keep one keyword system per document")

    for no, line in zip(line_nos, lines):
        if ("验收" in line or "acceptance" in line.lower()) and not re.search(r"\d", line):
            add(no, "acceptance-no-metric", ADVISORY,
                "验收标准无量化指标；给出数字、单位或阈值 / state a number, unit, or threshold")

    return findings


def scan_kind_contract(text, filename, kind, disabled):
    """过程文件头契约检查：仅在 --kind 指定时运行。"""
    if kind not in KIND_REQUIRED_FIELDS:
        return []
    missing = [f for f in KIND_REQUIRED_FIELDS[kind] if f not in text]
    if not missing or "kind-contract" in disabled:
        return []
    return [Finding(filename, 1, "kind-contract", HARD,
                    f"{kind} 文件缺少必需字段：{'、'.join(missing)} / missing required fields: {', '.join(missing)}")]


# ---------------------------------------------------------------------------
# 自检
# ---------------------------------------------------------------------------

def selftest():
    cases = [
        # (说明, 文本, 必须命中的规则集, 必须不命中的规则集)
        ("英文分号", "Do A; then do B.", {"en-semicolon"}, set()),
        ("英文超长句", "This sentence is deliberately padded with a sufficient number of plain words to comfortably exceed the twenty five word limit imposed on english sentences by this linter today.", {"en-long-sentence"}, set()),
        ("中文超长句", "这句话刻意写得足够长，以便超过六十个字符的中文句长上限，从而验证 linter 能够正确识别并报告此类违规情况，确保规则真正生效并且稳定可靠地运行。", {"zh-long-sentence"}, set()),
        ("营销词", "本方案提供无缝且极致的用户体验，堪称业界领先。", {"marketing-word"}, set()),
        ("模糊量词", "支持各种格式与相关配置。", {"vague-quantifier"}, set()),
        ("短语动词", "Please reach out to the team and kick off the review.", {"en-phrasal-verb"}, set()),
        ("名词化", "We will perform an analysis of the log.", {"en-nominalization"}, set()),
        ("情态保护", "The request may have failed.", set(), {"marketing-word", "en-semicolon", "vague-quantifier"}),
        ("中文情态保护", "请求可能失败了，需要检查日志。", set(), {"vague-quantifier"}),
        ("合规中文句", "打开配置文件。读取第三行。比对期望值。", set(), {"zh-long-sentence", "vague-quantifier"}),
        ("代码围栏豁免", "```\nDo A; then do B with seamless robust power.\n```", set(), {"en-semicolon", "marketing-word"}),
        ("被动语态建议", "The file was deleted by the agent.", {"en-passive"}, set()),
        ("完成时建议", "We have received the report.", {"en-present-perfect"}, set()),
        ("验收无量化", "验收标准：功能正确。", {"acceptance-no-metric"}, set()),
    ]
    failed = 0
    for desc, text, must_hit, must_miss in cases:
        got = {f.rule for f in scan_text(text, "<selftest>", set())}
        missing = must_hit - got
        unexpected = must_miss & got
        ok = not missing and not unexpected
        if not ok:
            failed += 1
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {desc} 命中={sorted(got) or '无'}")
        if missing:
            print(f"       期望命中但未命中: {sorted(missing)}")
        if unexpected:
            print(f"       不应命中却命中: {sorted(unexpected)}")
    # 情态保护专项断言：硬性违规数必须为 0
    hard = [f for f in scan_text("The request may have failed. 请求可能失败了。", "<selftest>", set())
            if f.severity == HARD]
    if hard:
        failed += 1
        print(f"[FAIL] 情态保护：出现 {len(hard)} 条硬性违规")
    else:
        print("[PASS] 情态保护：may have failed / 可能 不触发任何硬性违规")
    # 契约检查
    adr_missing = scan_kind_contract("# ADR\n状态: 已接受", "<selftest>", "adr", set())
    if adr_missing and adr_missing[0].rule == "kind-contract":
        print("[PASS] kind-contract：adr 缺字段被报告")
    else:
        failed += 1
        print("[FAIL] kind-contract：adr 缺字段未被报告")
    # 项目级配置：扩充词表后新词命中、移除词表后旧词放行、阈值覆盖生效
    cfg = clarify_config.Settings.built_in().apply(
        clarify_config.parse_config(
            "override:\n  zh_sentence_limit: 10\n"
            "add:\n  vague_quantifier_zh: [差不多]\n"
            "remove:\n  vague_quantifier_zh: [相关]\n"))
    got = {f.rule for f in scan_text("结果差不多完成了。涉及相关的配置。", "<selftest>", set(), cfg)}
    if "vague-quantifier" in got and len(got) == 1:
        print("[PASS] 项目级配置：add/remove 词表生效")
    else:
        failed += 1
        print(f"[FAIL] 项目级配置词表：命中={sorted(got)}")
    long_zh = "这是一句用于阈值覆盖验证的中文句子，长度超过十个字但不超过默认上限。"
    got2 = {f.rule for f in scan_text(long_zh, "<selftest>", set(), cfg)}
    if "zh-long-sentence" in got2:
        print("[PASS] 项目级配置：override 阈值生效")
    else:
        failed += 1
        print(f"[FAIL] 项目级配置阈值：命中={sorted(got2)}")
    # 共享配置模块自检
    failed += clarify_config.selftest()
    print(f"\nselftest: {'全部通过' if failed == 0 else f'{failed} 项失败'}")
    return 1 if failed else 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def iter_input_files(paths):
    for p in paths:
        if p == "-":
            yield "<stdin>", sys.stdin.read()
        elif os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for name in sorted(names):
                    if name.endswith((".md", ".txt")):
                        full = os.path.join(root, name)
                        with open(full, encoding="utf-8") as fh:
                            yield full, fh.read()
        else:
            with open(p, encoding="utf-8") as fh:
                yield p, fh.read()


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="spec-lint: 双语表达与过程文件消歧 linter（结构规则机械检查）")
    ap.add_argument("files", nargs="*", help="Markdown/文本文件、目录，或 - 表示 stdin")
    ap.add_argument("--json", action="store_true", help="结构化 JSON 输出")
    ap.add_argument("--baseline", type=int, default=0,
                    help="允许的硬性违规数，超过则 exit 1（存量文档渐进采用）")
    ap.add_argument("--disable", default="", help="逗号分隔的禁用的规则名")
    ap.add_argument("--kind", choices=sorted(KIND_REQUIRED_FIELDS),
                    help="按过程文件类型检查头契约：plan/handoff/adr/status")
    ap.add_argument("--config", metavar="PATH",
                    help="项目级 .clarify-spec.yml 路径；缺省时自输入向上查找；"
                         "配置损坏则 exit 2（fail-loud，绝不静默回退）")
    ap.add_argument("--selftest", action="store_true", help="运行内置自检")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.files:
        ap.error("请提供文件路径、目录或 -（stdin）")

    try:
        settings, cfg_source, cfg_digest = clarify_config.load_settings(
            args.config, start_dir=args.files[0] if len(args.files) == 1 else os.getcwd())
    except clarify_config.ConfigError as exc:
        print(f"spec-lint: 配置文件损坏（{exc}）/ malformed config", file=sys.stderr)
        return 2

    disabled = {s.strip() for s in args.disable.split(",") if s.strip()}
    all_findings = []
    for filename, text in iter_input_files(args.files):
        all_findings.extend(scan_text(text, filename, disabled, settings))
        if args.kind:
            all_findings.extend(scan_kind_contract(text, filename, args.kind, disabled))

    hard = [f for f in all_findings if f.severity == HARD]
    advisory = [f for f in all_findings if f.severity == ADVISORY]
    cfg_info = {"source": cfg_source, "digest": cfg_digest}

    if args.json:
        print(json.dumps({
            "tool": "spec-lint",
            "version": VERSION,
            "config": cfg_info,
            "summary": {"hard": len(hard), "advisory": len(advisory),
                        "baseline": args.baseline, "exit": 1 if len(hard) > args.baseline else 0},
            "findings": [f.to_dict() for f in all_findings],
        }, ensure_ascii=False, indent=2))
    else:
        for f in all_findings:
            print(f"{f.file}:{f.line} [{f.severity}] {f.rule}: {f.message}")
        print(f"\n{len(hard)} hard / {len(advisory)} advisory "
              f"(baseline {args.baseline}) -> exit {1 if len(hard) > args.baseline else 0}")
        if cfg_source != "built-in defaults":
            print(f"config: {cfg_source} (sha256:{cfg_digest})")
        else:
            print("config: built-in defaults")

    return 1 if len(hard) > args.baseline else 0


if __name__ == "__main__":
    sys.exit(main())
