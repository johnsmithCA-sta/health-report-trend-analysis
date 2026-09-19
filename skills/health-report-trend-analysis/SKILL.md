---
name: health-report-trend-analysis
slug: health-report-trend-analysis
displayName: 体检指标趋势分析
summary: 多年度体检报告趋势分析：解析电子/扫描/照片三种报告形态，产出统一指标字典、异常与趋好趋坏判定、权威医学解读、Markdown 报告与离线 HTML 工作台。
description: 体检指标趋势分析系统。当用户要求对历年体检报告进行数据化处理、指标趋势分析、健康管理工作台展示（体检报告、指标趋势、历年体检、健康管理、体检数据解析、化验单分析）时使用。支持
  3 种输入形态：电子版 PDF（文本层）、扫描件 PDF、照片 JPG（自动合成 PDF）；产出统一指标字典（114
  指标）、历年趋势比对（异常/显著变化/趋好趋坏）、权威医学解读（默沙东/丁香医生/中国指南）、结构化 Markdown 报告与离线 HTML
  工作台。全程本地处理，自动生成脱敏数据集。趋势判定聚焦近三年（--focus-years 可配置）。不适用于股票/账单/合同等非体检文档的分析。
version: 1.1.2
license: MIT
author: johnsmithCA-sta
homepage: https://github.com/johnsmithCA-sta/health-report-trend-analysis
agent_created: true
tags:
  - 体检报告
  - 健康趋势
  - lab-results
  - health-analytics
  - 数据可视化
  - 健康档案
---

# 体检指标趋势分析系统

## 用途

将多年度、多形态（电子 PDF / 扫描件 / 照片）的体检报告统一解析为标准化指标时间序列，产出趋势分析报告 + 交互式健康管理工作台。全本地处理、自动脱敏、动态扩展（新增报告重跑流水线即可）。

## 触发词

- 历年体检报告 / 多年度体检报告 / 历年的体检报告 / 历年体检
- 体检报告数据化 / 体检数据解析 / 体检报告解析
- 体检指标趋势 / 指标趋势分析 / 指标趋势
- 历年体检指标对比 / 体检指标对比 / 逐年对比 / 逐年变化
- 化验单分析 / 化验单解读 / 检验报告分析
- 体检报告扫描件 / 扫描件体检报告 / 扫描件 OCR
- 体检报告照片 / 照片版体检报告 / 手机拍的体检报告
- 健康管理工作台 / 健康管理看板 / 健康数据看板 / 可视化看板
- 血糖趋势 / 血糖变化 / 尿酸偏高 / 血脂趋势 / 血压趋势
- 体检异常指标 / 异常指标解读 / 指标异常
- 新增体检报告 / 新报告接入 / 加入新一年体检
- 体检数据脱敏 / 脱敏数据集 / 脱敏版 / 可分享数据集

## 环境准备

```bash
# 依赖（已装可跳过）：pymupdf 必需；Pillow（照片合成）、pyobjc-framework-Vision/Quartz（OCR，仅 macOS）可选
export REPORT_DIR=/path/to/体检报告目录      # 报告存放目录（含 PDF 或 年度文件夹+JPG）
export WORK_DIR=/path/to/工作数据目录        # 数据产物目录（自动建 data/ 与 output/）
export PY=/path/to/python                    # 建议用带依赖的 python 解释器
```

**Step 0（每个新会话第一步，必做）**：

```bash
$PY scripts/check_deps.py            # 一键体检：缺什么、影响哪几个脚本、怎么装
$PY scripts/check_deps.py --json     # 机器可读，供自动化消费
```

退出码 `0` = 必需依赖齐全可开工；`1` = 缺必需依赖（主流程走不通，按提示装）；可选依赖缺失只影响对应输入形态，不阻断电子版 PDF 主路径。

## 执行流程

所有脚本均支持 `--help`，参数优先于环境变量；不带参数运行 = 沿用环境变量的原有行为。

