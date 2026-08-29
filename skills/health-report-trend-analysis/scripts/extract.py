#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR 指标提取器（参数化，取代按年份硬编码的 extract_2015_2020.py / extract_2022.py）

新增年份报告**不需要改代码**——只要 OCR 产物按 data/ocr_<年份>.json 命名落盘，
直接 `extract.py --year 2027` 即可。

两种提取策略（按输入 JSON 的顶层类型自动选择，也可 --strategy 强制）：
  abbr —— 输入为 dict {年份: [页]}：用英文缩写表(ALT/AST/WBC…)匹配 + 参考范围反推
  row  —— 输入为 list [页]：按 y 坐标聚合成视觉行，用「参考范围 + 单位」打分匹配

用法见 --help。
"""
import argparse
import json
import os
import sys

BASE = os.environ.get("WORK_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_DIR = os.path.join(BASE, "data")

YEAR_MIN, YEAR_MAX = 1900, 2100


# ---------------------------------------------------------------- 年份解析
def _to_int(text):
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return None


def parse_years(values):
    """解析年份：2022 / 2015,2017 / 2015-2020 / 多次传入。非法返回 None。"""
    years = []
    for raw in values:
        for part in str(raw).split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                lo_s, _, hi_s = part.partition("-")
                lo, hi = _to_int(lo_s), _to_int(hi_s)
                if lo is None or hi is None or lo > hi:
                    return None
                years.extend(range(lo, hi + 1))
            else:
                v = _to_int(part)
                if v is None:
                    return None
                years.append(v)
    years = sorted(set(years))
    if not years:
        return None
    if years[0] < YEAR_MIN or years[-1] > YEAR_MAX:
        return None
    return years


def spec_label(years):
    """年份集合 → 文件名片段：单年 2022 / 连续 2015_2020 / 离散 2015_2017_2019"""
    if not years:
        return ""
    if len(years) == 1:
        return str(years[0])
    if years == list(range(years[0], years[-1] + 1)):
        return f"{years[0]}_{years[-1]}"
    return "_".join(str(y) for y in years)


def find_ocr_json(data_dir, years, explicit=None):
    """定位 OCR 输入文件。

    查找顺序：--ocr-json > data/ocr_<spec>.json > data/ocr_<spec with dash>.json
             > 逐年份 data/ocr_<year>.json 合并
    返回 (ocr_json 路径或 None, 候选列表)
    """
    if explicit:
        return explicit, [explicit]
    spec = spec_label(years)
    candidates = []
    for name in (f"ocr_{spec}.json", f"ocr_{spec.replace('_', '-')}.json"):
        candidates.append(os.path.join(data_dir, name))
    for p in candidates:
        if os.path.isfile(p):
            return p, candidates
    # 逐年份文件（离散年份场景）
    per_year = [os.path.join(data_dir, f"ocr_{y}.json") for y in years]
    if all(os.path.isfile(p) for p in per_year):
        return "__per_year__", per_year
    return None, candidates + per_year


def load_per_year(paths_by_year):
    """合并多个单年份 OCR 文件 → dict {年份: [页]}（供 abbr 策略消费）"""
    merged = {}
    for year, p in paths_by_year.items():
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            merged[year] = data
        elif isinstance(data, dict):
            merged.update({int(k): v for k, v in data.items()})
    return merged


# ---------------------------------------------------------------- 策略 A：abbr（原 extract_2015_2020.py）
ABBR_MAP = {
    "ALT": "丙氨酸氨基转移酶(ALT)", "AST": "天门冬氨酸氨基转移酶(AST)",
    "TP": "总蛋白", "ALB": "白蛋白", "GLB": "球蛋白", "A/G": "白球比",
    "T-Bili": "总胆红素", "D-Bili": "直接胆红素", "I-Bili": "间接胆红素",
    "GGT": "γ-谷氨酰转移酶", "ALP": "碱性磷酸酶",
    "WBC": "白细胞计数", "RBC": "红细胞计数", "Hb": "血红蛋白", "HGB": "血红蛋白",
    "PLT": "血小板计数", "HCT": "红细胞比积", "MCV": "平均红细胞体积",
    "MCH": "平均红细胞血红蛋白量", "MCHC": "平均红细胞血红蛋白浓度",
    "MPV": "平均血小板体积", "PDW": "血小板分布宽度", "RDW": "红细胞分布宽度",
    "GLU": "空腹血糖", "GHb": "糖化血红蛋白", "HbA1c": "糖化血红蛋白",
    "TC": "总胆固醇", "TG": "甘油三酯", "HDL-C": "高密度脂蛋白胆固醇",
    "LDL-C": "低密度脂蛋白胆固醇", "LDL": "低密度脂蛋白胆固醇",
    "UA": "尿酸", "Cr": "肌酐", "BUN": "尿素氮",
    "TSH": "促甲状腺激素(TSH)", "FT3": "游离三碘甲状腺原氨酸(FT3)", "FT4": "游离甲状腺素(FT4)",
    "AFP": "甲胎蛋白(AFP)", "CEA": "癌胚抗原(CEA)", "CA199": "糖类抗原199(CA19-9)",
    "CA19-9": "糖类抗原199(CA19-9)", "CA125": "糖类抗原125(CA125)",
    "tPSA": "总前列腺特异性抗原(tPSA)", "TPSA": "总前列腺特异性抗原(tPSA)",
    "fPSA": "游离前列腺特异性抗原(fPSA)", "FPSA": "游离前列腺特异性抗原(fPSA)",
    "HCY": "同型半胱氨酸", "CYSC": "胱抑素C", "CysC": "胱抑素C",
    "CK": "肌酸激酶", "CK-MB": "肌酸激酶同工酶MB", "LDH": "乳酸脱氢酶",
    "HBDH": "α-羟基丁酸脱氢酶", "cTnI": "肌钙蛋白I",
    "K": "钾", "Na": "钠", "Cl": "氯", "Ca": "钙", "CO2": "二氧化碳",
    "VitD": "25-羟基维生素D", "VD": "25-羟基维生素D",
    "ESR": "血沉",
}


def build_indicator_refs(std, include_measurements=False):
    """从 dataset_std.json 建立「标准指标名 → unit + 参考范围列表」反向索引。

    include_measurements=True 时额外收录无固定范围的测量类指标（row 策略需要）。
    """
    refs = {}
    for ind in std.get("indicators", []):
        ranges = []
        for e in ind.get("series", []):
            if not e.get("is_qualitative") and e.get("value") is not None:
                ref = e.get("ref") or {}
                if ref.get("lo") is not None or ref.get("hi") is not None:
                    ranges.append((ref.get("lo"), ref.get("hi")))
        if ranges:
            refs[ind["key"]] = {"unit": ind.get("unit", ""), "refs": ranges,
                                "display": ind.get("display", ind["key"])}
    if include_measurements:
        for k, series in (std.get("measurements") or {}).items():
            if k in refs:
                continue
            if any(e.get("value") is not None for e in series):
                refs[k] = {"unit": "", "refs": [(None, None)],
                           "display": k, "is_measurement": True}
    return refs


def parse_ref_str(s):
    import re
    s = s.strip().replace(' ', '')
    s = re.sub(r'\.{2,}', '.', s)
    m = re.match(r'^([\d.]+)-([\d.]+)$', s)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except ValueError:
            return None, None
    m = re.match(r'^<([\d.]+)$', s)
    if m:
        try:
            return None, float(m.group(1))
        except ValueError:
            return None, None
    m = re.match(r'^>([\d.]+)$', s)
    if m:
        try:
            return float(m.group(1)), None
        except ValueError:
            return None, None
    return None, None


def match_indicator_by_ref(indicator_refs, lo, hi):
    """通过参考范围反推指标（容差 max(lo*0.15, 0.5)）"""
    for key, info in indicator_refs.items():
        for rlo, rhi in info["refs"]:
            match = False
            if lo is not None and rlo is not None and abs(lo - rlo) < max(rlo * 0.15, 0.5):
                if hi is not None and rhi is not None and abs(hi - rhi) < max(rhi * 0.15, 0.5):
                    match = True
                    break
                elif hi is None and rhi is None:
                    match = True
                    break
            elif lo is None and rlo is None:
                if hi is not None and rhi is not None and abs(hi - rhi) < max(rhi * 0.15, 0.5):
                    match = True
                    break
        if match:
            return key
    return None


def extract_abbr(pages, year, indicator_refs):
    """策略 A：缩写匹配 + 参考范围反推。pages 为单年份的页列表。"""
    import re
    items = []
    for page in pages:
        row_texts = []
        for line in page.get("lines", []):
            text, x0, y0 = line[0], line[1], line[2]
            row_texts.append((y0, x0, text))
        row_texts.sort(key=lambda t: (t[0], t[1]))

        # 1) 缩写识别
        for i, (y0, x0, text) in enumerate(row_texts):
            for abbr, key in ABBR_MAP.items():
                if not re.search(r'\b' + re.escape(abbr) + r'\b', text, re.I):
                    continue
                val, ref_lo, ref_hi, unit = None, None, None, ""
                for j in range(max(0, i - 3), min(len(row_texts), i + 4)):
                    if j == i:
                        continue
                    _, _, txt = row_texts[j]
                    nums = re.findall(r'(?<![\d.])\d+\.?\d*', txt)
                    if nums and val is None:
                        val = float(nums[-1])
                    ref_match = re.search(r'([\d.]+-[\d.]+|<[\d.]+|>[\d.]+)', txt)
                    if ref_match and ref_lo is None:
                        ref_lo, ref_hi = parse_ref_str(ref_match.group(1))
                    if not unit:
                        u = re.search(r'(mmol/L|umol/L|U/L|g/L|%|fL|pg|10\^9/L|10\^12/L|/L|μmol/L|mg/dL|ug/|ng/ml|U/m)',
                                      txt, re.I)
                        if u:
                            unit = u.group(1)
                if val is not None:
                    items.append({"year": year, "key": key, "value": val, "unit": unit,
                                  "ref_lo": ref_lo, "ref_hi": ref_hi,
                                  "source": "ocr", "method": "abbr"})

        # 2) 参考范围反推（跳过已命中缩写的行）
        for i, (y0, x0, text) in enumerate(row_texts):
            if any(re.search(r'\b' + re.escape(a) + r'\b', text, re.I) for a in ABBR_MAP):
                continue
            ref_match = re.search(r'([\d.]+-[\d.]+)', text)
            if not ref_match:
                continue
            ref_lo, ref_hi = parse_ref_str(ref_match.group(1))
            if ref_lo is None and ref_hi is None:
                continue
            val = None
            for j in range(max(0, i - 2), min(len(row_texts), i + 3)):
                if j == i:
                    continue
                _, _, txt = row_texts[j]
                nums = re.findall(r'(?<![\d.])\d+\.?\d*', txt)
                if nums:
                    val = float(nums[-1])
                    break
            if val is None:
                continue
            key = match_indicator_by_ref(indicator_refs, ref_lo, ref_hi)
            if key:
                items.append({"year": year, "key": key, "value": val, "unit": "",
                              "ref_lo": ref_lo, "ref_hi": ref_hi,
                              "source": "ocr", "method": "ref"})

    # 去重：同一 key 保留首个
    seen = {}
    for it in items:
        seen.setdefault(it["key"], it)
    return list(seen.values())


# ---------------------------------------------------------------- 策略 B：row（原 extract_2022.py）
def normalize_range(s):
    import re
    s = s.strip().replace(" ", "")
    m = re.match(r'^(\d+(?:\.\d+)?)\s*[-－—]\s*(\d+(?:\.\d+)?)$', s)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.match(r'^[<>]\s*(\d+(?:\.\d+)?)$', s)
    if m:
        return (None, float(m.group(1))) if s.startswith("<") else (float(m.group(1)), None)
    return None


def page_lines(lines, y_tol=18):
    """按 y 坐标聚合 OCR 文字为视觉行"""
    if not lines:
        return []
    items = sorted(lines, key=lambda l: (l[2], l[1]))
    rows, cur = [], [items[0]]
    for it in items[1:]:
        if abs(it[2] - cur[-1][2]) < y_tol:
            cur.append(it)
        else:
            cur.sort(key=lambda x: x[1])
            rows.append(cur)
            cur = [it]
    cur.sort(key=lambda x: x[1])
    rows.append(cur)
    merged = []
    for row in rows:
        row_y = sum(r[2] for r in row) / len(row)
        merged.append((row_y, [(r[1], r[0]) for r in row]))
    return merged


def row_text_and_features(row):
    import re
    full = " ".join(w for _, w in row)
    ref = None
    ref_m = re.search(r'(\d+(?:\.\d+)?)\s*[-－—]\s*(\d+(?:\.\d+)?)', full)
    if ref_m:
        ref = (float(ref_m.group(1)), float(ref_m.group(2)))
    unit = None
    for u in ["mmol/L", "mmol/l", "μmol/L", "umol/L", "g/L", "g/l",
              "10^9/L", "10^12/L", "U/L", "u/L", "u/l", "mIU/L", "pmol/L",
              "ng/mL", "ng/ml", "ug/L", "μg/L", "%", "fL", "pg", "mm/h",
              "nmol/L", "mol/L", "U/mL", "u/ml", "/uL", "/μL",
              "kU/L", "U/l", "mol/l"]:
        if u in full:
            unit = u
            break
    val_m = re.search(r'(-?\d+\.\d+|-?\d+)', full)
    return full, (float(val_m.group(1)) if val_m else None), ref, unit


def ref_matches(ocr_ref, indicator_refs, tol=0.05):
    if ocr_ref is None:
        return False
    lo, hi = ocr_ref
    for (ilo, ihi) in indicator_refs:
        if ilo is None or ihi is None:
            continue
        if abs(lo - ilo) <= max(0.5, abs(ilo) * tol) and abs(hi - ihi) <= max(0.5, abs(ihi) * tol):
            return True
    return False


def unit_matches(ocr_unit, indicator_unit):
    if not ocr_unit or not indicator_unit:
        return False
    a = ocr_unit.lower().replace(" ", "")
    b = indicator_unit.lower().replace(" ", "").replace("μ", "u")
    return a == b or a.replace("/l", "/L") == b.replace("/l", "/L")


def extract_row(pages, year, indicator_refs):
    """策略 B：视觉行聚合 + 「参考范围 × 单位」打分，每个指标只保留最高分。"""
    all_candidates = []
    for page_data in pages:
        pid = page_data.get("page")
        for row_y, row in page_lines(page_data.get("lines", [])):
            full, val, ref, unit = row_text_and_features(row)
            if val is None or ref is None:
                continue
            candidates = []
            for key, meta in indicator_refs.items():
                if not ref_matches(ref, meta["refs"]):
                    continue
                score = 1.0
                if unit and meta["unit"]:
                    score += 2.0 if unit_matches(unit, meta["unit"]) else -0.5
                candidates.append((score, key, meta["display"], meta.get("unit", "")))
            if not candidates:
                continue
            candidates.sort(key=lambda x: -x[0])
            score, key, display, matched_unit = candidates[0]
            all_candidates.append({
                "page": pid, "y": row_y, "full_text": full, "value": val,
                "ref_lo": ref[0], "ref_hi": ref[1], "unit": unit,
                "matched_key": key, "matched_display": display,
                "matched_unit": matched_unit, "match_score": score,
            })

    best_by_key = {}
    for c in all_candidates:
        k = c["matched_key"]
        if k not in best_by_key or c["match_score"] > best_by_key[k]["match_score"]:
            best_by_key[k] = c

    out_items = []
    for key, c in best_by_key.items():
        out_items.append({
            "key": key, "display": c["matched_display"], "value": c["value"],
            "unit": c["matched_unit"],
            "reference": f"{c['ref_lo']}-{c['ref_hi']}",
            "ref_lo": c["ref_lo"], "ref_hi": c["ref_hi"], "page": c["page"],
            "source_text": c["full_text"][:80], "match_score": c["match_score"],
            "source": "ocr", "year": year,
        })
    return out_items


# ---------------------------------------------------------------- 编排
def build_parser():
    parser = argparse.ArgumentParser(
        prog="extract.py",
        description="从 OCR 结果中提取体检指标（参数化，新增年份无需改代码）",
        epilog="""
