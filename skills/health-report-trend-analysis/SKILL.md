---
name: health-report-trend-analysis
description: >-
  体检指标趋势分析系统。当用户要求对历年体检报告进行数据化处理、指标趋势分析、
  健康管理工作台展示（体检报告、指标趋势、历年体检、健康管理、体检数据解析、
  化验单分析）时使用。支持 3 种输入形态：电子版 PDF（文本层）、扫描件 PDF、
  照片 JPG（自动合成 PDF）；产出统一指标字典（116 指标）、历年趋势比对
  （异常/显著变化/趋好趋坏）、权威医学解读（默沙东/丁香医生/中国指南）、
  结构化 Markdown 报告与离线 HTML 工作台。全程本地处理，自动生成脱敏数据集。
  趋势判定聚焦近三年（TREND_FOCUS_YEARS 可配置）。
version: "1.0.2"
license: MIT
tags: [体检, 健康管理, 趋势分析, 指标, 医学解读, health, wellness, OCR]
---

# 体检指标趋势分析系统

## 用途

将多年度、多形态（电子 PDF / 扫描件 / 照片）的体检报告统一解析为标准化指标时间序列，产出趋势分析报告 + 交互式健康管理工作台。全本地处理、自动脱敏、动态扩展（新增报告重跑流水线即可）。

## 触发词

- "帮我把 XX 年体检报告加进去，更新趋势分析"
- "分析历年体检报告 / 体检指标趋势"
- "健康管理工作台 / 体检数据解析 / 化验单分析"

## 环境准备

```bash
# 依赖（已装可跳过）：pymupdf、Pillow；扫描件/照片需 macOS Vision（pyobjc-framework-Vision）
export REPORT_DIR=/path/to/体检报告目录      # 报告存放目录（含 PDF 或 年度文件夹+JPG）
export WORK_DIR=/path/to/工作数据目录        # 数据产物目录（自动建 data/ 与 output/）
export PY=/path/to/python                    # 建议用带依赖的 python 解释器
```

## 执行流程

1. **识别输入形态**：遍历 `REPORT_DIR`
   - 根目录 `*.pdf` 含文本层 → 电子版（parse_reports 处理）
   - 根目录 `*.pdf` 无文本层 → 扫描件（vision_ocr + extract_2022 流程）
   - 年度子目录 `YYYY体检报告/*.JPG` → 照片版（make_year_pdfs 合成 → OCR 提取）
2. **解析电子版 PDF**（坐标定位法，列边界见 `references/解析与口径.md`）：
   ```bash
   $PY scripts/parse_reports.py
   ```
   产出 `data/reports_raw.json`（历年化验项目 + 测量 + 检查结论 + 医生小结）
3. **照片版合成 PDF + OCR**（如存在 JPG 目录）：
   ```bash
   $PY scripts/make_year_pdfs.py      # 年度多张 JPG → 单份 PDF（横拍自动旋转校正）
   $PY scripts/extract_2015_2020.py   # Vision OCR + 缩写映射/参考范围反推
   ```
   扫描件（如 2022.PDF）：`$PY scripts/extract_2022.py`
4. **归一化 + 构建数据集**（名称/单位映射、脏数据过滤、OCR 自动注入、生成脱敏版）：
   ```bash
   $PY scripts/build_dataset.py
   ```
   产出 `data/dataset_std.json` + `data/anonymized_dataset.json`
5. **趋势分析**（当年口径判定异常、显著变化 ≥20% 或 ≥参考宽度 30%、趋好/趋坏、近三年聚焦）：
   ```bash
   $PY scripts/trend_analysis.py
   ```
6. **生成交付物**：
   ```bash
   $PY scripts/report_generator.py    # output/体检指标趋势分析报告.md
   $PY scripts/build_dashboard.py     # output/health_dashboard.html（单文件离线）
   ```

## 新报告接入指南

新增年度体检报告时，按形态走对应分支（详见 `references/新报告接入指南.md`）：