1. **识别输入形态**：遍历 `REPORT_DIR`
   - 根目录 `*.pdf` 含文本层 → 电子版（`parse_reports.py` 处理）
   - 根目录 `*.pdf` 无文本层 → 扫描件（`vision_ocr.py` + `extract.py`）
   - 年度子目录 `YYYY体检报告/*.JPG` → 照片版（`make_year_pdfs.py` 合成 → OCR → `extract.py`）
2. **解析电子版 PDF**（坐标定位法，列边界见 `references/解析与口径.md`）：
   ```bash
   $PY scripts/parse_reports.py                        # → data/reports_raw.json
   $PY scripts/parse_reports.py --year 2027 --dry-run  # 单年份试跑，不写盘
   ```
3. **照片版合成 PDF + OCR + 提取**（如存在 JPG 目录 / 扫描件）：
   ```bash
   $PY scripts/make_year_pdfs.py --year 2015-2020      # 年度多张 JPG → 单份 PDF（横拍自动旋转校正）
   $PY scripts/vision_ocr.py <pdf> data/ocr_2022.json  # 扫描件/照片 OCR → 带坐标 JSON
   $PY scripts/extract.py --year 2022                  # OCR 结果 → 指标（策略自动判定）
   $PY scripts/extract.py --years 2015-2020            # 多年份 dict 型 OCR（缩写+参考范围反推）
   ```
   `extract.py` **按年份参数化，新年份无需改代码**：放入 `data/ocr_<年份>.json` 后直接 `--year <年份>`。
   策略默认 `auto`（输入 JSON 顶层为 dict → `abbr`，为 list → `row`），可用 `--strategy` 强制。
4. **归一化 + 构建数据集**（名称/单位映射、脏数据过滤、OCR 自动注入、生成脱敏版）：
   ```bash
   $PY scripts/build_dataset.py
   ```
   产出 `data/dataset_std.json`（完整版，本地受控）+ `data/anonymized/anonymized_dataset_anon_shareable.json`（脱敏版，独立子目录 + 只读 444 + 可分享）
5. **趋势分析**（当年口径判定异常、显著变化 ≥20% 或 ≥参考宽度 30%、趋好/趋坏、近三年聚焦）：
   ```bash
   $PY scripts/trend_analysis.py                        # 默认近三年
   $PY scripts/trend_analysis.py --focus-years 2020,2023,2026
   ```
6. **生成交付物**：
   ```bash
   $PY scripts/report_generator.py    # output/体检指标趋势分析报告.md（默认**开启**正文脱敏）
   $PY scripts/build_dashboard.py     # output/health_dashboard.html（单文件离线）
   ```

## 新报告接入指南

新增年度体检报告时，按形态走对应分支（详见 `references/新报告接入指南.md`）：

1. **放入报告**：`REPORT_DIR` 根目录放 `*.pdf`，或建年度目录 `YYYY体检报告/` 放 JPG
2. **识别形态**：检查 PDF 文本层（`get_text()` 长度 >0 = 电子版）
   - 电子版 → 直接跑 `parse_reports.py`；列边界异常时先打印 1 页坐标样本
   - 扫描件/照片 → `make_year_pdfs.py` → `vision_ocr.py` → **`extract.py --year <年份>`**（不要新建按年份的脚本）
3. **补字典**（如有未收录指标）：`indicator_dict.py` 的 `NAME_MAP` 补一行映射（日志见 `data/unrecognized`）
   ```bash
   $PY scripts/indicator_dict.py --search 尿酸      # 查是否已收录（含别名）
   $PY scripts/indicator_dict.py --validate         # 自检字典完整性（悬空别名/重复键）
   $PY scripts/indicator_dict.py --count            # 当前标准指标总数
   ```
4. **重跑流水线**：build_dataset → trend_analysis → report_generator → build_dashboard
5. **验收**：确认新年份出现在 `trend_analysis.json["years"]` 与工作台时间轴；抽查 3 个关键指标数值与报告一致；生成并校验脱敏版

## 关键规则

