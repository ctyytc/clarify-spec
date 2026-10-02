#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
msg-lint.py — Agent 运行时消息（A2A / 工具调用 / 事件）的确定性契约检查。

对应 references/runtime-message-rules.md 中可机械判定的 C 类规则。
退出码契约与 spec-lint.py 一致：硬性违规超 --baseline 时 exit 1；建议性发现永不失败。
情态保护继承 R-A1：推测词本身不违规，未字段化才违规（C-5）。

用法：
    python3 msg-lint.py MSG.json [MSG.json ...]
    cat msg.json | python3 msg-lint.py -
    python3 msg-lint.py --json msgs/
    python3 msg-lint.py --baseline 3 --disable c10-time-relative MSG.json
    python3 msg-lint.py --selftest
"""

import argparse
import json
import os
import re
import sys

VERSION = "0.2.0"

INTENT_ENUM = ("delegate", "query", "respond", "report", "clarify", "cancel")
REQUIRED_ENVELOPE = ("message_id", "sender", "recipient",
                     "timestamp", "correlation_id", "intent")
ERROR_REQUIRED = ("error_code", "message", "retryable", "recovery_hint")

RFC3339_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$")

RELATIVE_TIME_ZH = ["稍后", "一会儿", "马上", "尽快", "过两天", "下周"]
RELATIVE_TIME_EN = ["later", "in a while", "asap", "soon", "shortly"]

HEDGES_ZH = ["可能", "也许", "大概", "没准"]
HEDGES_EN = ["maybe", "perhaps", "possibly", "probably"]

PAYLOAD_LIMIT = 2000      # C-11：超过此字符数的 payload 应外置为 artifact
LONG_FIELD_LIMIT = 500    # 单字段超长：提示外置并按 A 类 prose 规则检查

HARD = "HARD"
ADVISORY = "ADVISORY"


class Finding:
    __slots__ = ("file", "path", "rule", "severity", "message")

    def __init__(self, file, path, rule, severity, message):
        self.file = file
        self.path = path
        self.rule = rule
        self.severity = severity
        self.message = message

    def to_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


def walk_strings(obj, prefix="$"):
    """递归收集 JSON 中所有字符串值及其路径。"""
    if isinstance(obj, str):
        yield prefix, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_strings(v, f"{prefix}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_strings(v, f"{prefix}[{i}]")


def hit_word(text, word):
    if word.isascii():
        return re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE)
    return word in text


def scan_message(msg, filename, disabled):
    findings = []
    disabled = set(disabled)

    def add(path, rule, severity, message):
        if rule not in disabled:
            findings.append(Finding(filename, path, rule, severity, message))

    if not isinstance(msg, dict):
        add("$", "c1-envelope", HARD, "消息体必须是 JSON 对象 / message must be a JSON object")
        return findings

    # --- C-1 信封契约 ---
    for f in REQUIRED_ENVELOPE:
        if f not in msg:
            add("$", "c1-envelope", HARD, f"信封缺字段 {f} / missing envelope field: {f}")
    ts = msg.get("timestamp")
    if isinstance(ts, str) and not RFC3339_UTC.match(ts):
        add("$.timestamp", "c1-envelope", HARD,
            f"timestamp 不是 RFC 3339 UTC 格式「{ts}」/ timestamp must be RFC 3339 with explicit zone")

    # --- C-2 意图枚举 ---
    intent = msg.get("intent")
    if intent is not None and intent not in INTENT_ENUM:
        add("$.intent", "c2-intent-enum", HARD,
            f"intent「{intent}」不在封闭枚举内 / intent must be one of {', '.join(INTENT_ENUM)}")

    # --- C-6 错误机器可读 ---
    err = msg.get("error")
    if isinstance(err, dict):
        for f in ERROR_REQUIRED:
            if f not in err:
                add("$.error", "c6-error-shape", HARD,
                    f"error 缺字段 {f}（C-6 四字段）/ error object missing: {f}")

    # --- 文本字段扫描：C-10 相对时间、C-5 情态字段化、长文本建议 ---
    hedged = False
    for path, text in walk_strings(msg):
        for w in RELATIVE_TIME_ZH + RELATIVE_TIME_EN:
            if hit_word(text, w):
                add(path, "c10-time-relative", HARD,
                    f"相对时间「{w}」：改用绝对 UTC 时间戳 / relative time; use an absolute UTC timestamp")
        for w in HEDGES_ZH + HEDGES_EN:
            if hit_word(text, w):
                hedged = True
        if len(text) > LONG_FIELD_LIMIT:
            add(path, "c11-long-field", ADVISORY,
                f"文本字段 {len(text)} 字符：建议外置为 artifact 并按 A 类规则检查 / long text field; consider an artifact reference")

    if hedged and "confidence" not in msg:
        add("$", "c5-confidence-fielded", HARD,
            "正文含推测词而消息无 confidence 字段（C-5）/ hedge words present without a confidence field")

    # --- 建议性契约 ---
    if "ack_required" not in msg:
        add("$", "c7-delivery", ADVISORY, "未声明 ack_required（none/ack/response）")
    if "timeout_seconds" not in msg:
        add("$", "c7-delivery", ADVISORY, "未声明 timeout_seconds")
    if "schema_version" not in msg:
        add("$", "c12-versioning", ADVISORY, "未声明 schema_version（SemVer）")

    payload = msg.get("payload")
    if payload is not None:
        size = len(json.dumps(payload, ensure_ascii=False))
        if size > PAYLOAD_LIMIT and "artifact_ref" not in msg:
            add("$.payload", "c11-payload-size", ADVISORY,
                f"payload {size} 字符（上限 {PAYLOAD_LIMIT}）：外置为 artifact 并传 artifact_ref / payload too large; use an artifact reference")

    return findings


def selftest():
    base = {
        "message_id": "m-1", "sender": "planner", "recipient": "coder",
        "timestamp": "2026-10-02T08:00:00Z", "correlation_id": "c-1",
        "intent": "delegate", "schema_version": "1.0.0",
        "ack_required": "response", "timeout_seconds": 300,
        "confidence": "confirmed",
        "message": "实现 parser 模块。",
    }
    cases = [
        ("合规信封", dict(base), set(), set()),
        ("缺 correlation_id", {k: v for k, v in base.items() if k != "correlation_id"},
         {"c1-envelope"}, set()),
        ("timestamp 无时区", dict(base, timestamp="2026-10-02 08:00:00"),
         {"c1-envelope"}, set()),
        ("意图自由文本", dict(base, intent="delegate tasks please"),
         {"c2-intent-enum"}, set()),
        ("error 缺 retryable", dict(base, error={"error_code": "E_TIMEOUT", "message": "超时", "recovery_hint": "重试"}),
         {"c6-error-shape"}, set()),
        ("相对时间", dict(base, message="请稍后重试"), {"c10-time-relative"}, set()),
        ("英文相对时间", dict(base, message="try again later"), {"c10-time-relative"}, set()),
        ("推测词未字段化", {k: v for k, v in dict(base, message="结果可能不完整").items() if k != "confidence"},
         {"c5-confidence-fielded"}, set()),
        ("推测词已字段化", dict(base, message="结果可能不完整"), set(), {"c5-confidence-fielded"}),
        ("推测词永不单独处罚", dict(base, message="结果可能不完整"), set(), {"c10-time-relative"}),
    ]
    failed = 0
    for desc, obj, must_hit, must_miss in cases:
        got = {f.rule for f in scan_message(obj, "<selftest>", set())}
        missing, unexpected = must_hit - got, must_miss & got
        ok = not missing and not unexpected
        failed += 0 if ok else 1
        print(f"[{'PASS' if ok else 'FAIL'}] {desc} 命中={sorted(got) or '无'}")
        if missing:
            print(f"       期望命中但未命中: {sorted(missing)}")
        if unexpected:
            print(f"       不应命中却命中: {sorted(unexpected)}")
    # 建议性永不失败：满建议性消息硬性数必须为 0
    advisory_only = {k: v for k, v in base.items()
                     if k not in ("ack_required", "timeout_seconds", "schema_version")}
    advisory_only["payload"] = "x" * (PAYLOAD_LIMIT + 1)
    hard = [f for f in scan_message(advisory_only, "<selftest>", set()) if f.severity == HARD]
    if hard:
        failed += 1
        print(f"[FAIL] 建议性隔离：出现 {len(hard)} 条硬性违规")
    else:
        print("[PASS] 建议性隔离：缺 ack/timeout/version 与大 payload 不触发硬性违规")
    print(f"\nselftest: {'全部通过' if failed == 0 else f'{failed} 项失败'}")
    return 1 if failed else 0


def iter_inputs(paths):
    for p in paths:
        if p == "-":
            yield "<stdin>", sys.stdin.read()
        elif os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for name in sorted(names):
                    if name.endswith(".json"):
                        full = os.path.join(root, name)
                        with open(full, encoding="utf-8") as fh:
                            yield full, fh.read()
        else:
            with open(p, encoding="utf-8") as fh:
                yield p, fh.read()


def main(argv=None):
    ap = argparse.ArgumentParser(description="msg-lint: 运行时消息契约 linter（C 类规则机械检查）")
    ap.add_argument("files", nargs="*", help="JSON 消息文件、目录，或 - 表示 stdin")
    ap.add_argument("--json", action="store_true", help="结构化 JSON 输出")
    ap.add_argument("--baseline", type=int, default=0, help="允许的硬性违规数")
    ap.add_argument("--disable", default="", help="逗号分隔的禁用的规则名")
    ap.add_argument("--selftest", action="store_true", help="运行内置自检")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.files:
        ap.error("请提供 JSON 文件、目录或 -（stdin）")

    disabled = {s.strip() for s in args.disable.split(",") if s.strip()}
    all_findings = []
    for filename, raw in iter_inputs(args.files):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as e:
            all_findings.append(Finding(filename, "$", "c0-parse", HARD, f"JSON 解析失败：{e}"))
            continue
        all_findings.extend(scan_message(msg, filename, disabled))

    hard = [f for f in all_findings if f.severity == HARD]
    advisory = [f for f in all_findings if f.severity == ADVISORY]
    exit_code = 1 if len(hard) > args.baseline else 0

    if args.json:
        print(json.dumps({
            "tool": "msg-lint", "version": VERSION,
            "summary": {"hard": len(hard), "advisory": len(advisory),
                        "baseline": args.baseline, "exit": exit_code},
            "findings": [f.to_dict() for f in all_findings],
        }, ensure_ascii=False, indent=2))
    else:
        for f in all_findings:
            print(f"{f.file}:{f.path} [{f.severity}] {f.rule}: {f.message}")
        print(f"\n{len(hard)} hard / {len(advisory)} advisory "
              f"(baseline {args.baseline}) -> exit {exit_code}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
