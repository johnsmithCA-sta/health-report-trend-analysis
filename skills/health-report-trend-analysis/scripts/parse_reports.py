#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
体检报告 PDF 解析器 v2（坐标定位版）
- 化验表格: 名称 x<200 | 值 200-300 | 参考 295-390 | 标志 385-500 | 单位 x>=460
- 身体测量: 名称 x<120 | 值 120-300（兼容 2023 值在前/名称在后的文本模式）
- 检查结论: 超声/CT/心电图/心脏彩超
- 医生小结: 本次体检汇总
输出结构化 JSON
"""
import pymupdf
import json
import re
import os
from collections import defaultdict

# 环境变量可配置（技能化支持）：REPORT_DIR 报告目录 / DATA_DIR 数据输出目录
REPORT_DIR = os.environ.get("REPORT_DIR", "体检报告")  # 可配：REPORT_DIR 指向报告目录
OUT_DIR = os.environ.get("DATA_DIR", "data")  # 可配：DATA_DIR 指向数据输出目录
os.makedirs(OUT_DIR, exist_ok=True)

# 页眉页脚噪声词
NOISE = ["美好人生", "体检号", "姓名", "日期", "审核日期", "检验者", "初检医师", "终检医师",
         "第", "页", "体检报告书", "体 检 报 告 书"]

def group_lines(words):
    """按 y 聚合为行；同一视觉行（y 差 <1.5px）合并"""
    items = []
    for w in words:
        x0, y0, x1, y1, word = w[0], w[1], w[2], w[3], w[4]
        items.append((y0, x0, word))
    items.sort(key=lambda t: t[0])
    result = []
    cur_y = None
    cur = []
    for y0, x0, word in items:
        if cur_y is None or y0 - cur_y < 1.5:
            cur.append((x0, word))
            if cur_y is None:
                cur_y = y0
        else:
            result.append((cur_y, sorted(cur, key=lambda t: t[0])))
            cur = [(x0, word)]
            cur_y = y0
    if cur:
        result.append((cur_y, sorted(cur, key=lambda t: t[0])))
    return result

def is_noise_line(name, full_text):
    """判断是否为页眉页脚噪声行"""
    if not name:
        return True
    for n in NOISE:
        if name.startswith(n):
            return True
    # 页码行：纯数字或 第X页/共Y页
    if re.fullmatch(r'\d+', name):
        return True
    # 小结编号行：如 "8、乙肝五项"
    if re.match(r'^\d+、', name):
        return True
    return False

def parse_lab_tables(lines, page_idx, year, shared_section):
    """解析一页中所有化验表格，返回 (items, sections)。shared_section 跨页共享当前分组。
    状态机：pending_title 记录表头前的标题 → 表头出现时消费为 section → 数据行直到'检验者'结束"""
    items = []
    sections = []
    current_section = shared_section[0]
    pending_title = None
    in_table = False
    for y, ws in lines:
        full = "".join(w for _, w in ws)
        name = "".join(w for x, w in ws if x < 195).strip()
        val = "".join(w for x, w in ws if 195 <= x < 290).strip()
        ref = "".join(w for x, w in ws if 290 <= x < 385).strip()
        flag = "".join(w for x, w in ws if 385 <= x < 455).strip()
        unit = "".join(w for x, w in ws if x >= 455).strip()

        # 表头行：消费 pending_title 作为分组
        if "检验项目" in full and "参考范围" in full:
            if pending_title:
                current_section = pending_title
                sections.append(pending_title)
                pending_title = None
            in_table = True
            continue
        # 无值非噪声行 → 可能的标题（表格外或表格内都可能出现）
        if name and not val and not is_noise_line(name, full):
            pending_title = name
            continue
        if not in_table:
            continue
        # 表格结束标志
        if is_noise_line(name, full):
            if name.startswith("检验者") or name.startswith("审核日期") or \
               name.startswith("初检") or name.startswith("终检") or "第" in name:
                in_table = False
                pending_title = None
            continue
        # 数据行
        if name and val:
            items.append({
                "section": current_section,
                "name": name,
                "value": val,
                "flag": flag,
                "reference": ref,
                "unit": unit,
                "year": year,
            })
    shared_section[0] = current_section
    return items, sections

def parse_measurement_table(lines):
    """身体测量：名称 x<120, 值 120-300。兼容值在前的文本模式。"""
    result = {}
    for y, ws in lines:
        name_words = [w for x, w in ws if x < 120]
        val_words = [w for x, w in ws if 120 <= x < 300]
        name = "".join(name_words).strip()
        val = "".join(val_words).strip()
        # 兼容值在前名称在后（2023 文本模式："114 mmHg 收缩压"）
        if not name and val:
            pass
        if name in ["收缩压", "舒张压", "体重", "身高", "体重指数", "血压结论"]:
            # 去掉单位
            v = re.sub(r'\s*(mmHg|kg|cm)\s*$', '', val)
            result[name] = v.strip()
    return result

def extract_conclusions(doc):
    """提取检查结论：超声/CT/心电图/心脏彩超（按文本行）"""
    conclusions = {}
    for i in range(len(doc)):
        text = doc[i].get_text()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for j, l in enumerate(lines):
            if "检查结论" not in l:
                continue
            # 确定属于哪个检查项（向上找最近的检查标题）
            section = None
            for k in range(j, -1, -1):
                kl = lines[k]
                if kl.startswith("超声检查"):
                    section = "超声"; break
                if kl.startswith("放射科(CT)") or kl.startswith("放射科"):
                    section = "CT"; break
                if kl.startswith("心电图"):
                    section = "心电图"; break
                if kl.startswith("心脏彩超"):
                    section = "心脏彩超"; break
            if section is None:
                continue
            # 结论内容：本行"检查结论："之后的部分 + 后续行直到新检查项/页脚/表格
            concl_parts = []
            after = l.split("检查结论", 1)[-1].lstrip(":： ")
            if after:
                concl_parts.append(after)
            for k in range(j+1, len(lines)):
                nxt = lines[k]
                if nxt.startswith("检查医生") or nxt.startswith("审核日期") or nxt.startswith("检验者") or \
                   nxt.startswith("血常规") or nxt.startswith("尿常规") or nxt.startswith("肝功能") or \
                   nxt.startswith("肾功能") or nxt.startswith("血脂") or nxt.startswith("血糖") or \
                   nxt.startswith("糖化") or nxt.startswith("心肌酶") or nxt.startswith("甲状腺") or \
                   nxt.startswith("乙肝") or nxt.startswith("肿瘤") or nxt.startswith("EB") or \
                   nxt.startswith("前列腺") or nxt.startswith("体检报告书") or nxt.startswith("第") or \
                   nxt.startswith("美好人生") or nxt.startswith("小结") or nxt.startswith("项目名称") or \
                   nxt.startswith("超声检查") or nxt.startswith("放射科") or nxt.startswith("心电图") or \
                   nxt.startswith("心脏彩超") or nxt == "检验项目" or "参考范围" in nxt or \
                   nxt.startswith("检查结论") or re.match(r'^\d+\.', nxt):
                    break
                concl_parts.append(nxt)
            if concl_parts:
                conclusions[section] = "\n".join(concl_parts)
    return conclusions

def extract_summary(doc):
    """医生小结：本次体检汇总 + 健康建议"""
    summary = []
    suggestions = []
    for i in range(len(doc)):
        text = doc[i].get_text()
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for j, l in enumerate(lines):
            if l == "本次体检汇总：" or l.startswith("本次体检汇总"):
                for k in range(j+1, len(lines)):
                    nxt = lines[k]
                    if nxt.startswith("【") or re.match(r'^\d+\.【', nxt):
                        summary.append(nxt)
                    elif "健康建议" in nxt or nxt.startswith("第") or nxt.startswith("页"):
                        break
                break
        # 健康建议
        if "健康建议" in text:
            idx = text.find("健康建议")
            seg = text[idx:idx+2000]
            suggestions.append(seg)
    return summary, suggestions

def parse_report(pdf_path, report_id, year):
    doc = pymupdf.open(pdf_path)
    report = {
        "report_id": report_id,
        "year": year,
        "date": None,
        "age": None,
        "basic_info": {},
        "lab_items": [],
        "measurements": {},
        "exam_conclusions": {},
        "summary": [],
        "suggestions": [],
        "sections": [],
    }
    shared_section = [None]
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text()
        words = page.get_text("words")
        lines = group_lines(words)

        if i == 0:
            m = re.search(r'登记日期\s*\n?\s*([\d-]+)', text)
            if m: report["date"] = m.group(1)
            m = re.search(r'年\s*龄\s*\n?\s*(\d+)\s*岁', text)
            if m: report["age"] = m.group(1)

        # 化验表格（跨页共享分组）
        has_lab_header = any("检验项目" in "".join(w for _, w in ws) for _, ws in lines)
        if has_lab_header:
            items, sections = parse_lab_tables(lines, i, year, shared_section)
            report["lab_items"].extend(items)
            report["sections"].extend(sections)

        # 身体测量
        if any("身高" in "".join(w for _, w in ws) or "体重" in "".join(w for _, w in ws) for _, ws in lines):
            meas = parse_measurement_table(lines)
            if meas:
                report["measurements"].update(meas)

    report["exam_conclusions"] = extract_conclusions(doc)
    report["summary"], report["suggestions"] = extract_summary(doc)
    return report

def main():
    # 自动扫描 REPORT_DIR 下的电子版 PDF（技能化/脱敏：不硬编码任何具体文件名）
    files = []
    if os.path.isdir(REPORT_DIR):
        for fn in sorted(os.listdir(REPORT_DIR)):
            if fn.lower().endswith(".pdf"):
                # 文件名内嵌报告编号（如 YYMMDD...）时尝试推断年份
                m = re.search(r'(\d{2})(\d{4})\d{4}', fn)
                year = None
                if m:
                    yy = int(m.group(1))
                    year = 2000 + yy if yy < 50 else 1900 + yy
                if year and 1990 <= year <= 2030:
                    rid = re.search(r'\d{10}', fn)
                    files.append((fn, rid.group(0) if rid else fn, year))
    if not files:
        print(f"[警告] REPORT_DIR（{REPORT_DIR}）下未发现可识别年份的 PDF；请检查文件名格式（如 体检报告_YYMMDDXXXX.pdf）或设置 REPORT_DIR 环境变量")
        return
    all_reports = []
    for fname, rid, year in files:
        path = os.path.join(REPORT_DIR, fname)
        if not os.path.exists(path):
            print(f"[跳过] {path}")
            continue
        print(f"[解析] {fname} ({year})")
        report = parse_report(path, rid, year)
        all_reports.append(report)
        print(f"  日期={report['date']} 年龄={report['age']}")
        print(f"  化验指标={len(report['lab_items'])} 测量={report['measurements']}")
        print(f"  结论: {list(report['exam_conclusions'].keys())}")
        print(f"  汇总条数={len(report['summary'])}")
        print()

    out_path = os.path.join(OUT_DIR, "reports_raw.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=2)
    print(f"已保存: {out_path}")

if __name__ == "__main__":
    main()
