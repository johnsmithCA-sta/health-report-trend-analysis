#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将各年度多张 JPG 体检报告照片合成单份 PDF
- 2015-2020 每年多张 4032x3024 横拍照片（文字顺时针旋转 90°）
- 逆时针旋转 90° 校正为竖版后合成 PDF
- 输出到 <out-dir>/YYYY体检报告.pdf（默认 <report-dir>/YYYY体检报告.pdf）

依赖 Pillow，仅在真正合成 PDF 时导入（--help 不依赖）
"""
import argparse
import os
import sys

DEFAULT_REPORT_DIR = os.environ.get("REPORT_DIR", "体检报告")  # 可配：REPORT_DIR 指向报告目录
REPORT_DIR = DEFAULT_REPORT_DIR  # 保留旧全局名，供既有 import / 运行时改写
DEFAULT_YEARS = [2015, 2016, 2017, 2018, 2019, 2020]
YEAR_MIN, YEAR_MAX = 1990, 2100


def _to_int(text):
    """年份字符串 → int；非法返回 None"""
    try:
        return int(str(text).strip())
    except (TypeError, ValueError):
        return None


def parse_years(values):
    """解析年份参数，支持 2015 / 2015,2016 / 2015-2020 / 多次传入；非法返回 None"""
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


def make_pdf(year, report_dir=None, out_dir=None, dry_run=False):
    """将 <report-dir>/<year>体检报告/ 下的 JPG 合成 <out-dir>/<year>体检报告.pdf

    返回 (输出路径, 图片张数, 文件大小MB)；无文件时返回 None。
    未传 report_dir / out_dir 时沿用模块级 REPORT_DIR（保持原行为）。
    """
    try:
        from PIL import Image
    except ImportError as e:
        print(f"[错误] 缺少依赖 Pillow: {e}（安装：pip install pillow）")
        return None

    report_dir = report_dir or REPORT_DIR
    out_dir = out_dir or report_dir
    folder = os.path.join(report_dir, f"{year}体检报告")
    if not os.path.isdir(folder):
        return None
    files = sorted(f for f in os.listdir(folder) if f.upper().endswith(".JPG"))
    if not files:
        return None
    images = []
    for fn in files:
        img = Image.open(os.path.join(folder, fn))
        if img.mode != "RGB":
            img = img.convert("RGB")
        # 照片横拍（宽>高且文字需右转 90°）：顺时针旋转 90° 转竖版
        if img.width > img.height:
            img = img.rotate(-90, expand=True)  # 顺时针 90°
        images.append(img)
    out_path = os.path.join(out_dir, f"{year}体检报告.pdf")
    if dry_run:
        return out_path, len(images), None
    images[0].save(out_path, "PDF", save_all=True, append_images=images[1:], resolution=150)
    size = os.path.getsize(out_path) / 1024 / 1024
    return out_path, len(images), size


def build_parser():
    parser = argparse.ArgumentParser(
        prog="make_year_pdfs.py",
        description="将各年度多张 JPG 体检报告照片合成单份 PDF（默认处理 2015-2020）",
        epilog="""
示例:
  python3 scripts/make_year_pdfs.py                                  # 按 $REPORT_DIR（默认 体检报告）处理 2015-2020
  python3 scripts/make_year_pdfs.py --report-dir ~/体检报告            # 指定报告目录
  python3 scripts/make_year_pdfs.py --year 2015,2016 --year 2018-2020 # 只处理指定年份
  python3 scripts/make_year_pdfs.py --out-dir /tmp/pdf --dry-run       # 试运行，不写文件
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--report-dir", metavar="目录", default=None,
                        help=f"体检报告根目录，其下为 <年份>体检报告/ 子目录（默认 $REPORT_DIR 或 体检报告，当前: {DEFAULT_REPORT_DIR}）")
    parser.add_argument("--year", metavar="年份", action="append", default=None,
                        help="只处理指定年份，支持 2015 / 2015,2016 / 2015-2020，可多次传入（默认 2015-2020）")
    parser.add_argument("--out-dir", metavar="目录", default=None,
                        help="PDF 输出目录，不存在时自动创建（默认与 --report-dir 相同）")
    parser.add_argument("--dry-run", action="store_true",
                        help="只打印将要合成的 PDF 与图片张数，不写文件")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    report_dir = args.report_dir or DEFAULT_REPORT_DIR
    if args.report_dir and not os.path.isdir(report_dir):
        parser.error(f"--report-dir 目录不存在: {report_dir}")

    out_dir = args.out_dir or report_dir
    if args.out_dir and os.path.exists(out_dir) and not os.path.isdir(out_dir):
        parser.error(f"--out-dir 已存在但不是目录: {out_dir}")

    if args.year:
        years = parse_years(args.year)
        if years is None:
            parser.error(f"--year 取值非法: {args.year}"
                         f"（需为 {YEAR_MIN}-{YEAR_MAX} 之间的年份，支持 2015、2015,2016、2015-2020）")
    else:
        years = list(DEFAULT_YEARS)

    if not args.dry_run:
        os.makedirs(out_dir, exist_ok=True)
    if not os.path.isdir(report_dir):
        print(f"[警告] 默认报告目录不存在: {report_dir}（可用 --report-dir 指定）")

    for year in years:
        result = make_pdf(year, report_dir=report_dir, out_dir=out_dir, dry_run=args.dry_run)
        if result:
            path, n, size = result
            if args.dry_run:
                print(f"✓ {year}: {n} 张图 → {path}（--dry-run 未写入）")
            else:
                print(f"✓ {year}: {n} 张图 → {path} ({size:.1f} MB)")
        else:
            print(f"✗ {year}: 无文件")

    if args.dry_run:
        print(f"[信息] --dry-run：未写入任何文件（待处理 {len(years)} 个年份 → {out_dir}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
