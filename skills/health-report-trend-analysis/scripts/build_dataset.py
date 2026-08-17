#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标准化数据集构建器
- 应用名称归一化（indicator_dict.NAME_MAP）与单位归一化（UNIT_MAP）
- 过滤小结混入脏数据、去重（同年同名）
- 参考范围解析、数值化容错（缺失值处理）
- 输出:
    data/dataset_std.json        本地完整版（含年龄/性别，不含证件/电话/医院）
    data/anonymized_dataset.json 脱敏版（仅指标数值+年份，可安全用于云端/分享）
"""
import json
import os
import re
from collections import OrderedDict
from indicator_dict import NAME_MAP, UNIT_MAP, INDICATOR_META, CATEGORY_OVERRIDE, parse_reference, parse_numeric, is_qualitative_value

BASE = os.environ.get("WORK_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_PATH = os.path.join(BASE, "data", "reports_raw.json")
STD_PATH = os.path.join(BASE, "data", "dataset_std.json")
ANON_PATH = os.path.join(BASE, "data", "anonymized_dataset.json")

# 需过滤的脏数据（小结段落混入）
DIRTY_PATTERNS = [
    r'^\(\d+\)',          # (1)xxx
    r'^\d+、',            # 8、xxx
    r'结论',              # 乙肝结论
]

def is_dirty(name):
    for p in DIRTY_PATTERNS:
        if re.match(p, name):
            return True
    return False

def norm_name(raw):
    """名称归一化，返回标准名；未收录的返回 None 并记录"""
    return NAME_MAP.get(raw)

def norm_unit(raw):
    if not raw:
        return ""
    return UNIT_MAP.get(raw, raw)

SECTION_CATEGORY_KEYWORDS = [
    ("血常规", "血常规"), ("尿常规", "尿常规"), ("肝功能", "肝功能"),
    ("肾功", "肾功能"), ("肾功能", "肾功能"), ("血脂", "血脂"),
    ("血糖", "血糖"), ("糖化", "血糖"), ("心肌酶", "心肌酶"),
    ("肌钙", "心肌酶"), ("甲状腺", "甲状腺"), ("乙肝", "乙肝"),
    ("电解质", "电解质"), ("肿瘤", "肿瘤标志物"), ("AFP", "肿瘤标志物"),
    ("癌胚", "肿瘤标志物"), ("PSA", "肿瘤标志物"), ("前列腺", "肿瘤标志物"),
    ("TK1", "肿瘤标志物"), ("鼻咽癌", "肿瘤标志物"), ("维生素", "维生素"),
    ("同型", "心血管"), ("半胱氨酸", "心血管"), ("血沉", "其他"), ("EB", "其他"),
]

def infer_category(std_name, section):
    """分类推断：INDICATOR_META > CATEGORY_OVERRIDE > section 关键词"""
    if std_name in INDICATOR_META:
        return INDICATOR_META[std_name]["category"]
    if std_name in CATEGORY_OVERRIDE:
        return CATEGORY_OVERRIDE[std_name][0]
    if section:
        for kw, cat in SECTION_CATEGORY_KEYWORDS:
            if kw in section:
                return cat
    return "其他"

def build():
    with open(RAW_PATH, encoding="utf-8") as f:
        reports = json.load(f)

    # 个人信息（脱敏：只保留年龄性别，用于解读；不含证件号/电话/单位/医院）
    person = {
        "anonymized": True,
        "sex": "男",
        "age_by_year": {r["year"]: r["age"] for r in reports},
        "note": "姓名、证件号、联系方式、地址、单位、医院等身份信息已脱敏，仅保留指标数值用于分析。"
    }

    # 按标准名聚合：key -> {"category", "unit", "display", "desc", "advice", "series": []}
    indicators = OrderedDict()
    unrecognized = {}   # raw_name -> years
    skipped_dirty = []

    for r in reports:
        year = r["year"]
        for it in r["lab_items"]:
            raw_name = it["name"]
            # 脏数据过滤
            if is_dirty(raw_name):
                skipped_dirty.append((year, raw_name))
                continue
            std_name = norm_name(raw_name)
            if std_name is None:
                unrecognized.setdefault(raw_name, []).append(year)
                continue
            meta = INDICATOR_META.get(std_name, {
                "category": infer_category(std_name, it["section"]),
                "unit": norm_unit(it["unit"]), "display": std_name,
                "desc": "", "advice": {}
            })
            # 用 override 的单位（若有）
            if std_name in CATEGORY_OVERRIDE and std_name not in INDICATOR_META:
                meta["unit"] = CATEGORY_OVERRIDE[std_name][1]
            key = std_name
            if key not in indicators:
                indicators[key] = {
                    "key": key,
                    "category": meta.get("category", "其他"),
                    "unit": meta.get("unit", norm_unit(it["unit"])),
                    "display": meta.get("display", std_name),
                    "desc": meta.get("desc", ""),
                    "advice": meta.get("advice", {}),
                    "series": [],
                }
            entry = {
                "year": year,
                "value_str": it["value"],
                "value": parse_numeric(it["value"]),
                "is_qualitative": is_qualitative_value(it["value"]),
                "flag": it["flag"] or "",
                "reference_str": it["reference"],
                "ref": parse_reference(it["reference"]),
                "section": it["section"],
                "raw_name": raw_name,
                "raw_unit": it["unit"],
                "unit": norm_unit(it["unit"]),
            }
            indicators[key]["series"].append(entry)

    # 按年份排序 series，并去重（同年同名同值保留一条）
    for key in indicators:
        series = indicators[key]["series"]
        seen = set()
        dedup = []
        for e in sorted(series, key=lambda x: x["year"]):
            sig = (e["year"], e["value_str"])
            if sig in seen:
                continue
            seen.add(sig)
            dedup.append(e)
        indicators[key]["series"] = dedup

    # 基础测量逐年
    measurements = {}
    for r in reports:
        year = r["year"]
        for k, v in r["measurements"].items():
            if k not in ("身高", "体重", "体重指数", "收缩压", "舒张压", "血压结论"):
                continue
            measurements.setdefault(k, []).append({
                "year": year,
                "value": parse_numeric(v) if v else None,
                "value_str": v,
                "flag": "",
            })
    # 补充 BMI 计算校验：若缺体重指数，用身高体重计算
    for r in reports:
        year = r["year"]
        h = parse_numeric(r["measurements"].get("身高"))
        w = parse_numeric(r["measurements"].get("体重"))
        if h and w:
            bmi = round(w / (h/100)**2, 2)
            # 若已有体重指数但差异大，以实测为准
            if "体重指数" in measurements and any(m["year"]==year for m in measurements["体重指数"]):
                continue
            measurements.setdefault("体重指数", []).append({"year": year, "value": bmi, "value_str": str(bmi), "flag": ""})

    # 检查结论 & 医生汇总
    exam_conclusions = {}
    summaries = {}
    for r in reports:
        year = r["year"]
        for k, v in r["exam_conclusions"].items():
            exam_conclusions.setdefault(k, {})[year] = v
        summaries[year] = r["summary"]

    dataset = {
        "generated_at": "2026-08-16",
        "schema_version": "1.0",
        "person": person,
        "years": sorted(set(r["year"] for r in reports)),
        "indicators": list(indicators.values()),
        "measurements": measurements,
        "exam_conclusions": exam_conclusions,
        "summaries": summaries,
        "unrecognized_names": {k: v for k, v in unrecognized.items()},
    }

    with open(STD_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    # ---- 脱敏版：仅指标数值 ----
    anon = {
        "anonymized": True,
        "note": "已脱敏：不含姓名、证件号、电话、地址、单位、医院等任何身份信息，仅保留指标数值与年份。",
        "years": dataset["years"],
        "indicators": [
            {
                "key": ind["key"],
                "category": ind["category"],
                "unit": ind["unit"],
                "display": ind["display"],
                "series": [{"year": e["year"], "value": e["value"], "value_str": e["value_str"]} for e in ind["series"]],
            }
            for ind in dataset["indicators"]
        ],
        "measurements": {
            k: [{"year": m["year"], "value": m["value"], "value_str": m["value_str"]} for m in v]
            for k, v in dataset["measurements"].items()
        },
    }
    with open(ANON_PATH, "w", encoding="utf-8") as f:
        json.dump(anon, f, ensure_ascii=False, indent=2)

    # 统计报告
    n_series = sum(len(ind["series"]) for ind in dataset["indicators"])
    print(f"标准指标数: {len(dataset['indicators'])}")
    print(f"指标-年度数据点: {n_series}")
    print(f"未识别指标名: {len(unrecognized)}")
    for k, v in list(unrecognized.items())[:20]:
        print(f"  {k} -> {v}")
    print(f"过滤脏数据: {len(skipped_dirty)}")
    print(f"基础测量: {list(dataset['measurements'].keys())}")
    print(f"已保存: {STD_PATH}")
    print(f"已保存(脱敏): {ANON_PATH}")

    # ---- 自动注入 OCR 数据 ----
    _inject_ocr(dataset)
    _inject_ocr_range(dataset, 2015, 2020)
    # 重新计算 years（包含 OCR 注入的年份）
    all_years = set()
    for ind in dataset["indicators"]:
        for e in ind["series"]:
            if e.get("value") is not None:
                all_years.add(e["year"])
    for k, v in dataset["measurements"].items():
        for m in v:
            if m.get("value") is not None:
                all_years.add(m["year"])
    dataset["years"] = sorted(all_years)
    # 重新写盘（含 OCR 与更新后的 years）
    with open(STD_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    with open(ANON_PATH, "w", encoding="utf-8") as f:
        anon = {
            "anonymized": True,
            "note": "已脱敏：不含姓名、证件号、电话、地址、单位、医院等任何身份信息。",
            "years": dataset["years"],
            "indicators": [{"key": i["key"], "category": i["category"], "unit": i["unit"],
                          "display": i["display"],
                          "series": [{"year": e["year"], "value": e["value"], "value_str": e["value_str"]}
                                      for e in i["series"]]} for i in dataset["indicators"]],
            "measurements": {k: [{"year": m["year"], "value": m["value"], "value_str": m["value_str"]} for m in v]
                             for k, v in dataset["measurements"].items()},
        }
        json.dump(anon, f, ensure_ascii=False, indent=2)
    # 移除 _inject_ocr 内部独立写盘（已统一）
    print(f"\n✓ dataset_std.json 已更新（含 OCR 数据）")
    print(f"✓ years 范围: {dataset['years']}")

    # 脱敏版自动校验（P1 整改：命中身份/机构信息即报错退出）
    verify_anonymized(ANON_PATH)


# OCR 注入（确保 build_dataset 之后不会被覆盖）
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

def _inject_ocr_range(dataset, start_year, end_year):
    """将 OCR 提取的多年度指标合并入数据集"""
    ocr_path = os.path.join(BASE, "data", "indicators_2015_2020.json")
    if not os.path.exists(ocr_path):
        return
    try:
        with open(ocr_path, encoding="utf-8") as f:
            ocr_all = json.load(f)
    except Exception:
        return
    total_accepted, total_rejected = 0, 0
    for year_str, ocr_items in ocr_all.items():
        year = int(year_str)
        if year < start_year or year > end_year:
            continue
        accepted, rejected = [], []
        for ocr in ocr_items:
            key = ocr["key"]
            val = ocr["value"]
            unit = ocr.get("unit", "")
            ind = next((x for x in dataset["indicators"] if x["key"] == key), None)
            if ind is None:
                rejected.append((key, "未收录")); continue
            rng = PLAUSIBLE_RANGES.get(key)
            if rng and (val < rng[0] or val > rng[1]):
                rejected.append((key, f"数值不合理: {rng}")); continue
            if any(e.get("year") == year for e in ind["series"]):
                rejected.append((key, f"{year} 已有数据")); continue
            ind_unit = ind.get("unit", "")
            if unit and ind_unit:
                a = unit.replace("μ", "u").lower()
                b = ind_unit.replace("μ", "u").lower()
                if a != b and not (a.replace("/l", "/L") == b.replace("/l", "/L")):
                    rejected.append((key, f"单位不匹配: {unit} vs {ind_unit}")); continue
            ref_lo = ocr.get("ref_lo")
            ref_hi = ocr.get("ref_hi")
            ref_str = f"{ref_lo}-{ref_hi}" if ref_lo is not None and ref_hi is not None else ""
            ind["series"].append({
                "year": year, "value_str": str(val), "value": val,
                "is_qualitative": False, "flag": "",
                "reference_str": ref_str,
                "ref": {"lo": ref_lo, "hi": ref_hi, "qualitative": False},
                "section": "(OCR提取)", "raw_name": key, "raw_unit": unit,
                "unit": ind_unit, "source": "ocr",
            })
            accepted.append(key)
        total_accepted += len(accepted)
        total_rejected += len(rejected)
        if accepted or rejected:
            print(f"\n[OCR 注入 {year}] 接受 {len(accepted)} 项: {', '.join(accepted[:8])}{'...' if len(accepted)>8 else ''}")
            if rejected:
                print(f"[OCR 注入 {year}] 拒绝 {len(rejected)} 项: {[(k, r) for k, r in rejected[:3]]}")
    return total_accepted, total_rejected

def _inject_ocr(dataset):
    """向后兼容：注入 2022 年 OCR 数据"""
    ocr_path = os.path.join(BASE, "data", "indicators_2022.json")
    if not os.path.exists(ocr_path):
        return
    try:
        with open(ocr_path, encoding="utf-8") as f:
            ocr_items = json.load(f)
    except Exception:
        return
    accepted, rejected = [], []
    for ocr in ocr_items:
        key = ocr["key"]
        val = ocr["value"]
        unit = ocr["unit"]
        ind = next((x for x in dataset["indicators"] if x["key"] == key), None)
        if ind is None:
            rejected.append((key, "未收录")); continue
        rng = PLAUSIBLE_RANGES.get(key)
        if rng and (val < rng[0] or val > rng[1]):
            rejected.append((key, f"数值不合理: {rng}")); continue
        # 跳过已存在同年的数据
        if any(e.get("year") == 2022 for e in ind["series"]):
            rejected.append((key, "2022 已有数据")); continue
        # 单位匹配（归一化）
        ind_unit = ind.get("unit", "")
        if unit and ind_unit:
            a = unit.replace("μ", "u").lower()
            b = ind_unit.replace("μ", "u").lower()
            if a != b and not (a.replace("/l", "/L") == b.replace("/l", "/L")):
                rejected.append((key, f"单位不匹配: {unit} vs {ind_unit}")); continue
        ind["series"].append({
            "year": 2022, "value_str": str(val), "value": val,
            "is_qualitative": False, "flag": "",
            "reference_str": ocr["reference"],
            "ref": {"lo": ocr["ref_lo"], "hi": ocr["ref_hi"], "qualitative": False},
            "section": "(OCR提取)", "raw_name": ocr["display"], "raw_unit": unit,
            "unit": ind_unit, "source": "ocr",
            "ocr_page": ocr["page"], "ocr_match_score": ocr["match_score"],
        })
        accepted.append(key)
    # 写盘逻辑统一移至 build() 末尾
    if accepted or rejected:
        print(f"\n[OCR 注入] 接受 {len(accepted)} 项: {', '.join(accepted[:8])}{'...' if len(accepted)>8 else ''}")
        if rejected:
            print(f"[OCR 注入] 拒绝 {len(rejected)} 项: {[(k, r) for k, r in rejected[:3]]}")


# ---- 脱敏版自动校验（P1 整改）----
IDENTITY_PATTERNS = [
    ("手机号", re.compile(r"1[3-9]\d{9}")),
    ("身份证号", re.compile(r"\d{17}[\dXx]")),
    ("邮箱地址", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("医院名称", re.compile(r"[\u4e00-\u9fa5]{2,12}(人民医院|中心医院|中医院|医院)")),
]


def verify_anonymized(path):
    """校验脱敏版数据不含身份/机构信息，命中即报错退出。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    problems = []
    for label, pattern in IDENTITY_PATTERNS:
        if pattern.search(text):
            problems.append(label)
    if problems:
        raise SystemExit(f"[FAIL] 脱敏版仍含疑似身份/机构信息: {', '.join(problems)}，请检查脱敏逻辑后重试")
    print("✓ 脱敏版自动校验通过：未发现手机号/身份证号/邮箱/医院名称等身份信息")


if __name__ == "__main__":
    build()