1. **放入报告**：`REPORT_DIR` 根目录放 `*.pdf`，或建年度目录 `YYYY体检报告/` 放 JPG
2. **识别形态**：`python -c` 检查 PDF 文本层（`get_text()` 长度 >0 = 电子版）
   - 电子版 → 直接跑 `parse_reports.py`；列边界异常时先打印 1 页坐标样本
   - 扫描件/照片 → `make_year_pdfs.py` + `extract_2022.py`（或 `extract_2015_2020.py`）
3. **补字典**（如有未收录指标）：`indicator_dict.py` 的 `NAME_MAP` 补一行映射（日志见 `data/unrecognized`）
4. **重跑流水线**：build_dataset → trend_analysis → report_generator → build_dashboard
5. **验收**：确认新年份出现在 `trend_analysis.json["years"]` 与工作台时间轴；抽查 3 个关键指标数值与报告一致；生成并校验脱敏版

## 关键规则

- **新增年度报告**：放入 `REPORT_DIR` → 重跑 2→6 步即可（解析/归一化/趋势/交付自动含新数据）；字典未收录指标在 `data/unrecognized` 记录，补 `indicator_dict.py` 的 `NAME_MAP` 一行即可
- **隐私硬约束**：全程本地；任务完成必须生成并校验脱敏版（不含姓名/证件号/电话/地址/医院），分享只用 `anonymized_dataset.json`；报告正文中的体检小结与影像结论已做展示层脱敏（机构名称、医师姓名掩码，见 `report_generator.py` 的 `mask_identity_text`）；`build_dataset.py` 末尾自动校验脱敏版（身份证/手机号/邮箱/医院名正则扫描，命中即报错退出）
- **OCR 数据定位**：OCR 提取的指标只用于图表展示（灰色 Ⓞ 标注），**不参与显著变化判定**，避免污染统计
- **趋势聚焦**：整体趋势与首末对比仅基于 `trend_analysis.py` 中 `TREND_FOCUS_YEARS`（默认近三年），历史数据仅作展示背景
- **口径一致性**：异常判定用**当年报告自带参考范围**（试剂更换自动适配，如直接胆红素 2025 年起 0.0–4.0 → 1.7–6.8）

## 交付物

- `output/体检指标趋势分析报告.md` — 指标汇总表、异常高亮、权威解读、分层建议（生活方式/饮食/运动/就医指征）、方法学
- `output/health_dashboard.html` — 健康总览、趋好/趋坏分组筛选、折线图+参考范围带、时间跨度切换（单文件、无外部依赖）

## 使用示例（一次完整会话）

**用户**：「帮我把 2027 年体检报告加进去，更新趋势分析。」

1. 检查 `REPORT_DIR`：发现新文件 `体检报告_270510004567.pdf`（电子版，文本层完整）
2. 小样本确认列边界：打印 1 页坐标，与 `references/解析与口径.md` 一致 → 无需调整
3. 跑流水线：
   ```
   export REPORT_DIR=体检报告 WORK_DIR=/path/to/work
   python3 scripts/parse_reports.py
   python3 scripts/build_dataset.py
   python3 scripts/trend_analysis.py
   python3 scripts/report_generator.py
   python3 scripts/build_dashboard.py
   ```
4. 解析日志显示：新年度 98 项指标，1 个未识别名 → 在 `indicator_dict.py` 的 `NAME_MAP` 补 1 行后重跑 build_dataset
5. 验收：`trend_analysis.json["years"]` 含 2027；工作台时间轴出现 2027；抽查血糖/血脂/BMI 数值与报告一致；grep 脱敏版无身份信息
6. 交付：报告 + 工作台路径告知用户；说明 2027 年各异常指标的变化与建议

## 降本纪律（执行时强制）

1. **小样本先行**：解析新格式前先打印 1 页坐标样本确认列边界，再全量处理（避免整文件 dump）
2. **输出压缩**：调试命令统一 `| head -N` / `python -c` 精准提取，禁止整文件 cat 大 JSON
3. **子代理隔离**：大文件读取/格式探测交给 Explore 子代理，主线程只收结论
4. 验证只做一次最终截图，中间迭代用 DOM/JS 检查替代

详见 `references/降本纪律.md`。
