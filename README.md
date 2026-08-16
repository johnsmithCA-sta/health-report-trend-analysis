# health-report-trend-analysis

体检指标趋势分析系统：把多年度、多形态的体检报告统一解析为标准化指标时间序列，产出趋势分析报告 + 交互式健康管理工作台。全程本地处理、自动脱敏、动态扩展。

> 让历年"吃灰的体检报告"变成可追踪的健康趋势 —— 电子 PDF / 扫描件 / 照片三种形态统一解析，116 项指标逐年比对，异常变化一目了然。

## ✨ 功能特性

- **3 种输入形态**：电子版 PDF（文本层）、扫描件 PDF（无文本层）、照片 JPG（自动合成 PDF）
- **统一指标字典**：146 个原始指标名归一化到 116 个标准指标，跨年份/跨医院统一表达
- **历年趋势比对**：异常判定（当年报告自带参考范围）、显著变化（≥20% 或≥参考宽度 30%）、趋好/趋坏标注
- **权威医学解读**：默沙东诊疗手册 / 丁香医生 / 中国临床指南，分层建议（生活方式/饮食/运动/就医指征）
- **双交付物**：结构化 Markdown 报告 + 离线 HTML 工作台（SVG 折线图+参考范围带，无外部依赖）
- **隐私保护**：全程本地处理，自动生成脱敏数据集（仅指标数值+年份）
- **动态扩展**：新增年度报告重跑流水线即可，趋势聚焦近三年（可配置）

## 🔍 差异化说明 / Why This Project

与市面上"体检报告解读"类工具（医院 App 单年报告、通用 OCR 提取器等）相比，本项目不是又一款"单年报告阅读器"，而是一条**跨年度、多形态的趋势分析流水线**，核心差异化：

| 差异化点 | 本项目 | 同类工具 |
|---|---|---|
| **跨年度时间序列** | 自动对齐多年度报告为标准化指标序列，输出 5 年+ 趋势曲线与首末对比 | 多数只解读单年报告，无法跨年比对 |
| **三形态输入** | 电子 PDF / 扫描件 / 照片 JPG 统一接入（OCR + 参考范围反推） | 多数只支持单一格式 |
| **口径一致性** | 异常判定用**当年报告自带参考范围**（试剂更换自动适配），杜绝跨年误判 | 固定参考范围，试剂更换后误报 |
| **显著变化判定** | ≥20% 或 ≥参考宽度 30% 自动标注，OCR 数据灰色标注不污染统计 | 仅看升降，无变化显著性 |
| **隐私优先** | 全程本地处理，自动生成脱敏数据集（仅指标数值+年份）供分享 | 多需上传云端分析 |
| **AI Skill 形态** | 标准 Agent Skills 规范（agentskills.io），Agent 可直接驱动全流程 | 传统网页/App，无法被 Agent 调用 |

**一句话定位**：同类工具解决"看懂一份报告"，本项目解决"看懂你的健康轨迹"——自动把历年纸质/电子报告变成可检索、可追踪、可分享脱敏数据集的健康资产。

## 📦 快速开始

```bash
# 1. 设置环境变量
export REPORT_DIR=/path/to/体检报告目录      # 报告存放目录
export WORK_DIR=/path/to/工作数据目录        # 数据产物目录
export PY=python3                            # 建议用带依赖的 python

# 2. 解析（按输入形态选对应脚本）
$PY scripts/parse_reports.py                 # 电子版 PDF
$PY scripts/make_year_pdfs.py                # 照片 JPG → 合成 PDF（可选）
$PY scripts/extract_2022.py                  # 扫描件 OCR 提取（可选）

# 3. 归一化 + 趋势 + 交付
$PY scripts/build_dataset.py
$PY scripts/trend_analysis.py
$PY scripts/report_generator.py
$PY scripts/build_dashboard.py
```

## 🗂 目录结构

```
health-report-trend-analysis/
├── skills/
│   └── health-report-trend-analysis/   # Agent Skills 规范（agentskills.io）
│       ├── SKILL.md                    # 技能行为规范
│       ├── scripts/                    # 可执行脚本（10 个）
│       └── references/                 # 解析口径 / OCR 方法学 / 新报告接入 / 降本纪律
├── README.md
├── LICENSE
└── CONTRIBUTING.md
```

## 依赖

- Python 3.8+
- `pymupdf`（PDF 文本层解析）
- `Pillow`（照片合成 PDF）
- macOS `Vision` framework via `pyobjc-framework-Vision`（扫描件/照片 OCR，仅 macOS）

## 免责声明

本系统为健康管理参考工具，依据公开医学权威来源整理指标解读建议，**不构成诊疗意见**。OCR 提取的指标准确率有限，趋势参考为主。如指标持续异常或伴不适症状，请及时就医。

## License

MIT
