#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
依赖自检（Step 0）——每个新会话第一步就该跑这个。

体检：
  必需依赖  缺失 → 主流程走不通，退出码 1
  可选依赖  缺失 → 只影响某个输入形态分支，告警但不阻断，退出码仍为 0
  本地模块  indicator_dict 必须可 import（build_dataset / trend_analysis 依赖它）

用法见 --help。
"""
import argparse
import importlib.util
import os
import platform
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))

# 依赖 → (pip 包名, 导入名, 影响的脚本, 影响的输入形态, 是否必需)
DEPS = [
    {
        "name": "pymupdf", "import": "pymupdf", "pip": "pymupdf", "required": True,
        "scripts": ["parse_reports.py", "vision_ocr.py"],
        "affects": "电子版 PDF（含文本层）解析 —— 主路径，缺失则整个流水线无法启动",
    },
    {
        "name": "Pillow", "import": "PIL", "pip": "Pillow", "required": False,
        "scripts": ["make_year_pdfs.py"],
        "affects": "照片版报告（JPG）合成 PDF",
    },
    {
        "name": "pyobjc-framework-Vision", "import": "Vision", "pip": "pyobjc-framework-Vision",
        "required": False, "platform": "Darwin",
        "scripts": ["vision_ocr.py"],
        "affects": "扫描件 PDF / 照片版 OCR 识别（依赖 macOS Vision 框架，仅 macOS 可用）",
    },
    {
        "name": "pyobjc-framework-Quartz", "import": "Quartz", "pip": "pyobjc-framework-Quartz",
        "required": False, "platform": "Darwin",
        "scripts": ["vision_ocr.py"],
        "affects": "扫描件 PDF / 照片版 OCR 识别（图像解码）",
    },
]

LOCAL_MODULES = ["indicator_dict"]


def check_import(import_name):
    """模块能否 import。返回 (ok, 版本字符串)"""
    try:
        spec = importlib.util.find_spec(import_name)
    except (ImportError, ValueError):
        return False, ""
    if spec is None:
        return False, ""
    try:
        mod = importlib.import_module(import_name)
        return True, getattr(mod, "__version__", "") or ""
    except Exception:
        # find_spec 能找到但 import 失败：通常是二进制依赖缺失
        return False, ""


def run_checks():
    """返回 (结果列表, 缺必需数, 缺可选数)"""
    results, missing_required, missing_optional = [], 0, 0
    sys.path.insert(0, SCRIPTS_DIR)
    for dep in DEPS:
        if dep.get("platform") and platform.system() != dep["platform"]:
            results.append({"name": dep["name"], "status": "不适用",
                            "reason": f"仅 {dep['platform']} 可用，当前 {platform.system()}",
                            "scripts": dep["scripts"], "required": False, "version": ""})
            continue
        ok, ver = check_import(dep["import"])
        results.append({"name": dep["name"], "status": "已安装" if ok else "缺失",
                        "version": ver, "scripts": dep["scripts"],
                        "affects": dep["affects"], "required": dep["required"],
                        "pip": dep["pip"]})
        if not ok:
            if dep["required"]:
                missing_required += 1
            else:
                missing_optional += 1

    for name in LOCAL_MODULES:
        ok = importlib.util.find_spec(name) is not None
        results.append({"name": f"{name}.py（本地模块）", "status": "已就绪" if ok else "缺失",
                        "version": "", "scripts": ["build_dataset.py", "trend_analysis.py"],
                        "affects": "指标字典，归一化与趋势分析的基础", "required": True, "pip": ""})
        if not ok:
            missing_required += 1
    return results, missing_required, missing_optional


def build_parser():
    parser = argparse.ArgumentParser(
        prog="check_deps.py",
        description="体检报告分析流水线依赖自检：缺什么、影响哪几个脚本、怎么装",
        epilog="""
示例:
  python3 scripts/check_deps.py            # 人类可读报告
  python3 scripts/check_deps.py --json     # 机器可读，供 CI / 评测断言消费
  python3 scripts/check_deps.py --quiet    # 只在有问题时输出

退出码: 0 = 必需依赖齐全（可选依赖缺失仍为 0）
        1 = 缺必需依赖，主流程走不通
        2 = 参数错误
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="以 JSON 输出，供自动化消费")
    parser.add_argument("--quiet", "-q", action="store_true", help="全部就绪时不打印任何内容")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    results, miss_req, miss_opt = run_checks()

    if args.json:
        import json
        print(json.dumps({
            "platform": platform.system(),
            "python": sys.version.split()[0],
            "missing_required": miss_req,
            "missing_optional": miss_opt,
            "ok": miss_req == 0,
            "deps": results,
        }, ensure_ascii=False, indent=2))
        return 1 if miss_req else 0

    if args.quiet and miss_req == 0 and miss_opt == 0:
        return 0

    lines = [f"平台: {platform.system()}  Python: {sys.version.split()[0]}", ""]
    for r in results:
        mark = {"已安装": "✓", "已就绪": "✓", "缺失": "✗", "不适用": "–"}[r["status"]]
        tag = "必需" if r.get("required") else "可选"
        ver = f" {r['version']}" if r.get("version") else ""
        lines.append(f"  {mark} [{tag}] {r['name']}{ver} — {r['status']}"
                     + (f"（{r['reason']}）" if r.get("reason") else ""))
        if r["status"] == "缺失":
            lines.append(f"        影响脚本: {', '.join(r['scripts'])}")
            lines.append(f"        影响能力: {r['affects']}")
            if r.get("pip"):
                lines.append(f"        安装命令: pip install {r['pip']}")
    lines.append("")

    if miss_req:
        lines.append(f"[FAIL] 缺少 {miss_req} 个必需依赖，主流程无法启动。按上面的安装命令补齐后重跑本脚本。")
    else:
        lines.append("[PASS] 必需依赖齐全，可运行流水线。")
        if miss_opt:
            lines.append(f"[警告] 另有 {miss_opt} 个可选依赖缺失，仅影响对应输入形态（见上），不影响电子版 PDF 主路径。")

    print("\n".join(lines))
    return 1 if miss_req else 0


if __name__ == "__main__":
    sys.exit(main())