- **隐私硬约束**（零容忍）：全程本地，技能内不含任何外发网络调用；任务完成必须生成并校验脱敏版（不含姓名/证件号/电话/地址/医院），分享只用 `data/anonymized/anonymized_dataset_anon_shareable.json`（与完整版 `dataset_std.json` 分目录强隔离、只读 444，防止误分享完整版）
- **脱敏校验先于写盘**：`build_dataset.py` 的 `_write_anon_verified()` 是脱敏版落盘的唯一出口——先在内存校验、通过后才写盘。脱敏版落盘即置只读 444，若校验在写盘之后，命中身份信息时带 PII 的文件已留在磁盘且改不动，`[FAIL]` 只是事后告警。禁止绕过该出口直接调 `_write_anon()`；`--skip-verify` 仅供排查，产物不可分享
- **报告正文脱敏**：`report_generator.py` 的 `mask_identity_text` 默认开启（机构名称、医师姓名、手机号、身份证号掩码）；`--no-mask` 才关闭，仅供本地核对原文，生成物切勿分享
- **新增年度报告**：放入 `REPORT_DIR` → 重跑 2→6 步即可；字典未收录指标在 `data/unrecognized` 记录，补 `indicator_dict.py` 的 `NAME_MAP` 一行即可
- **OCR 数据定位**：OCR 提取的指标只用于图表展示（灰色 Ⓞ 标注），**不参与显著变化判定**，避免污染统计
- **趋势聚焦**：整体趋势与首末对比仅基于聚焦年份（默认近三年，可用 `--focus-years` 覆盖），历史数据仅作展示背景
- **口径一致性**：异常判定用**当年报告自带参考范围**（试剂更换自动适配，如直接胆红素 2025 年起 0.0–4.0 → 1.7–6.8）

## 交付物

- `output/体检指标趋势分析报告.md` — 指标汇总表、异常高亮、权威解读、分层建议（生活方式/饮食/运动/就医指征）、方法学
- `output/health_dashboard.html` — 健康总览、趋好/趋坏分组筛选、折线图+参考范围带、时间跨度切换（单文件、无外部依赖）
- `data/anonymized/anonymized_dataset_anon_shareable.json` — 可分享脱敏数据集

## 脚本一览

| 脚本 | 用途 | 主要参数 |
|---|---|---|
| `check_deps.py` | 依赖自检（Step 0） | `--json` `--quiet` |
| `parse_reports.py` | 电子版 PDF 解析 | `--report-dir` `--data-dir` `--year` `--out` `--dry-run` |
| `make_year_pdfs.py` | 年度 JPG → PDF | `--report-dir` `--year` `--out-dir` `--dry-run` |
| `vision_ocr.py` | 扫描件/照片 OCR | `pdf` `out`（位置参数）`--dpi` `--quiet` |
| `extract.py` | OCR 结果 → 指标（参数化） | `--year` `--strategy` `--ocr-json` `--out` `--data-dir` `--quiet` |
| `build_dataset.py` | 归一化 + 脱敏版 | `--work-dir` `--data-dir` `--out` `--skip-verify` `--dry-run` |
| `trend_analysis.py` | 趋势判定 | `--work-dir` `--focus-years` `--out` `--dry-run` |
| `report_generator.py` | Markdown 报告 | `--work-dir` `--out` `--no-mask` `--dry-run` |
| `build_dashboard.py` | HTML 工作台 | `--work-dir` `--data-dir` `--out` `--quiet` |
| `indicator_dict.py` | 指标字典（被 import） | `--list` `--search` `--count` `--validate` `--category`（仅在直接运行时生效） |

退出码统一为三态：`0` 成功 / `1` 运行期失败 / `2` 参数或前置条件不满足。

## 参考文档

