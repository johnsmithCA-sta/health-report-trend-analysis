#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2022 报告 OCR 数字驱动指标提取
策略：
1. 聚合 OCR 文字为视觉行（y 容差 <15px）
2. 识别化验行（含数值 + 参考范围 + 单位）
3. 通过参考范围字符串反推所属指标
4. 用 2023-2026 历史范围匹配 + 数值+单位特征
5. 输出 2022 指标数据，标注 source="ocr"
"""
import json, re, os
from collections import defaultdict

BASE = os.environ.get("WORK_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR_PATH = os.path.join(BASE, "data", "ocr_2022.json")
STD_PATH = os.path.join(BASE, "data", "dataset_std.json")
OUT_PATH = os.path.join(BASE, "data", "indicators_2022.json")

with open(OCR_PATH, encoding="utf-8") as f:
    ocr = json.load(f)
with open(STD_PATH, encoding="utf-8") as f:
    std = json.load(f)

# 收集所有指标的参考范围（来自 2023-2026）建立反向索引
# key: 标准名 → unit + (lo, hi) 列表
INDICATOR_REFS = {}
for ind in std["indicators"]:
    refs = []
    units = set()
    for e in ind["series"]:
        if not e.get("is_qualitative") and e["value"] is not None:
            ref = e["ref"]
            if ref.get("lo") is not None or ref.get("hi") is not None:
                refs.append((ref.get("lo"), ref.get("hi")))
            units.add(e["unit"])
    if refs:
        INDICATOR_REFS[ind["key"]] = {
            "unit": ind["unit"],
            "refs": refs,
            "display": ind["display"],
        }

# 测量指标
for k, series in std["measurements"].items():
    if k in INDICATOR_REFS:
        continue
    vals = [e for e in series if e.get("value") is not None]
    if vals:
        INDICATOR_REFS[k] = {
            "unit": "",
            "refs": [(None, None)],  # 测量无固定范围
            "display": k,
            "is_measurement": True,
        }

def normalize_range(s):
    """解析参考范围字符串，返回 (lo, hi) 或 None"""
    s = s.strip().replace(" ", "")
    # 范围 X-X 或 X．X-X．X
    m = re.match(r'^(\d+(?:\.\d+)?)\s*[-－—]\s*(\d+(?:\.\d+)?)$', s)
    if m:
        return float(m.group(1)), float(m.group(2))
    # 小于/大于
    m = re.match(r'^[<>]\s*(\d+(?:\.\d+)?)$', s)
    if m:
        return (None, float(m.group(1))) if s.startswith("<") else (float(m.group(1)), None)
    return None

def page_lines(lines, y_tol=18):
    """按 y 坐标聚合 OCR 文字为视觉行（页内每行是表格行）"""
    if not lines:
        return []
    items = sorted(lines, key=lambda l: (l[2], l[1]))  # 按 y0, x0
    rows = []
    cur = [items[0]]
    for it in items[1:]:
        if abs(it[2] - cur[-1][2]) < y_tol:
            cur.append(it)
        else:
            cur.sort(key=lambda x: x[1])
            rows.append(cur)
            cur = [it]
    cur.sort(key=lambda x: x[1])
    rows.append(cur)
    # 合并为行：每个词为 (x, text)
    merged = []
    for row in rows:
        row_y = sum(r[2] for r in row) / len(row)
        words = [(r[1], r[0]) for r in row]
        merged.append((row_y, words))
    return merged

def row_text_and_features(row):
    """从一行提取：完整文本、值、参考范围、单位"""
    full = " ".join(w for _, w in row)
    # 提取参考范围
    ref_m = re.search(r'(\d+(?:\.\d+)?)\s*[-－—]\s*(\d+(?:\.\d+)?)', full)
    ref = None
    if ref_m:
        ref = (float(ref_m.group(1)), float(ref_m.group(2)))
    # 提取单位
    unit = None
    for u in ["mmol/L", "mmol/l", "μmol/L", "umol/L", "g/L", "g/l",
              "10^9/L", "10^12/L", "U/L", "u/L", "u/l", "mIU/L", "pmol/L",
              "ng/mL", "ng/ml", "ug/L", "μg/L", "%", "fL", "pg", "mm/h",
              "nmol/L", "mol/L", "U/mL", "u/ml", "ng/mL", "/uL", "/μL",
              "kU/L", "U/l", "mol/l"]:
        if u in full:
            unit = u
            break
    # 提取数值（第一个数字）
    val_m = re.search(r'(-?\d+\.\d+|-?\d+)', full)
    val = float(val_m.group(1)) if val_m else None
    return full, val, ref, unit

def ref_matches(ocr_ref, indicator_refs, tol=0.05):
    """OCR 参考范围是否匹配某指标的参考范围（容忍小差异）"""
    if ocr_ref is None:
        return False
    lo, hi = ocr_ref
    for (ilo, ihi) in indicator_refs:
        if ilo is None or ihi is None:
            continue
        # 允许 5% 或 0.5 误差
        ok = abs(lo - ilo) <= max(0.5, abs(ilo)*tol) and abs(hi - ihi) <= max(0.5, abs(ihi)*tol)
        if ok:
            return True
    return False

def unit_matches(ocr_unit, indicator_unit):
    """单位匹配（归一化后）"""
    if not ocr_unit or not indicator_unit:
        return False
    a = ocr_unit.lower().replace(" ", "")
    b = indicator_unit.lower().replace(" ", "").replace("μ", "u")
    return a == b or a.replace("/l", "/L") == b.replace("/l", "/L")

# 主流程
all_candidates = []
for page_data in ocr:
    pid = page_data["page"]
    rows = page_lines(page_data["lines"])
    for row_y, row in rows:
        full, val, ref, unit = row_text_and_features(row)
        if val is None or ref is None:
            continue
        # 候选：参考范围匹配
        candidates = []
        for key, meta in INDICATOR_REFS.items():
            if not ref_matches(ref, meta["refs"]):
                continue
            score = 1.0
            if unit and meta["unit"]:
                if unit_matches(unit, meta["unit"]):
                    score += 2.0
                else:
                    score -= 0.5
            candidates.append((score, key, meta["display"], meta.get("unit","")))
        if not candidates:
            continue
        candidates.sort(key=lambda x: -x[0])
        top = candidates[0]
        all_candidates.append({
            "page": pid,
            "y": row_y,
            "full_text": full,
            "value": val,
            "ref_lo": ref[0],
            "ref_hi": ref[1],
            "unit": unit,
            "matched_key": top[1],
            "matched_display": top[2],
            "matched_unit": top[3],
            "match_score": top[0],
        })

# 每个指标仅保留分数最高的（避免同一指标多次匹配）
best_by_key = {}
for c in all_candidates:
    k = c["matched_key"]
    if k not in best_by_key or c["match_score"] > best_by_key[k]["match_score"]:
        best_by_key[k] = c

# 输出
out_items = []
for key, c in best_by_key.items():
    out_items.append({
        "key": key,
        "display": c["matched_display"],
        "value": c["value"],
        "unit": c["matched_unit"],
        "reference": f"{c['ref_lo']}-{c['ref_hi']}",
        "ref_lo": c["ref_lo"],
        "ref_hi": c["ref_hi"],
        "page": c["page"],
        "source_text": c["full_text"][:80],
        "match_score": c["match_score"],
        "source": "ocr",
        "year": 2022,
    })

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(out_items, f, ensure_ascii=False, indent=2)

print(f"已保存: {OUT_PATH}")
print(f"匹配到 {len(out_items)} 个 2022 年指标")
for it in sorted(out_items, key=lambda x: -x["match_score"]):
    print(f"  [{it['page']}页] {it['key']}: {it['value']} {it['unit']} | 参考 {it['reference']} | 分数 {it['match_score']:.1f}")