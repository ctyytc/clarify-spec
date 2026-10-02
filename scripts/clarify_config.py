#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
clarify_config.py — clarify-spec 双 linter 共享的项目级配置加载器。

配置文件 .clarify-spec.yml 定义在工作目录（项目根）级别：linter 从当前工作目录
向上逐级查找，最近的配置文件生效；也可用 --config 显式指定路径。
格式为受限 YAML 子集（零依赖，解析行为由 selftest() 固化）：

    # 示例：某项目的自行扩充
    extends: default                 # 仅支持 default（内置词表为基线）
    override:                        # 数值阈值覆盖
      zh_sentence_limit: 80
    add:                             # 词表扩充
      vague_quantifier_zh: [差不多]
      intent_enum:
        - escalate
    remove:                          # 词表移除
      vague_quantifier_zh: [相关]

设计约束：
1. 空配置 = 内置默认，行为完全不变（向后兼容）。
2. 配置文件损坏 = 明确报错并以 exit 2 退出，绝不静默回退默认（fail loud）。
3. 支持行首注释（#）、行内列表 [a, b] 与块列表（- item）两种写法。
4. 词表只增删、阈值只覆盖；规则的硬/建议分级与退出码契约不可配置。
"""

import hashlib
import os

CONFIG_FILENAME = ".clarify-spec.yml"

THRESHOLDS = ("zh_sentence_limit", "en_sentence_limit",
              "zh_pronoun_paragraph_limit", "payload_limit", "long_field_limit")

WORDLISTS = ("marketing_en", "marketing_zh", "vague_quantifier_zh",
             "phrasal_verb_en", "relative_time_zh", "relative_time_en",
             "hedges_zh", "hedges_en", "intent_enum")

DEFAULT_THRESHOLDS = {
    "zh_sentence_limit": 60,           # 中文字（剔除标点后）
    "en_sentence_limit": 25,           # 英文词
    "zh_pronoun_paragraph_limit": 5,   # 每段指示代词建议阈值
    "payload_limit": 2000,             # C-11：payload 外置阈值（字符）
    "long_field_limit": 500,           # 单文本字段外置建议阈值（字符）
}

DEFAULT_WORDLISTS = {
    "marketing_en": [
        "seamless", "robust", "powerful", "cutting-edge", "effortless",
        "blazing", "state-of-the-art", "revolutionary", "world-class",
        "best-in-class", "industry-leading",
    ],
    "marketing_zh": [
        "无缝", "丝滑", "强大", "极致", "革命性", "颠覆性", "赋能",
        "业界领先", "世界一流", "领先一代",
    ],
    "vague_quantifier_zh": ["等等", "相关", "有关", "各种", "之类", "诸多", "若干"],
    "phrasal_verb_en": [
        "spin up", "shut down", "take off", "kick off", "reach out",
        "dive into", "carry out", "roll back", "log in", "log out",
        "sign up", "set up", "point out", "figure out", "look up",
        "hook up", "scale up", "speed up", "break down", "clean up",
        "wrap up", "sum up", "check out",
    ],
    "relative_time_zh": ["稍后", "一会儿", "马上", "尽快", "过两天", "下周"],
    "relative_time_en": ["later", "in a while", "asap", "soon", "shortly"],
    "hedges_zh": ["可能", "也许", "大概", "没准"],
    "hedges_en": ["maybe", "perhaps", "possibly", "probably"],
    "intent_enum": ["delegate", "query", "respond", "report", "clarify", "cancel"],
}


class ConfigError(Exception):
    """配置文件语法或语义错误。消息含文件名与行号。"""


def _parse_inline_list(val, lineno):
    inner = val[1:-1].strip()
    if not inner:
        return []
    items = []
    for part in inner.split(","):
        item = part.strip().strip("'\"")
        if not item:
            raise ConfigError(f"第 {lineno} 行：列表含空项")
        items.append(item)
    return items


def parse_config(text):
    """解析受限 YAML 子集。返回 {"extends", "override", "add", "remove"}。"""
    doc = {"extends": "default", "override": {}, "add": {}, "remove": {}}
    section = None
    last_list_key = None
    for lineno, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if indent == 0:
            if ":" not in stripped:
                raise ConfigError(f"第 {lineno} 行：应为「键: 值」形式：{stripped}")
            key, _, val = stripped.partition(":")
            key, val = key.strip(), val.strip()
            if key not in ("extends", "override", "add", "remove"):
                raise ConfigError(
                    f"第 {lineno} 行：未知顶层键「{key}」（允许：extends/override/add/remove）")
            if key == "extends":
                if val != "default":
                    raise ConfigError(f"第 {lineno} 行：extends 仅支持 default，得到「{val}」")
                doc["extends"] = val
                section = None
            else:
                if val:
                    raise ConfigError(f"第 {lineno} 行：「{key}」是节，不应有同行值")
                section = key
            last_list_key = None
            continue
        # 缩进项：属于某个节
        if section is None:
            raise ConfigError(f"第 {lineno} 行：缩进项不属于任何节")
        if stripped.startswith("- "):
            if last_list_key is None:
                raise ConfigError(f"第 {lineno} 行：列表项「{stripped}」前应有键")
            if not isinstance(doc[section].get(last_list_key), list):
                raise ConfigError(f"第 {lineno} 行：键「{last_list_key}」已定义为标量，不能接列表项")
            doc[section].setdefault(last_list_key, [])
            doc[section][last_list_key].append(stripped[2:].strip().strip("'\""))
            continue
        if ":" not in stripped:
            raise ConfigError(f"第 {lineno} 行：应为「键: 值」形式：{stripped}")
        key, _, val = stripped.partition(":")
        key, val = key.strip(), val.strip()
        last_list_key = key
        if section == "override":
            if key not in THRESHOLDS:
                raise ConfigError(
                    f"第 {lineno} 行：未知阈值「{key}」（允许：{'、'.join(THRESHOLDS)}）")
            try:
                doc["override"][key] = int(val)
            except ValueError:
                raise ConfigError(f"第 {lineno} 行：阈值「{key}」应为整数，得到「{val}」")
        else:
            if key not in WORDLISTS:
                raise ConfigError(
                    f"第 {lineno} 行：未知词表「{key}」（允许：{'、'.join(WORDLISTS)}）")
            if val.startswith("[") and val.endswith("]"):
                doc[section][key] = _parse_inline_list(val, lineno)
            elif val:
                raise ConfigError(f"第 {lineno} 行：词表「{key}」的值应为列表，得到「{val}」")
            else:
                doc[section][key] = []  # 值在后续块列表（- item）给出
    return doc


class Settings:
    """生效规则集 = 内置默认 + 项目配置差异。词表只增删，阈值只覆盖。"""

    def __init__(self):
        self._t = dict(DEFAULT_THRESHOLDS)
        self._w = {k: list(v) for k, v in DEFAULT_WORDLISTS.items()}

    @classmethod
    def built_in(cls):
        return cls()

    def apply(self, doc):
        for k, v in doc["override"].items():
            self._t[k] = v
        for name, items in doc["add"].items():
            for it in items:
                if it not in self._w[name]:
                    self._w[name].append(it)
        for name, items in doc["remove"].items():
            self._w[name] = [x for x in self._w[name] if x not in items]
        return self

    def threshold(self, name):
        return self._t[name]

    def wordlist(self, name):
        return self._w[name]


def find_config(start_dir):
    """自 start_dir 向上逐级查找 .clarify-spec.yml；找到返回路径，否则 None。"""
    d = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(d, CONFIG_FILENAME)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def load_settings(config_path=None, start_dir=None):
    """加载生效配置。

    返回 (settings, source, digest)。source 为配置文件路径或 "built-in defaults"；
    digest 为文件内容 sha256 前 12 位（built-in 时为 None），供 CI 精确复现。
    配置文件损坏抛 ConfigError，调用方应以 exit 2 退出。
    """
    if config_path:
        if not os.path.isfile(config_path):
            raise ConfigError(f"配置文件不存在：{config_path}")
        path = config_path
    else:
        path = find_config(start_dir or os.getcwd())
        if path is None:
            return Settings.built_in(), "built-in defaults", None
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return Settings.built_in().apply(parse_config(text)), path, digest


def selftest():
    """配置解析器自检。返回 0 表示全部通过。"""
    failed = 0

    def check(desc, cond):
        nonlocal failed
        failed += 0 if cond else 1
        print(f"[{'PASS' if cond else 'FAIL'}] {desc}")

    ok_text = """# 示例项目配置
