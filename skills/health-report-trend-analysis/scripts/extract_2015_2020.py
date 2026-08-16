#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2015-2020 报告 OCR 智能提取 v2
策略：
1. 识别英文缩写/代号（ALT、AST、TP、ALB 等）→ 直接映射指标
2. 参考范围反推（无缩写时）
3. 基于 y 坐标近邻配对数值与参考范围
"""
import json, re, os
from collections import defaultdict

BASE = os.environ.get("WORK_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OCR_PATH = os.path.join(BASE, "data", "ocr_2015_2020.json")
STD_PATH = os.path.join(BASE, "data", "dataset_std.json")
OUT_PATH = os.path.join(BASE, "data", "indicators_2015_2020.json")

if not os.path.exists(OCR_PATH):
    print(f"[跳过] {OCR_PATH} 不存在")
    exit(0)

with open(OCR_PATH, encoding="utf-8") as f:
    ocr_all = json.load(f)
with open(STD_PATH, encoding="utf-8") as f:
    std = json.load(f)

# 缩写映射
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

# 参考范围反向索引
INDICATOR_REFS = {}
for ind in std["indicators"]:
    refs = []
    for e in ind["series"]:
        if not e.get("is_qualitative") and e["value"] is not None:
            ref = e["ref"]
            if ref.get("lo") is not None or ref.get("hi") is not None:
                refs.append((ref.get("lo"), ref.get("hi")))
    if refs:
        INDICATOR_REFS[ind["key"]] = {"unit": ind["unit"], "refs": refs}

PLAUSIBLE_RANGES = {
    "空腹血糖": (2, 30), "糖化血红蛋白": (3, 20),
    "总胆固醇": (1, 15), "甘油三酯": (0.1, 30),
    "低密度脂蛋白胆固醇": (0.1, 10), "高密度脂蛋白胆固醇": (0.1, 4),
    "尿酸": (50, 1000), "肌酐": (10, 1000), "尿素氮": (0.5, 30),
    "丙氨酸氨基转移酶(ALT)": (1, 1000), "天门冬氨酸氨基转移酶(AST)": (1, 1000),
    "γ-谷氨酰转移酶": (1, 1000), "碱性磷酸酶": (10, 1500),
    "总蛋白": (20, 120), "白蛋白": (10, 70), "球蛋白": (5, 60),
    "总胆红素": (0.5, 500), "直接胆红素": (0, 200), "间接胆红素": (0, 200),
    "白细胞计数": (0.5, 50), "血红蛋白": (30, 250), "红细胞计数": (1, 10),
    "血小板计数": (5, 1500), "红细胞比积": (10, 70),
    "平均红细胞体积": (50, 130), "平均红细胞血红蛋白量": (10, 60),
    "平均红细胞血红蛋白浓度": (200, 450), "平均血小板体积": (5, 25),
    "中性粒细胞百分比": (0, 100), "淋巴细胞百分比": (0, 100),
    "单核细胞百分比": (0, 30), "嗜酸性粒细胞百分比": (0, 30), "嗜碱性粒细胞百分比": (0, 10),
    "中性粒细胞绝对值": (0, 50), "淋巴细胞绝对值": (0, 20),
    "单核细胞绝对值": (0, 5), "嗜酸性粒细胞绝对值": (0, 5), "嗜碱性粒细胞绝对值": (0, 1),
    "血小板压积": (0, 2), "血小板分布宽度": (0, 30), "红细胞分布宽度": (0, 30),
    "肌酸激酶": (5, 5000), "肌酸激酶同工酶MB": (0, 100), "乳酸脱氢酶": (50, 2000),
    "α-羟基丁酸脱氢酶": (10, 1000), "肌钙蛋白I": (0, 100),
    "促甲状腺激素(TSH)": (0.01, 100), "游离甲状腺素(FT4)": (1, 100),
    "游离三碘甲状腺原氨酸(FT3)": (1, 30),
    "钾": (1, 10), "钠": (100, 200), "氯": (70, 130), "钙": (1.5, 5), "二氧化碳": (10, 50),
    "25-羟基维生素D": (5, 300), "同型半胱氨酸": (2, 100),
    "甲胎蛋白(AFP)": (0, 1000), "癌胚抗原(CEA)": (0, 500),
    "糖类抗原199(CA19-9)": (0, 1000), "总前列腺特异性抗原(tPSA)": (0, 100),
    "游离前列腺特异性抗原(fPSA)": (0, 50),
    "尿沉渣白细胞": (0, 100), "尿沉渣红细胞": (0, 5000), "尿沉渣细菌": (0, 5000),
    "尿酸碱度": (4, 9), "尿比重": (1, 1.05),
}

def parse_ref_str(s):
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

def match_indicator_by_ref(lo, hi):
    """通过参考范围匹配指标"""
    for key, info in INDICATOR_REFS.items():
        for rlo, rhi in info["refs"]:
            match = False
            if lo is not None and rlo is not None and abs(lo - rlo) < max(rlo*0.15, 0.5):
                if hi is not None and rhi is not None and abs(hi - rhi) < max(rhi*0.15, 0.5):
                    match = True
                    break
                elif hi is None and rhi is None:
                    match = True
                    break
            elif lo is None and rlo is None:
                if hi is not None and rhi is not None and abs(hi - rhi) < max(rhi*0.15, 0.5):
                    match = True
                    break
        if match:
            return key
    return None

def extract_page(pages, year):
    """提取一页中的所有指标"""
    items = []
    for page in pages:
        lines = page["lines"]
        # 构建行列表（含坐标）
        row_texts = []
        for line in lines:
            text, x0, y0, x1, y1 = line
            row_texts.append((y0, x0, text))
        row_texts.sort(key=lambda t: (t[0], t[1]))
        
        # 1. 基于缩写识别
        for i, (y0, x0, text) in enumerate(row_texts):
            for abbr, key in ABBR_MAP.items():
                # 缩写作为独立词匹配
                if re.search(r'\b' + re.escape(abbr) + r'\b', text, re.I):
                    # 找附近 3 行内的数值和参考范围
                    val = None
                    ref_lo, ref_hi = None, None
                    unit = ""
                    for j in range(max(0, i-3), min(len(row_texts), i+4)):
                        if j == i:
                            continue
                        _, _, txt = row_texts[j]
                        # 找数值
                        nums = re.findall(r'(?<![\d.])\d+\.?\d*', txt)
                        if nums and val is None:
                            val = float(nums[-1])
                        # 找参考范围
                        ref_match = re.search(r'([\d.]+-[\d.]+|<[\d.]+|>[\d.]+)', txt)
                        if ref_match and ref_lo is None:
                            ref_lo, ref_hi = parse_ref_str(ref_match.group(1))
                        # 找单位
                        u = re.search(r'(mmol/L|umol/L|U/L|g/L|%|fL|pg|10\^9/L|10\^12/L|/L|μmol/L|mg/dL|ug/|ng/ml|U/m)', txt, re.I)
                        if u and not unit:
                            unit = u.group(1)
                    if val is not None:
                        items.append({
                            "year": year, "key": key, "value": val,
                            "unit": unit, "ref_lo": ref_lo, "ref_hi": ref_hi,
                            "source": "ocr", "method": "abbr"
                        })
        
        # 2. 基于参考范围反推（找没有缩写匹配到的行）
        for i, (y0, x0, text) in enumerate(row_texts):
            # 如果这行已经被缩写匹配过，跳过
            skip = False
            for abbr, _ in ABBR_MAP.items():
                if re.search(r'\b' + re.escape(abbr) + r'\b', text, re.I):
                    skip = True
                    break
            if skip:
                continue
            # 找参考范围
            ref_match = re.search(r'([\d.]+-[\d.]+)', text)
            if not ref_match:
                continue
            ref_lo, ref_hi = parse_ref_str(ref_match.group(1))
            if ref_lo is None and ref_hi is None:
                continue
            # 找附近数值
            val = None
            for j in range(max(0, i-2), min(len(row_texts), i+3)):
                if j == i:
                    continue
                _, _, txt = row_texts[j]
                nums = re.findall(r'(?<![\d.])\d+\.?\d*', txt)
                if nums:
                    val = float(nums[-1])
                    break
            if val is None:
                continue
            key = match_indicator_by_ref(ref_lo, ref_hi)
            if key:
                items.append({
                    "year": year, "key": key, "value": val,
                    "unit": "", "ref_lo": ref_lo, "ref_hi": ref_hi,
                    "source": "ocr", "method": "ref"
                })
    
    # 去重
    seen = {}
    for it in items:
        k = it["key"]
        if k not in seen:
            seen[k] = it
    return list(seen.values())

# 处理所有年份
all_items = {}
for year_str in sorted(ocr_all.keys(), key=int):
    year = int(year_str)
    items = extract_page(ocr_all[year_str], year)
    all_items[year] = items
    print(f"{year}: 提取 {len(items)} 项")
    for it in items[:12]:
        ref = f"{it['ref_lo']}-{it['ref_hi']}" if it['ref_lo'] or it['ref_hi'] else ""
        print(f"  [{it['method']}] {it['key']}: {it['value']} {it['unit']} (ref {ref})")
    if len(items) > 12:
        print(f"  ... 等共 {len(items)} 项")

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(all_items, f, ensure_ascii=False, indent=2)
print(f"\n已保存: {OUT_PATH}")
