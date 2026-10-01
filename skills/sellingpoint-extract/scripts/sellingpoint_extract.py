#!/usr/bin/env python3
"""卖点提炼（零依赖，FAB 结构）。

把商品资料里的属性转成「特性 Feature → 优势 Advantage → 利益 Benefit」卖点卡，
并按受众分层排序，输出可直接喂给文案/视频/详情页的结构化卖点清单。

v2 修订（2026-09）
------------------
v1 会把写死的成品文案注入到任何商品上，属**编造卖点 + 违规比较**：
  1. `BENEFIT_MAP` 是关键词 → 成品利益点，例如属性里出现「材质」就注入
     「**接触食品安全，长期用不担心**」—— 在没有任何资质/检测依据的情况下，
     替商家做**食品安全声明**（合规高危）；「保温」→「出门一天随时有热水」
     同样是替商家做未经实测的承诺。
  2. `advantage` 模板固定拼「**优于同价位常见水平**」—— 无依据的竞品比较，
     直接触碰业务红线「不贬低竞品 / 不引用未核实的外部事实」。
  实测中该缺陷未触发，只因当时素材（香氛）没有命中这些属性关键词；
  换个品类（保温杯/充电宝）就会立即触发，属典型的「沉默炸弹」。

v2 起：
  - 脚本**不再产出可对外发布的成品利益点**，只给「利益方向 + 需要什么证据」；
  - 调用方若已核验过具体利益点文案，用 `--benefits '{"保温":"…"}'` 传入，
    产出里会标 `benefit_source: "caller"`（脚本不负责核实调用方给的内容）；
  - `advantage` 去掉「优于同价位常见水平」，只做中性的属性复述；
  - 新增 `compliance_review`：命中食品接触 / 特殊人群 / 功效宣称 / 绝对化用语
    的属性会被单独标记并给出理由，提示必须补资质或改写。

用法:
    python3 sellingpoint_extract.py --file product.json
    echo '{"name":"保温杯","attrs":{"容量":"500ml","保温":"24小时"}}' | python3 sellingpoint_extract.py --json
    python3 sellingpoint_extract.py --file product.json --benefits '{"保温":"实测 24h 保温（附检测报告）"}'
    python3 sellingpoint_extract.py --selftest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 属性关键词 → (利益方向, 还需要什么证据) —— 只是方向，不是可直接发布的文案
BENEFIT_DIRECTION = {
    "保温": ("省事（少反复加热）", "需实测保温时长与测试条件"),
    "容量": ("省事（少续装）", "需明确容量口径：满杯 / 有效容量"),
    "重量": ("便携（更轻）", "需给出实测重量与称量口径"),
    "材质": ("安心（接触体验）", "涉及接触安全，需食品级资质或检测报告后才可对外声称"),
    "续航": ("省心（少充电）", "需实测续航时长与使用条件"),
    "便携": ("便携（易携带）", "需给出具体尺寸与重量"),
    "防水": ("适用场景更广", "需标明防水等级（如 IPX4）与测试条件"),
    "静音": ("不打扰他人", "需实测噪声值（dB）与测试距离"),
    "省电": ("长期用电成本更低", "需实测功耗；不得承诺「省下多少钱」"),
    "保修": ("售后有兜底", "需给出保修期限与覆盖范围"),
    "尺寸": ("适配（更好摆放/佩戴）", "需给出具体尺寸与适配场景"),
    "成分": ("安心（成分透明）", "需成分表原文；不得声称功效"),
}
AUDIENCE_HINT = {
    "通勤人群": ["便携", "容量", "续航", "轻"],
    "宝妈": ["材质", "安全", "易清洗", "静音"],
    "学生党": ["价格", "颜值", "容量", "轻"],
    "户外人群": ["防水", "续航", "耐用", "保温"],
}

# 合规敏感属性：命中即必须补资质/改写，不得直接沿用
COMPLIANCE_SENSITIVE = [
    (r"食品|食用|入口|接触食物|食品级", "涉及食品接触，需食品级资质或检测报告"),
    (r"婴幼|儿童|宝宝|孕妇|新生儿", "涉及特殊人群，不得做安全 / 可用性承诺"),
    (r"治疗|疗效|功效|抗菌|杀菌|消炎|药", "涉及功效宣称，需资质且不得声称疗效"),
    (r"绝对|100%|完全|无任何|永久", "含绝对化用语，违反广告法禁用词"),
]


def extract(product: dict, verified_benefits: dict[str, str] | None = None) -> dict:
    verified_benefits = verified_benefits or {}
    name = product.get("name", "未命名商品")
    attrs = product.get("attrs", {}) or {}
    cards = []
    for k, v in attrs.items():
        direction, evidence = "", ""
        key_hit = ""
        for key, (d, e) in BENEFIT_DIRECTION.items():
            if key in str(k) or key in str(v):
                direction, evidence, key_hit = d, e, key
                break

        # 调用方核验过的成品文案（脚本只透传，不负责核实内容真伪）
        benefit = verified_benefits.get(key_hit, "") if key_hit else ""
        source = "caller" if benefit else ("direction_only" if direction else "none")

        reviews = [why for pat, why in COMPLIANCE_SENSITIVE
                   if re.search(pat, f"{k}{v}")]

        cards.append({
            "feature": f"{k}：{v}",
            # 中性复述：v1 在这里拼「优于同价位常见水平」（无依据的竞品比较）
            "advantage": f"{k}为 {v}",
            "benefit_direction": direction or "（未能从属性推断利益方向，需结合场景补写）",
            "benefit": benefit,
            "benefit_source": source,
            "benefit_evidence_needed": evidence or "需补充可核验的证据后再对外使用",
            "compliance_review": reviews,
            "evidence_needed": True,
        })

    audience = product.get("audience", "通勤人群")
    prio_keys = AUDIENCE_HINT.get(audience, [])
    cards.sort(key=lambda c: 0 if any(pk in c["feature"] for pk in prio_keys) else 1)

    return {
        "name": name,
        "audience": audience,
        "cards": cards,
        "missing_benefit": [c["feature"] for c in cards if c["benefit_source"] == "none"],
        "need_verified_copy": [c["feature"] for c in cards
                               if c["benefit_source"] == "direction_only"],
        "compliance_blocked": [{"feature": c["feature"], "reasons": c["compliance_review"]}
                               for c in cards if c["compliance_review"]],
    }


def _selftest() -> int:
    """内嵌回归自测：核心断言是「不注入成品利益点」「不做无依据竞品比较」。"""
    checks: list[tuple[str, bool, str]] = []

    def ck(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    p = {"name": "保温杯", "audience": "通勤人群",
         "attrs": {"容量": "500ml", "保温": "24小时", "材质": "316不锈钢"}}
    r = extract(p)
    joined = json.dumps(r, ensure_ascii=False)

    # 1) 不得出现 v1 注入的成品承诺文案
    ck("不注入「接触食品安全」声明", "接触食品安全" not in joined)
    ck("不注入「一天随时有热水」承诺", "随时有热水" not in joined)
    ck("不注入「一次装够」承诺", "一次装够" not in joined)

    # 2) 不得做无依据竞品比较
    ck("不含「优于同价位常见水平」", "优于同价位" not in joined)
    ck("advantage 为中性复述", all("为 " in c["advantage"] for c in r["cards"]))

    # 3) 利益点缺省为空，只给方向与所需证据
    ck("缺省不产出成品利益点", all(not c["benefit"] for c in r["cards"]))
    ck("缺省标 benefit_source=direction_only",
       all(c["benefit_source"] == "direction_only" for c in r["cards"]))
    ck("每条都给出所需证据", all(c["benefit_evidence_needed"] for c in r["cards"]))

    # 4) 调用方给文案时才透传，并标 caller
    r2 = extract(p, {"保温": "实测 24h 保温（附检测报告）"})
    ck("调用方文案被透传",
       any(c["benefit"] == "实测 24h 保温（附检测报告）" for c in r2["cards"]))
    ck("调用方文案标 benefit_source=caller",
       any(c["benefit_source"] == "caller" for c in r2["cards"]))
    ck("未提供文案的条目仍是 direction_only",
       any(c["benefit_source"] == "direction_only" for c in r2["cards"]))

    # 5) 合规敏感属性必须被拦出来
    #    注意：「材质：316不锈钢」本身**不构成**食品接触声明，不该被拦（避免误报刷屏），
    #    它由「所需证据」提示覆盖；只有文本里真的出现「食品级 / 可入口」才拦。
    mat = [c for c in r["cards"] if "材质" in c["feature"]][0]
    ck("材质属性不误报合规阻断", not mat["compliance_review"])
    ck("材质属性的所需证据含食品级资质要求",
       "食品级" in mat["benefit_evidence_needed"])
    r_food = extract({"name": "x", "attrs": {"适用": "食品级可入口"}})
    ck("明确食品接触文本被拦",
       "食品接触" in json.dumps(r_food["compliance_blocked"], ensure_ascii=False))
    r3 = extract({"name": "x", "attrs": {"功效": "抗菌消炎", "适用": "孕妇婴儿都能用"}})
    reasons = json.dumps(r3["compliance_blocked"], ensure_ascii=False)
    ck("功效宣称被拦", "功效宣称" in reasons)
    ck("特殊人群被拦", "特殊人群" in reasons)
    r4 = extract({"name": "x", "attrs": {"卖点": "100% 无损"}})
    ck("绝对化用语被拦",
       "绝对化用语" in json.dumps(r4["compliance_blocked"], ensure_ascii=False))

    # 6) 受众排序：命中优先关键词的卡片排前面
    ck("受众优先排序生效", "容量" in r["cards"][0]["feature"])

    # 7) 未命中任何关键词的属性仍能被结构化，不吞掉
    r5 = extract({"name": "x", "attrs": {"颜色": "雾灰"}})
    ck("未知属性不丢失", len(r5["cards"]) == 1)
    ck("未知属性标 missing_benefit", bool(r5["missing_benefit"]))

    fails = [(n, d) for n, ok, d in checks if not ok]
    for n, ok, d in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}" + (f" —— {d}" if not ok and d else ""))
    print(f"sellingpoint_extract 自测：{len(checks) - len(fails)}/{len(checks)} 通过")
    return 1 if fails else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()

    ap = argparse.ArgumentParser(description="卖点提炼（FAB）")
    ap.add_argument("--file", help="商品资料 JSON；缺省 stdin")
    ap.add_argument("--benefits", help="已核验的利益点文案 JSON，如 '{\"保温\":\"…\"}'")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    try:
        product = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        print(f"错误：输入不是合法 JSON —— {exc}", file=sys.stderr)
        return 2
    if not product:
        print("错误：缺少商品资料", file=sys.stderr)
        return 2

    benefits = {}
    if args.benefits:
        try:
            benefits = json.loads(args.benefits)
        except json.JSONDecodeError as exc:
            print(f"错误：--benefits 不是合法 JSON —— {exc}", file=sys.stderr)
            return 2

    r = extract(product, benefits)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"商品：{r['name']}　目标人群：{r['audience']}\n")
        for i, c in enumerate(r["cards"], 1):
            print(f"{i}. 特性　{c['feature']}")
            print(f"   优势　{c['advantage']}")
            print(f"   利益方向　{c['benefit_direction']}")
            if c["benefit"]:
                print(f"   利益点（调用方提供）　{c['benefit']}")
            print(f"   所需证据　{c['benefit_evidence_needed']}")
            if c["compliance_review"]:
                for why in c["compliance_review"]:
                    print(f"   ⛔ 合规待核　{why}")
        if r["need_verified_copy"]:
            print(f"\n⚠ 以下卖点只有方向、无可发布文案，需补证据后撰写："
                  f"{', '.join(r['need_verified_copy'])}")
        if r["missing_benefit"]:
            print(f"⚠ 以下属性未能推断利益方向，需结合场景补写：{', '.join(r['missing_benefit'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