示例:
  python3 scripts/extract.py --year 2022                # 读取 data/ocr_2022.json，输出 data/indicators_2022.json
  python3 scripts/extract.py --years 2015-2020          # 读取 data/ocr_2015_2020.json（缩写+参考范围反推）
  python3 scripts/extract.py --year 2015,2017,2019      # 合并多个单年份 OCR 文件
  python3 scripts/extract.py --year 2027 --ocr-json /tmp/ocr.json --out /tmp/ind.json
  python3 scripts/extract.py --year 2022 --strategy abbr # 强制使用缩写策略

策略自动判定：输入 JSON 顶层为 dict → abbr；为 list → row。
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--year", metavar="年份", action="append", default=None,
                        help="目标年份，支持 2022 / 2015,2017 / 2015-2020，可多次传入（必填）")
    parser.add_argument("--years", metavar="年份", action="append", default=None,
                        help="--year 的别名，语义完全相同")
    parser.add_argument("--data-dir", metavar="目录", default=None,
                        help=f"数据目录，默认 $WORK_DIR/data（当前: {DEFAULT_DATA_DIR}）")
    parser.add_argument("--dataset-json", metavar="文件", default=None,
                        help="标准数据集路径，用于建立参考范围反向索引（默认 <data-dir>/dataset_std.json）")
    parser.add_argument("--ocr-json", metavar="文件", default=None,
                        help="直接指定 OCR 输入文件，跳过按年份查找")
    parser.add_argument("--strategy", choices=["auto", "abbr", "row"], default="auto",
                        help="提取策略：auto=按输入 JSON 类型判定（默认）/ abbr=缩写+范围反推 / row=视觉行打分")
    parser.add_argument("--out", metavar="文件", default=None,
                        help="输出路径，默认按输入文件名推导（ocr_X.json → indicators_X.json）")
    parser.add_argument("--quiet", "-q", action="store_true", help="不打印逐项明细")
    return parser