| 文档 | 内容 |
|---|---|
| `references/新报告接入指南.md` | 新形态/新年份报告接入的完整步骤与排错 |
| `references/解析与口径.md` | 电子版 PDF 的列边界坐标、口径定义 |
| `references/OCR方法学.md` | 扫描件/照片 OCR 策略、缩写映射表维护 |
| `evals/` | 8 条回归评测（含 3 条隐私防线），`eval_loop.py --run` 可跑 |

## 使用示例（一次完整会话）

**用户**：「帮我把 2027 年体检报告加进去，更新趋势分析。」

1. Step 0：`python3 scripts/check_deps.py` → 必需依赖齐全
2. 检查 `REPORT_DIR`：发现新文件 `体检报告_270510004567.pdf`（电子版，文本层完整）
3. 小样本确认列边界：打印 1 页坐标，与 `references/解析与口径.md` 一致 → 无需调整
4. 跑流水线：
   ```
   export REPORT_DIR=体检报告 WORK_DIR=/path/to/work
   python3 scripts/parse_reports.py
   python3 scripts/build_dataset.py
   python3 scripts/trend_analysis.py
   python3 scripts/report_generator.py
   python3 scripts/build_dashboard.py
   ```
5. 解析日志显示：新年度 98 项指标，1 个未识别名 → `indicator_dict.py --search` 确认未收录，在 `NAME_MAP` 补 1 行后重跑 build_dataset
6. 验收：`trend_analysis.json["years"]` 含 2027；工作台时间轴出现 2027；抽查血糖/血脂/BMI 数值与报告一致；`grep` 脱敏版无身份信息
7. 交付：报告 + 工作台路径告知用户；说明 2027 年各异常指标的变化与建议

## 降本纪律（执行时强制）

1. **小样本先行**：解析新格式前先打印 1 页坐标样本确认列边界，再全量处理（避免整文件 dump）
2. **输出压缩**：调试命令统一 `| head -N` / `python -c` 精准提取，禁止整文件 cat 大 JSON
3. **子代理隔离**：大文件读取/格式探测交给 Explore 子代理，主线程只收结论
4. 验证只做一次最终截图，中间迭代用 DOM/JS 检查替代

## Changelog

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.1.0 | 2026-08-29 | **工程化集中整改**：① 全部 10 脚本支持 `--help` + argparse + 退出码三态（整改前 0/10，全场最差）；② 新增 `check_deps.py` 依赖自检并写入 Step 0；③ 按年份硬编码的 `extract_2015_2020.py` / `extract_2022.py` 合并为参数化 `extract.py --year`（新年份接入不再改代码，输出格式与旧脚本逐字段一致）；④ 新增 `## 触发词` 章节 12 条 + `evals/` 8 条回归（含 3 条隐私防线用例）；⑤ **隐私修复**：脱敏版改为「先内存校验、通过后才写盘」（原为写盘后校验，命中 PII 时带身份信息的文件已落盘且只读，[FAIL] 只是事后告警）；⑥ 修复 `trend_analysis.py` 丢失测量项的死代码（`measurement_items` 追加后被重置，改为按 key 去重） |
| 1.0.3 | 2026-08-23 | **P2 M-1 整改（技能安全）**：脱敏版强隔离——`anonymized_dataset.json` → `data/anonymized/anonymized_dataset_anon_shareable.json`（独立子目录 + 只读 444 + `_anon_shareable` 命名标记），防止完整版与脱敏版混放误分享；`build_dataset.py` 新增 `_write_anon()`（tmp+replace 原子写入 + chmod 444）；report_generator 隐私声明路径同步 |
| 1.0.2 | 2026-08-17 | P1 整改：`build_dataset.py` 末尾新增 `verify_anonymized` 自动校验（身份证/手机号/邮箱/医院名正则扫描，命中即报错退出） |
| 1.0.1 | 2026-08-17 | P0 整改：`report_generator.py` 新增 `mask_identity_text` 脱敏函数（手机号/身份证/医师署名掩码 + 机构泛化），小结/结论文本展示层脱敏；隐私声明与实际输出对齐 |
| 1.0.0 | 2026-08-16 | 初版：体检指标趋势分析系统 |
