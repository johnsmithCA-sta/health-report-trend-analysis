#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
体检指标趋势分析 Markdown 报告生成器
- 指标汇总表（含异常高亮）
- 重点指标权威解读（引用默沙东诊疗手册/丁香医生/中国临床指南）
- 分层健康建议（生活方式/饮食/运动/就医指征）
- 趋势结论、逐年医生结论、方法学说明、动态扩展说明
输出: output/体检指标趋势分析报告.md
"""
import json
import os

BASE = os.environ.get("WORK_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TREND_PATH = os.path.join(BASE, "data", "trend_analysis.json")
DS_PATH = os.path.join(BASE, "data", "dataset_std.json")
OUT_DIR = os.path.join(BASE, "output")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "体检指标趋势分析报告.md")

with open(TREND_PATH, encoding="utf-8") as f:
    trend = json.load(f)
with open(DS_PATH, encoding="utf-8") as f:
    ds = json.load(f)

YEARS = trend["years"]

def fmt(v, unit=""):
    if v is None:
        return "—"
    if isinstance(v, float):
        s = f"{v:.2f}".rstrip("0").rstrip(".")
        return f"{s}{unit}"
    return f"{v}{unit}"

def cell(p):
    """表格单元格：异常加粗高亮"""
    if p["status"] == "偏高":
        return f"**{fmt(p['value'])}↑**"
    if p["status"] == "偏低":
        return f"**{fmt(p['value'])}↓**"
    return fmt(p["value"])

def advice_block(advice):
    if not advice:
        return ""
    lines = []
    labels = {"lifestyle": "生活方式", "diet": "饮食", "exercise": "运动", "see_doctor": "就医指征"}
    for k in ["lifestyle", "diet", "exercise", "see_doctor"]:
        if advice.get(k):
            lines.append(f"    - **{labels[k]}**：{advice[k]}")
    return "\n".join(lines)

def main():
    md = []
    years_str = "、".join(str(y) for y in YEARS)
    A = md.append

    # ========== 标题 ==========
    A(f"# 体检指标趋势分析报告（{YEARS[0]}–{YEARS[-1]}）")
    A("")
    A(f"> **报告日期**：2026-08-16　|　**覆盖年份**：{years_str}（2022 年数据为扫描件 OCR 提取，供参考）　|　**数据来源**：历年体检报告（已脱敏）")
    A(">")
    A("> **隐私声明**：本报告基于本地数据生成，不进行云端存储；姓名、证件号、联系方式、地址、单位、医院等个人身份信息均已脱敏，仅保留指标数值用于分析。")
    A("")
    A("---")
    A("")

    # ========== 一、健康总览（数据驱动，不硬编码任何个体数值） ==========
    A("## 一、健康总览")
    A("")
    ocr_note = "；其中扫描件/照片年份为 OCR 提取（参考为主，不参与显著变化判定）" if any(y < 2023 for y in YEARS) else ""
    n_years = len(YEARS)
    n_pts = sum(len(it["points"]) for it in trend["indicators"]) + sum(len(it["points"]) for it in trend["measurements"])
    A(f"对 {n_years} 年体检数据（{len(trend['indicators'])} 项指标，{n_pts} 个数据点{ocr_note}）进行逐年比对与趋势分析，核心发现如下：")
    A("")

    # 健康总览维度定义：维度名 → 相关指标 key 列表（数据驱动生成现状与趋势）
    OVERVIEW_DIMENSIONS = [
        ("血糖/糖尿病", ["空腹血糖", "糖化血红蛋白"]),
        ("血脂", ["总胆固醇", "甘油三酯", "低密度脂蛋白胆固醇", "高密度脂蛋白胆固醇"]),
        ("体重/肥胖", ["体重指数"]),
        ("血压", ["收缩压", "舒张压"]),
        ("肝功能", ["丙氨酸氨基转移酶(ALT)", "天门冬氨酸氨基转移酶(AST)", "γ-谷氨酰转移酶"]),
        ("尿酸/肾功能", ["尿酸", "肌酐", "尿素氮"]),
        ("同型半胱氨酸", ["同型半胱氨酸"]),
    ]
    all_items = {it["key"]: it for it in trend["indicators"] + trend["measurements"]}

    def dim_status(keys):
        """维度现状：聚合各指标的最近状态"""
        parts = []
        for k in keys:
            it = all_items.get(k)
            if not it or not it["points"]:
                continue
            last = it["points"][-1]
            flag = {"偏高": "偏高", "偏低": "偏低"}.get(last["status"], "")
            if flag:
                parts.append(f"{it['display']} {last['year']} 年{flag}（{fmt(last['value'])}{it['unit']}）")
            else:
                parts.append(f"{it['display']} 近年正常（{fmt(last['value'])}{it['unit']}）")
        return "；".join(parts) if parts else "—"

    def dim_trend(keys):
        """维度趋势：聚合各指标的整体方向与近三年变化"""
        parts = []
        for k in keys:
            it = all_items.get(k)
            if not it or not it["points"]:
                continue
            gd = it.get("good_direction", "中性")
            trend_txt = it["trend"]
            pct = it.get("total_change_pct")
            pct_txt = f"（{pct:+.1f}%）" if pct is not None else ""
            parts.append(f"{it['display']} {trend_txt}{pct_txt} {gd}")
        return "；".join(parts) if parts else "—"

    A("| 维度 | 现状 | 趋势结论 |")
    A("|---|---|---|")
    for name, keys in OVERVIEW_DIMENSIONS:
        A(f"| **{name}** | {dim_status(keys)} | {dim_trend(keys)} |")
    A("")
    A("> 注：上表由历年指标数据自动聚合生成（现状=最近一次检测结果与状态；趋势=整体方向+近三年变化百分比+趋好/趋坏判定）。具体数值与参考范围见下方分项明细表。")
    A("")
    A("**一句话结论**（自动生成）：")
    A("")
    bad_items = [it for it in trend["indicators"] if it.get("good_direction") == "趋坏" and it["has_abnormal"]]
    improve_items = [it for it in trend["indicators"] if it.get("good_direction") == "趋好" and it["has_abnormal"]]
    if bad_items:
        bad_desc = "、".join(f"{it['display']}（{it['trend']}）" for it in bad_items[:4])
        A(f"- **需重点关注**：{bad_desc} 呈趋坏或持续异常，建议就医评估。")
    else:
        A("- 未检出明显趋坏的核心指标。")
    if improve_items:
        imp_desc = "、".join(f"{it['display']}（{it['trend']}）" for it in improve_items[:4])
        A(f"- **已改善**：{imp_desc} 呈趋好，说明生活方式/干预措施有效，请继续保持。")
    ab_count = sum(1 for it in trend["indicators"] if it["has_abnormal"])
    A(f"- 全量 {len(trend['indicators'])} 项指标中 {ab_count} 项曾超出参考范围；详细解读与分层建议见下文各指标章节。")
    A("")
    A("---")
    A("")

    # ========== 二、基础测量趋势 ==========
    A("## 二、基础测量趋势（身高/体重/血压）")
    A("")
    A("| 指标 | " + " | ".join(str(y) for y in YEARS) + " | 参考 | 趋势 |")
    A("|---|---" + "---|" * len(YEARS) + "---|:---:|")
    for it in trend["measurements"]:
        row = [it["display"]]
        for y in YEARS:
            p = next((p for p in it["points"] if p["year"] == y), None)
            row.append(cell(p) if p else "—")
        ref = it["points"][0]["ref_str"] if it["points"] else "-"
        row.append(ref)
        row.append(it["trend"])
        A("| " + " | ".join(row) + " |")
    A("")
    A("> 注：血压结论按中国成人标准判定（正常血压 <120/80，正常高值 120–139/80–89）；BMI 判定：18.5–23.9 正常，24–27.9 超重，≥28 肥胖。")
    A("")
    A("---")
    A("")

    # ========== 三、异常指标汇总表 ==========
    abnormal = [it for it in trend["indicators"] if it["has_abnormal"]]
    A("## 三、异常指标汇总表（历年超参考范围项）")
    A("")
    A(f"共检出 **{len(abnormal)}** 项指标在 {YEARS[0]}–{YEARS[-1]} 年间至少一次超出参考范围。**加粗**表示该年度异常（↑偏高 / ↓偏低）。")
    A("")
    A("| 指标 | 分类 | " + " | ".join(str(y) for y in YEARS) + " | 参考范围（当年报告） | 4年趋势 |")
    A("|---|---|" + "---|" * len(YEARS) + "---|:---:|")
    # 按分类分组展示
    for cat in ["血糖", "血脂", "基础测量", "肝功能", "肾功能", "心血管", "血常规", "尿常规", "其他", "甲状腺", "维生素", "电解质", "肿瘤标志物", "心肌酶"]:
        items = [it for it in abnormal if it["category"] == cat]
        if not items:
            continue
        for it in items:
            row = [f"**{it['display']}**", it["category"]]
            for y in YEARS:
                p = next((p for p in it["points"] if p["year"] == y), None)
                row.append(cell(p) if p else "—")
            ref = it["points"][0]["ref_str"] if it["points"] else "-"
            row.append(ref)
            row.append(it["trend"])
            A("| " + " | ".join(row) + " |")
        A("")
    A("---")
    A("")

    # ========== 四、重点指标权威解读 ==========
    focus = [it for it in trend["indicators"] if it["has_abnormal"] or it["has_significant"]]
    A("## 四、重点指标权威解读与分层建议")
    A("")
    A("以下对检出异常或存在显著变化的重点指标进行解读。临床意义依据 **默沙东诊疗手册（MSD Manual）**、**丁香医生**及 **《中国2型糖尿病防治指南》《中国血脂管理指南》** 等权威来源整理，供健康管理参考，不构成诊疗意见。")
    A("")

    # 血糖
    A("### 4.1 血糖与糖代谢（重点）")
    A("")
    for key in ["空腹血糖", "糖化血红蛋白"]:
        it = next((x for x in trend["indicators"] if x["key"] == key), None)
        if it:
            A(f"#### {it['display']}（{it['unit']}）")
            A("")
            A("| " + " | ".join(str(y) for y in YEARS) + " | 参考 |")
            A("|" + "---|" * len(YEARS) + "---|")
            A("| " + " | ".join(cell(p) if (p := next((q for q in it["points"] if q["year"] == y), None)) else "—" for y in YEARS) + " | " + it["points"][0]["ref_str"] + " |")
            A("")
            A(f"- **4年趋势**：{it['trend']}（{it['total_change_pct']}%）。异常年份：{('、'.join(str(x) for x in it['abnormal_years']) or '无')}。")
            A(f"- **临床意义**：{it['desc']}")
            A("- **分层建议**：")
            A(advice_block(it["advice"]))
            A("")
    A("")
    A("### 4.2 血脂四项")
    A("")
    for key in ["总胆固醇", "甘油三酯", "低密度脂蛋白胆固醇", "高密度脂蛋白胆固醇"]:
        it = next((x for x in trend["indicators"] if x["key"] == key), None)
        if it:
            A(f"#### {it['display']}（{it['unit']}）")
            A("")
            A("| " + " | ".join(str(y) for y in YEARS) + " | 参考 |")
            A("|" + "---|" * len(YEARS) + "---|")
            A("| " + " | ".join(cell(p) if (p := next((q for q in it["points"] if q["year"] == y), None)) else "—" for y in YEARS) + " | " + it["points"][0]["ref_str"] + " |")
            A("")
            A(f"- **4年趋势**：{it['trend']}（{it['total_change_pct']}%）。异常年份：{('、'.join(str(x) for x in it['abnormal_years']) or '无')}。")
            A(f"- **临床意义**：{it['desc']}")
            A("- **分层建议**：")
            A(advice_block(it["advice"]))
            A("")
    A("")
    A("### 4.3 肝功能")
    A("")
    for key in ["丙氨酸氨基转移酶(ALT)", "γ-谷氨酰转移酶", "碱性磷酸酶", "直接胆红素"]:
        it = next((x for x in trend["indicators"] if x["key"] == key), None)
        if it:
            A(f"#### {it['display']}（{it['unit']}）")
            A("")
            A("| " + " | ".join(str(y) for y in YEARS) + " | 参考 |")
            A("|" + "---|" * len(YEARS) + "---|")
            A("| " + " | ".join(cell(p) if (p := next((q for q in it["points"] if q["year"] == y), None)) else "—" for y in YEARS) + " | " + it["points"][0]["ref_str"] + " |")
            A("")
            A(f"- **4年趋势**：{it['trend']}（{it['total_change_pct']}%）。异常年份：{('、'.join(str(x) for x in it['abnormal_years']) or '无')}。")
            A(f"- **临床意义**：{it['desc']}")
            A("- **分层建议**：")
            A(advice_block(it["advice"]))
            A("")
    A("")
    A("### 4.4 肾功能与尿酸")
    A("")
    for key in ["尿酸", "肌酐"]:
        it = next((x for x in trend["indicators"] if x["key"] == key), None)
        if it:
            A(f"#### {it['display']}（{it['unit']}）")
            A("")
            A("| " + " | ".join(str(y) for y in YEARS) + " | 参考 |")
            A("|" + "---|" * len(YEARS) + "---|")
            A("| " + " | ".join(cell(p) if (p := next((q for q in it["points"] if q["year"] == y), None)) else "—" for y in YEARS) + " | " + it["points"][0]["ref_str"] + " |")
            A("")
            A(f"- **4年趋势**：{it['trend']}（{it['total_change_pct']}%）。异常年份：{('、'.join(str(x) for x in it['abnormal_years']) or '无')}。")
            A(f"- **临床意义**：{it['desc']}")
            A("- **分层建议**：")
            A(advice_block(it["advice"]))
            A("")
    A("")
    A("### 4.5 心血管风险指标")
    A("")
    for key in ["同型半胱氨酸"]:
        it = next((x for x in trend["indicators"] if x["key"] == key), None)
        if it:
            A(f"#### {it['display']}（{it['unit']}）")
            A("")
            A("| " + " | ".join(str(y) for y in YEARS) + " | 参考 |")
            A("|" + "---|" * len(YEARS) + "---|")
            A("| " + " | ".join(cell(p) if (p := next((q for q in it["points"] if q["year"] == y), None)) else "—" for y in YEARS) + " | " + it["points"][0]["ref_str"] + " |")
            A("")
            A(f"- **4年趋势**：{it['trend']}（{it['total_change_pct']}%）。异常年份：{('、'.join(str(x) for x in it['abnormal_years']) or '无')}。")
            A(f"- **临床意义**：{it['desc']}")
            A("- **分层建议**：")
            A(advice_block(it["advice"]))
            A("")
    A("")
    A("### 4.6 血常规")
    A("")
    for it in [x for x in trend["indicators"] if x["category"] == "血常规" and (x["has_abnormal"] or x["has_significant"])]:
        A(f"#### {it['display']}（{it['unit']}）")
        A("")
        A("| " + " | ".join(str(y) for y in YEARS) + " | 参考 |")
        A("|" + "---|" * len(YEARS) + "---|")
        A("| " + " | ".join(cell(p) if (p := next((q for q in it["points"] if q["year"] == y), None)) else "—" for y in YEARS) + " | " + it["points"][0]["ref_str"] + " |")
        A("")
        A(f"- **4年趋势**：{it['trend']}（{it['total_change_pct']}%）。异常年份：{('、'.join(str(x) for x in it['abnormal_years']) or '无')}。")
        A(f"- **临床意义**：{it['desc']}")
        if it["advice"]:
            A("- **分层建议**：")
            A(advice_block(it["advice"]))
        A("")
    A("")
    A("### 4.7 尿常规")
    A("")
    it = next((x for x in trend["indicators"] if x["key"] == "尿沉渣红细胞"), None)
    if it:
        A(f"#### {it['display']}（{it['unit']}）")
        A("")
        A("| " + " | ".join(str(y) for y in YEARS) + " | 参考 |")
        A("|" + "---|" * len(YEARS) + "---|")
        A("| " + " | ".join(cell(p) if (p := next((q for q in it["points"] if q["year"] == y), None)) else "—" for y in YEARS) + " | " + it["points"][0]["ref_str"] + " |")
        A("")
        A(f"- **4年趋势**：{it['trend']}。异常年份：{('、'.join(str(x) for x in it['abnormal_years']) or '无')}。")
        A("- **临床意义**（通用解读）：尿沉渣红细胞升高常见于泌尿系结石、感染、运动性血尿等；一过性升高后恢复正常提示多为良性/可逆因素（如结石、剧烈运动），持续升高需排查肾小球疾病。具体数值与随访建议以医生意见为准。")
        A("- **分层建议**：")
        A(advice_block(it["advice"] or {
            "lifestyle": "多饮水（每日 2000ml 以上），减少尿路结石形成。",
            "diet": "低盐低嘌呤，适量补钙，避免高草酸食物过量（如浓茶、菠菜）。",
            "exercise": "适度运动，避免久坐。",
            "see_doctor": "若再次出现肉眼血尿或腰痛，及时至泌尿外科就诊；每年复查泌尿系超声。"}))
        A("")
    A("---")
    A("")

    # ========== 五、显著变化指标（未超范围但变化大） ==========
    sig_only = [it for it in trend["indicators"] if it["has_significant"] and not it["has_abnormal"]]
    A("## 五、显著变化指标（未超参考范围但年度变化 ≥20%）")
    A("")
    A("以下指标虽在参考范围内，但相邻年变化幅度较大，提示生理状态波动，值得关注：")
    A("")
    A("| 指标 | 分类 | 变化区间 | 变化幅度 | 方向 |")
    A("|---|---|---|---|:---:|")
    for it in sig_only:
        for c in it["significant_changes"]:
            A(f"| {it['display']} | {it['category']} | {c['from_year']}→{c['to_year']} | {fmt(c['from'])}→{fmt(c['to'])}（{c['pct']}%） | {c['direction']} |")
    A("")
    A("---")
    A("")

    # ========== 六、逐年医生结论 ==========
    A("## 六、逐年体检医生结论")
    A("")
    for y in YEARS:
        A(f"### {y} 年")
        A("")
        for item in ds["summaries"].get(str(y), []):
            A(f"- {item}")
        A("")
    A("---")
    A("")

    # ========== 七、影像与功能检查结论 ==========
    A("## 七、影像与功能检查结论（超声/CT/心电图）")
    A("")
    for k in ["超声", "CT", "心电图", "心脏彩超"]:
        v = ds["exam_conclusions"].get(k)
        if not v:
            continue
        A(f"### {k}")
        A("")
        for y in YEARS:
            txt = v.get(str(y))
            if txt:
                A(f"**{y}年**：")
                for line in txt.split("\n"):
                    A(f"- {line.strip()}")
                A("")
        A("")
    A("---")
    A("")

    # ========== 八、方法学与容错说明 ==========
    A("## 八、方法学与技术说明")
    A("")
    A("### 8.1 数据处理流程")
    A("")
    A("1. **数据解析**：遍历历年体检报告 PDF，基于文字坐标定位提取化验表格（项目/结果/异常标志/参考范围/单位），产出标准化指标与数据点。")
    A("2. **统一指标字典**：146 个原始指标名归一化为 116 个标准指标（如「高密度脂蛋白胆固醇[HDL-C]」→「高密度脂蛋白胆固醇」），保证多源口径一致。")
    A("3. **单位归一化**：统一单位写法（mmol/l→mmol/L、ug/L→μg/L、ng/ml→ng/mL 等）。")
    A("4. **异常判定**：以**当年报告自带参考范围**判定，规避不同年份试剂/标准差异（如直接胆红素 2025 年起参考范围由 0.0-4.0 调整为 1.7-6.8）。")
    A("5. **趋势判定**：相邻年变化幅度≥20% 或≥参考范围宽度 30% 记为显著变化；连续同向变化记为持续升/降。")
    A("")
    A("### 8.2 缺失值容错")
    A("")
    A("- 各年体检套餐不同，部分指标仅部分年份测量（如电解质、维生素 D、果糖胺、血沉等），在表中以「—」表示，不参与趋势计算。")
    A("- 同指标缺失年份已在趋势数据中标注（`missing_years`），图表中对应年份留空。")
    A("- 定性结果（阴性/阳性/颜色等）单独处理，不做数值趋势分析。")
    A("- 解析器对页眉页脚噪声、小结段落混入数据（4 条）、同值重复（去重）均有容错过滤。")
    A("")
    A("### 8.3 口径差异说明")
    A("")
    A("| 差异类型 | 示例 | 处理方式 |")
    A("|---|---|---|")
    A("| 试剂/仪器更换 | 某指标参考范围在不同年度发生变化（如直接胆红素） | 逐年用当年报告自带范围判定；跨年比较以数值变化为主 |")
    A("| 参考范围微调 | 同指标各年度参考下限/上限略有差异（如糖化血红蛋白、游离甲状腺素） | 均按当年范围独立判定，不影响结论 |")
    A("| 检测方法不同 | 某指标采用不同试剂盒（如肌钙蛋白I） | 分别按当年范围判定，不做跨年口径换算 |")
    A("| 单位写法差异 | ug/L 与 ng/mL 等价（1:1） | 单位归一化处理 |")
    A("")
    A("### 8.4 隐私与存储")
    A("")
    A("- 全程本地处理，不进行云端存储。")
    A("- 若需云端存储/分享，请使用脱敏数据集 `data/anonymized_dataset.json`（仅含指标数值+年份，不含姓名、证件号、电话、地址、单位、医院等身份信息）。")
    A("")
    A("---")
    A("")

    # ========== 九、动态扩展 ==========
    A("## 九、动态扩展（年度报告接入）")
    A("")
    A("系统预留年度报告接口，新报告加入后**无需人工调整**即可自动更新：")
    A("")
    A("1. **新增报告**：将新年度体检 PDF 放入 `体检报告/` 目录。")
    A("2. **自动重算**：运行 `python scripts/parse_reports.py`（解析新报告）→ `python scripts/build_dataset.py`（合并入标准数据集，自动识别新增指标并映射）→ `python scripts/trend_analysis.py`（重算全量趋势）。")
    A("3. **报告与工作台更新**：重新运行 `report_generator.py` 与健康管理工作台（HTML 读取同一份 `trend_analysis.json`），所有图表、汇总、异常高亮自动刷新。")
    A("4. **新指标自动纳入**：若新报告出现字典未收录的指标名，系统会记录到 `unrecognized_names`，只需在 `indicator_dict.py` 补充一行映射即可完全接入。")
    A("")
    A("---")
    A("")
    A("*本报告为健康管理参考，不能替代专业医疗诊断。如指标持续异常或有不适症状，请及时就医。*")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    print(f"已生成: {OUT_PATH}")

if __name__ == "__main__":
    main()
