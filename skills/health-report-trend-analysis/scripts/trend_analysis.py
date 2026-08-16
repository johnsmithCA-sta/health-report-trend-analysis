#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
趋势比对分析器
- 对每个数值型指标：逐年判定是否超出参考范围（用当年报告自带范围，保证口径一致）
- 相邻年显著升降检测（幅度 + 百分比）
- 连续多年趋势判定（持续上升/持续下降/先升后降/波动等）
- 输出 data/trend_analysis.json
"""
import json
import os
from collections import OrderedDict
from indicator_dict import INDICATOR_META

BASE = os.environ.get("WORK_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STD_PATH = os.path.join(BASE, "data", "dataset_std.json")
OUT_PATH = os.path.join(BASE, "data", "trend_analysis.json")

# 趋势聚焦年份（仅判断这几年的整体趋势）
TREND_FOCUS_YEARS = [2024, 2025, 2026]

# 显著变化阈值：相对变化 ≥20% 且绝对变化 ≥ 参考范围宽度的 10%（防止噪声）
PCT_THRESHOLD = 0.20

# 趋势方向与健康关系
# INVERSE：值越低越好（下降为趋好）
INVERSE_INDICATORS = {
    "总胆固醇", "甘油三酯", "低密度脂蛋白胆固醇", "非高密度脂蛋白胆固醇",
    "空腹血糖", "糖化血红蛋白", "果糖胺",
    "尿酸", "同型半胱氨酸",
    "丙氨酸氨基转移酶(ALT)", "天门冬氨酸氨基转移酶(AST)", "γ-谷氨酰转移酶",
    "碱性磷酸酶", "总胆红素", "直接胆红素", "间接胆红素",
    "胆碱酯酶",
    "尿沉渣红细胞", "尿糖", "尿酮体", "尿蛋白", "尿胆红素",
    "尿白细胞", "尿沉渣白细胞", "尿沉渣细菌",
    "体重指数", "体重", "收缩压", "舒张压",
    "嗜碱性粒细胞百分比", "嗜碱性粒细胞绝对值",
    "淋巴细胞绝对值", "血小板压积",
    "尿比重",
}
# POSITIVE：值越高越好（上升为趋好）
POSITIVE_INDICATORS = {
    "高密度脂蛋白胆固醇",
    "血红蛋白", "红细胞计数", "红细胞比积",
    "中性粒细胞绝对值", "中性粒细胞百分比",
    "血小板计数",
    "25-羟基维生素D",
}


def judge_good_direction(key, total_change_pct, first_status, last_status):
    """判定指标整体趋势的健康方向：
    返回 '趋好' / '趋坏' / '中性' / '复杂'
    优先级：参考范围状态变化 > 方向判定
    """
    # 优先依据：首末参考范围状态变化
    if first_status and last_status:
        # 首年异常 → 末年正常 = 趋好
        if first_status in ("偏高", "偏低") and last_status == "正常":
            return "趋好"
        # 首年正常 → 末年异常 = 趋坏
        if first_status == "正常" and last_status in ("偏高", "偏低"):
            return "趋坏"
        # 异常→异常但向参考范围收敛（更接近正常）
        # 异常→异常但偏离参考范围
        if first_status == "偏高" and last_status == "偏高":
            # 高位继续升 → 趋坏；下降但仍偏高 → 趋好
            if total_change_pct is None:
                return "复杂"
            return "趋坏" if total_change_pct > 5 else "趋好"
        if first_status == "偏低" and last_status == "偏低":
            if total_change_pct is None:
                return "复杂"
            return "趋坏" if total_change_pct < -5 else "趋好"
        # 首末都正常但有显著变化，根据方向判定
    if total_change_pct is None or abs(total_change_pct) < 5:
        return "中性"
    is_inverse = key in INVERSE_INDICATORS
    is_positive = key in POSITIVE_INDICATORS
    if not is_inverse and not is_positive:
        return "复杂"
    if is_inverse:
        # 下降好
        if total_change_pct < -5:
            return "趋好"
        if total_change_pct > 5:
            return "趋坏"
    else:  # positive
        if total_change_pct > 5:
            return "趋好"
        if total_change_pct < -5:
            return "趋坏"
    return "中性"


def judge_change_good(key, change_pct):
    """判定单次（相邻年）变化对健康的影响方向"""
    if change_pct is None:
        return None
    if key in INVERSE_INDICATORS:
        if change_pct <= -10: return "趋好"
        if change_pct >= 10: return "趋坏"
    elif key in POSITIVE_INDICATORS:
        if change_pct >= 10: return "趋好"
        if change_pct <= -10: return "趋坏"
    return None

def judge_status(value, ref):
    """依据当年参考范围判定状态：normal / high / low / qualitative / unknown"""
    if value is None:
        return "缺失"
    if ref.get("qualitative"):
        return "定性"
    lo, hi = ref.get("lo"), ref.get("hi")
    if lo is None and hi is None:
        return "无范围"
    if lo is not None and hi is not None:
        if value < lo:
            return "偏低"
        if value > hi:
            return "偏高"
        return "正常"
    if lo is not None and value < lo:
        return "偏低"
    if hi is not None and value > hi:
        return "偏高"
    return "正常"

def direction_text(v1, v2):
    if v2 > v1:
        return "上升"
    if v2 < v1:
        return "下降"
    return "持平"

def analyze():
    with open(STD_PATH, encoding="utf-8") as f:
        ds = json.load(f)

    years = ds["years"]
    trend_items = []
    measurement_items = []

    # ---- 化验指标 ----
    for ind in ds["indicators"]:
        # 区分 OCR 数据与正常数据：OCR 仅用于显示，不参与显著变化/趋势判定
        all_series = [e for e in ind["series"] if not e["is_qualitative"] and e["value"] is not None]
        ocr_series = [e for e in all_series if e.get("source") == "ocr"]
        series = [e for e in all_series if e.get("source") != "ocr"]
        if len(series) < 2:
            continue
        series.sort(key=lambda e: e["year"])
        # 状态判定
        points = []
        for e in series:
            status = judge_status(e["value"], e["ref"])
            flag = ""
            if status == "偏高":
                flag = "↑"
            elif status == "偏低":
                flag = "↓"
            points.append({
                "year": e["year"],
                "value": e["value"],
                "status": status,
                "flag": flag,
                "ref_str": e["reference_str"],
                "ref_lo": e["ref"].get("lo"),
                "ref_hi": e["ref"].get("hi"),
            })
        # 相邻年变化（含健康方向判定）
        changes = []
        for i in range(len(series) - 1):
            e1, e2 = series[i], series[i+1]
            v1, v2 = e1["value"], e2["value"]
            delta = round(v2 - v1, 4)
            pct = round(delta / abs(v1) * 100, 1) if v1 else None
            # 显著性：相对变化≥20%
            ref = e1["ref"] or e2["ref"]
            span = (ref.get("hi") or 0) - (ref.get("lo") or 0) if ref.get("lo") is not None or ref.get("hi") is not None else None
            significant = False
            if pct is not None:
                significant = abs(pct) >= PCT_THRESHOLD * 100
                if span and span > 0 and abs(delta) >= span * 0.3:
                    significant = True
            changes.append({
                "from_year": e1["year"],
                "to_year": e2["year"],
                "from": v1,
                "to": v2,
                "delta": delta,
                "pct": pct,
                "direction": direction_text(v1, v2),
                "significant": significant,
                "good_direction": judge_change_good(ind["key"], pct),
            })
        # 趋势判定（仅基于 TREND_FOCUS_YEARS）
        focus_points = [p for p in points if p["year"] in TREND_FOCUS_YEARS]
        focus_values = [p["value"] for p in focus_points]
        focus_diffs = [focus_values[i+1] - focus_values[i] for i in range(len(focus_values)-1)]
        if len(focus_diffs) >= 2:
            if all(d > 0 for d in focus_diffs):
                trend = "持续上升"
            elif all(d < 0 for d in focus_diffs):
                trend = "持续下降"
            elif focus_diffs[0] > 0 and focus_diffs[-1] < 0:
                trend = "先升后降"
            elif focus_diffs[0] < 0 and focus_diffs[-1] > 0:
                trend = "先降后升"
            else:
                trend = "波动"
        elif len(focus_diffs) == 1:
            trend = "上升" if focus_diffs[0] > 0 else ("下降" if focus_diffs[0] < 0 else "持平")
        else:
            trend = "—"
        # 首末对比（仅基于 TREND_FOCUS_YEARS）
        if len(focus_points) >= 2:
            first, last = focus_points[0]["value"], focus_points[-1]["value"]
            total_pct = round((last - first) / abs(first) * 100, 1) if first else None
            first_status, last_status = focus_points[0]["status"], focus_points[-1]["status"]
        elif len(focus_points) == 1:
            first = last = focus_points[0]["value"]
            total_pct = None
            first_status = last_status = focus_points[0]["status"]
        else:
            first = last = None
            total_pct = None
            first_status = last_status = "—"
        # 异常年份（所有年份）
        abnormal_years = [p["year"] for p in points if p["status"] in ("偏高", "偏低")]
        # 显著变化（所有相邻年）
        sig_changes = [c for c in changes if c["significant"]]
        has_abnormal = len(abnormal_years) > 0
        has_sig = len(sig_changes) > 0
        # 完整年份（含缺失年）
        full_years = {p["year"] for p in points}
        ocr_years = {p["year"] for p in ocr_series}
        measured_years = sorted(full_years | ocr_years)
        missing_years = [y for y in years if y not in measured_years]
        # OCR 数据点（用于工作台展示，不参与趋势判定）
        ocr_points = []
        for e in ocr_series:
            ocr_points.append({
                "year": e["year"],
                "value": e["value"],
                "source": "ocr",
                "page": e.get("ocr_page"),
            })

        item = {
            "key": ind["key"],
            "category": ind["category"],
            "unit": ind["unit"],
            "display": ind["display"],
            "desc": ind.get("desc", ""),
            "advice": ind.get("advice", {}),
            "points": points,
            "ocr_points": ocr_points,
            "all_points": sorted([{"year":e["year"],"value":e["value"],"status":e.get("status","OCR提取"),"flag":e.get("flag",""),"ref_str":e.get("reference_str",""),"source":e.get("source","")} for e in (series+ocr_series)], key=lambda x: x["year"]),
            "changes": changes,
            "trend": trend,
            "total_change_pct": total_pct,
            "first_value": first,
            "last_value": last,
            "abnormal_years": abnormal_years,
            "significant_changes": sig_changes,
            "has_abnormal": has_abnormal,
            "has_significant": has_sig,
            "missing_years": missing_years,
            "measured_years": measured_years,
            # 整体健康方向（首末对比 + 异常状态变化）
            "good_direction": judge_good_direction(ind["key"], total_pct, first_status, last_status),
        }
        if ind["key"] in ("体重指数", "收缩压", "舒张压", "体重", "身高"):
            measurement_items.append(item)
        else:
            trend_items.append(item)

    # ---- 基础测量（体重/身高/BMI/血压）----
    # 上面已通过 indicators? 不，测量在 ds["measurements"] 中单独存
    # 将测量转换为指标格式分析
    meas_keys = ["体重", "身高", "体重指数", "收缩压", "舒张压"]
    meas_ref = {
        "体重": {"lo": None, "hi": None},
        "身高": {"lo": None, "hi": None},
        "体重指数": {"lo": 18.5, "hi": 23.9},
        "收缩压": {"lo": 90, "hi": 139},
        "舒张压": {"lo": 60, "hi": 89},
    }
    measurement_items = []
    for k in meas_keys:
        series = ds["measurements"].get(k, [])
        series = [e for e in series if e.get("value") is not None]
        if len(series) < 2:
            continue
        series.sort(key=lambda e: e["year"])
        points = []
        for e in series:
            v = e["value"]
            ref = meas_ref[k]
            status = judge_status(v, ref) if ref["lo"] is not None or ref["hi"] is not None else "正常"
            if k == "血压结论":
                status = "定性"
            points.append({
                "year": e["year"], "value": v, "status": status,
                "flag": "↑" if status == "偏高" else ("↓" if status == "偏低" else ""),
                "ref_str": f"{ref['lo']}-{ref['hi']}" if ref["lo"] is not None else "-",
                "ref_lo": ref["lo"], "ref_hi": ref["hi"],
            })
        changes = []
        for i in range(len(series)-1):
            v1, v2 = series[i]["value"], series[i+1]["value"]
            delta = round(v2 - v1, 4)
            pct = round(delta / abs(v1) * 100, 1) if v1 else None
            changes.append({
                "from_year": series[i]["year"], "to_year": series[i+1]["year"],
                "from": v1, "to": v2, "delta": delta, "pct": pct,
                "direction": direction_text(v1, v2),
                "significant": pct is not None and abs(pct) >= 20,
                "good_direction": judge_change_good(k, pct),
            })
        values = [p["value"] for p in points]
        diffs = [values[i+1]-values[i] for i in range(len(values)-1)]
        if all(d > 0 for d in diffs): trend = "持续上升"
        elif all(d < 0 for d in diffs): trend = "持续下降"
        elif len(diffs) >= 2 and diffs[0] > 0 and diffs[-1] < 0: trend = "先升后降"
        else: trend = "波动"
        first, last = values[0], values[-1]
        total_pct = round((last-first)/abs(first)*100, 1) if first else None
        abnormal_years = [p["year"] for p in points if p["status"] in ("偏高", "偏低")]
        meta = {
            "体重指数": {"category": "基础测量", "display": "体重指数(BMI)"},
            "体重": {"category": "基础测量", "display": "体重"},
            "身高": {"category": "基础测量", "display": "身高"},
            "收缩压": {"category": "基础测量", "display": "收缩压"},
            "舒张压": {"category": "基础测量", "display": "舒张压"},
        }[k]
        measurement_items.append({
            "key": k, "category": meta["category"], "unit": "", "display": meta["display"],
            "desc": INDICATOR_META.get(k, {}).get("desc", ""),
            "advice": INDICATOR_META.get(k, {}).get("advice", {}),
            "points": points, "changes": changes, "trend": trend,
            "total_change_pct": total_pct, "first_value": first, "last_value": last,
            "abnormal_years": abnormal_years,
            "significant_changes": [c for c in changes if c["significant"]],
            "has_abnormal": len(abnormal_years) > 0,
            "has_significant": any(c["significant"] for c in changes),
            "missing_years": [], "measured_years": [p["year"] for p in points],
            "good_direction": judge_good_direction(k, total_pct, points[0]["status"], points[-1]["status"]),
        })

    # 排序：异常优先，其次按分类
    def sort_key(item):
        score = 0
        if item["has_abnormal"]:
            score -= 2
        if item["has_significant"]:
            score -= 1
        return (score, item["category"], item["key"])

    trend_items.sort(key=sort_key)
    measurement_items.sort(key=sort_key)

    result = {
        "years": years,
        "generated_at": "2026-08-16",
        "method": {
            "status_rule": "以当年报告自带参考范围判定正常/偏高/偏低",
            "significant_rule": "相邻年变化相对幅度≥20%，或绝对变化≥参考范围宽度30%",
            "trend_rule": "≥2个相邻变化同向为持续升/降；先升后降/先降后升；否则波动",
            "missing_rule": "缺失年份在missing_years中标注，不参与计算",
            "good_rule": "基于指标方向性（INVERSE/POSITIVE）和首末状态判定 趋好/趋坏/中性/复杂",
            "trend_focus": f"整体趋势与首末对比仅基于{TREND_FOCUS_YEARS[0]}–{TREND_FOCUS_YEARS[-1]}，历史数据用于图表展示",
        },
        "indicators": trend_items,
        "measurements": measurement_items,
        "stats": {
            "total_indicators": len(trend_items) + len(measurement_items),
            "abnormal_count": sum(1 for it in trend_items if it["has_abnormal"]),
            "significant_count": sum(1 for it in trend_items if it["has_significant"]),
            "good_count": sum(1 for it in trend_items if it.get("good_direction") == "趋好"),
            "bad_count": sum(1 for it in trend_items if it.get("good_direction") == "趋坏"),
        },
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"已保存: {OUT_PATH}")
    print(f"指标总数: {result['stats']['total_indicators']} (化验 {len(trend_items)} + 测量 {len(measurement_items)})")
    print(f"有异常: {result['stats']['abnormal_count']}, 有显著变化: {result['stats']['significant_count']}")
    print(f"趋好: {result['stats']['good_count']}, 趋坏: {result['stats']['bad_count']}")
    # 异常指标列表
    abnormal = [it for it in trend_items if it["has_abnormal"]]
    print("\n异常指标 + 趋好/趋坏:")
    for it in abnormal:
        st = "、".join(f"{p['year']}:{p['value']}{p['flag']}" for p in it["points"])
        print(f"  [{it['category']}] {it['key']}: {st} | {it['trend']} | {it.get('good_direction','-')}")
    return result

if __name__ == "__main__":
    analyze()