def cli(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    raw_years = (args.year or []) + (args.years or [])
    if not raw_years:
        parser.error("必须用 --year/--years 指定年份（这是本脚本取代按年份硬编码脚本的关键）")
    years = parse_years(raw_years)
    if years is None:
        parser.error(f"年份取值非法: {raw_years}（需为 {YEAR_MIN}-{YEAR_MAX} 之间，"
                     f"支持 2022、2015,2017、2015-2020）")

    data_dir = args.data_dir or DEFAULT_DATA_DIR
    if not os.path.isdir(data_dir):
        parser.error(f"--data-dir 目录不存在: {data_dir}")

    ocr_path, tried = find_ocr_json(data_dir, years, args.ocr_json)
    if ocr_path is None:
        print(f"[错误] 未找到 OCR 输入文件，已尝试：")
        for p in tried:
            print(f"       - {p}")
        print("       请先跑 vision_ocr.py 生成 OCR 结果，或用 --ocr-json 直接指定")
        return 1

    # 载入 OCR 数据
    try:
        if ocr_path == "__per_year__":
            ocr_data = load_per_year({y: p for y, p in zip(years, tried)})
        else:
            with open(ocr_path, encoding="utf-8") as f:
                ocr_data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[错误] OCR 文件读取失败: {e}")
        return 1

    # 载入标准数据集（参考范围反向索引）
    std_path = args.dataset_json or os.path.join(data_dir, "dataset_std.json")
    if not os.path.isfile(std_path):
        print(f"[错误] 缺少标准数据集: {std_path}（请先跑 build_dataset.py，或用 --dataset-json 指定）")
        return 1
    try:
        with open(std_path, encoding="utf-8") as f:
            std = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[错误] 标准数据集读取失败: {e}")
        return 1

    # 策略判定
    strategy = args.strategy
    if strategy == "auto":
        strategy = "abbr" if isinstance(ocr_data, dict) else "row"
    if strategy == "abbr" and not isinstance(ocr_data, dict):
        ocr_data = {years[0]: ocr_data}
    if strategy == "row" and isinstance(ocr_data, dict):
        if len(years) != 1:
            parser.error(f"row 策略只支持单年份，当前指定了 {len(years)} 个（{years}）；"
                         f"多年份请用 abbr 策略，或分批执行")
        ocr_data = ocr_data.get(str(years[0])) or ocr_data.get(years[0])
        if ocr_data is None:
            print(f"[错误] OCR 数据中不含 {years[0]} 年的内容")
            return 1

    indicator_refs = build_indicator_refs(std, include_measurements=(strategy == "row"))

    # 执行
    if strategy == "abbr":
        result = {}
        for year_key in sorted(ocr_data.keys(), key=lambda k: int(k)):
            year = int(year_key)
            if years and year not in years:
                continue
            result[year] = extract_abbr(ocr_data[year_key], year, indicator_refs)
            if not args.quiet:
                print(f"{year}: 提取 {len(result[year])} 项")
                for it in result[year][:12]:
                    ref = (f"{it['ref_lo']}-{it['ref_hi']}"
                           if it['ref_lo'] is not None or it['ref_hi'] is not None else "")
                    print(f"  [{it['method']}] {it['key']}: {it['value']} {it['unit']} (ref {ref})")
                if len(result[year]) > 12:
                    print(f"  ... 等共 {len(result[year])} 项")
    else:
        items = extract_row(ocr_data, years[0], indicator_refs)
        result = items
        if not args.quiet:
            print(f"匹配到 {len(items)} 个 {years[0]} 年指标")
            for it in sorted(items, key=lambda x: -x["match_score"]):
                print(f"  [{it['page']}页] {it['key']}: {it['value']} {it['unit']} "
                      f"| 参考 {it['reference']} | 分数 {it['match_score']:.1f}")

    # 输出
    if args.out:
        out_path = args.out
    elif ocr_path == "__per_year__":
        out_path = os.path.join(data_dir, f"indicators_{spec_label(years)}.json")
    else:
        base = os.path.basename(ocr_path)
        rest = base[len("ocr_"):] if base.startswith("ocr_") else base
        out_path = os.path.join(data_dir, f"indicators_{rest}")

    out_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n已保存: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(cli())
