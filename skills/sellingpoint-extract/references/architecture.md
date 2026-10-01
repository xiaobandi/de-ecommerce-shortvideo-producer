# 能力与字段速查

技能：`sellingpoint-extract`（L1 原子技能）

## 元信息

| 字段 | 值 |
|---|---|
| 技能 ID | `skill_sellingpoint_extract` |
| 目录 | `skills/sellingpoint-extract` |
| 复杂度 | S |
| 阶段 | P0 |
| 可见性 | platform_shared |
| 版本 | v1.0.0 |
| 许可 | MIT |
| 验证等级 | A（自带脚本 `sellingpoint_extract.py`，已用真实夹具执行并抓取 stdout/stderr/退出码） |

## 输入契约

- **必填**：商品资料（参数 / 描述）
- **可选**：目标人群
- **可选**：竞品对照
- **可选**：买家评论

## 脚本清单

| 脚本 | 用途 | 调用方式 |
|---|---|---|
| `scripts/sellingpoint_extract.py` | 确定性执行逻辑 | `python3 scripts/sellingpoint_extract.py` |

真实调用：

```bash
python3 scripts/sellingpoint_extract.py --file examples/input/product.json
```

## 质量门

- 每条卖点有明确利益点，非纯参数复述
- 参数原值引用，未四舍五入

## 已知陷阱

- 纯参数罗列不是卖点——'500ml'是特性，'装够一天水量'才是卖点
- 卖点过多等于没有卖点，同一渠道建议主推 3 个

## 边界

- 不做功效性承诺