extends: default
override:
  zh_sentence_limit: 80
add:
  vague_quantifier_zh: [差不多, 之类的]
  intent_enum:
    - escalate
remove:
  vague_quantifier_zh: [相关]
"""
    try:
        doc = parse_config(ok_text)
        s = Settings.built_in().apply(doc)
        check("override 生效（zh_sentence_limit=80）", s.threshold("zh_sentence_limit") == 80)
        check("行内列表 add 生效（差不多）", "差不多" in s.wordlist("vague_quantifier_zh"))
        check("块列表 add 生效（escalate）", "escalate" in s.wordlist("intent_enum"))
        check("remove 生效（相关 已移除）", "相关" not in s.wordlist("vague_quantifier_zh"))
        check("默认词表保留（等等 仍在）", "等等" in s.wordlist("vague_quantifier_zh"))
        check("默认阈值保留（en=25）", s.threshold("en_sentence_limit") == 25)
    except ConfigError as e:
        check(f"合法配置被误报：{e}", False)

    bad_cases = [
        ("未知顶层键", "foo: bar\n"),
        ("extends 非 default", "extends: strict\n"),
        ("未知词表", "add:\n  notalist: [x]\n"),
        ("未知阈值", "override:\n  nope: 1\n"),
        ("阈值非整数", "override:\n  zh_sentence_limit: abc\n"),
        ("节带同行值", "add: [x]\n"),
        ("列表项前无键", "add:\n  - x\n"),
    ]
    for desc, text in bad_cases:
        try:
            parse_config(text)
            check(f"非法配置未被拒绝：{desc}", False)
        except ConfigError:
            check(f"非法配置被拒绝：{desc}", True)

    print(f"\nconfig selftest: {'全部通过' if failed == 0 else f'{failed} 项失败'}")
    return 1 if failed else 0


if __name__ == "__main__":
    import sys
    sys.exit(selftest())
