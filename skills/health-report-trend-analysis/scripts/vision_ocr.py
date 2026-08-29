#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS Vision framework OCR（中文 + 英文）
输入：PDF 路径
输出：每页文字列表 [(text, x0, y0, x1, y1), ...] 像素坐标（左上原点）

依赖仅在真正 OCR 时导入（--help 不需要）：
  pip install pymupdf pyobjc-framework-Vision pyobjc-framework-Quartz
"""
import argparse
import json
import os
import sys

DEFAULT_PDF = os.environ.get("OCR_PDF", "report.pdf")      # 可配：默认输入 PDF
DEFAULT_OUT = os.environ.get("OCR_OUT", "ocr_output.json")  # 可配：默认输出 JSON
DEFAULT_DPI = 300
DPI_MIN, DPI_MAX = 72, 1200


def ocr_image(png_path):
    from Foundation import NSURL
    from Vision import VNImageRequestHandler, VNRecognizeTextRequest
    from Quartz import (CGImageSourceCreateWithURL, CGImageSourceCreateImageAtIndex,
                        CGImageGetWidth, CGImageGetHeight)
    url = NSURL.fileURLWithPath_(png_path)
    src = CGImageSourceCreateWithURL(url, None)
    img = CGImageSourceCreateImageAtIndex(src, 0, None)
    if img is None:
        return [], 0, 0
    w = CGImageGetWidth(img)
    h = CGImageGetHeight(img)
    req = VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(1)  # accurate
    req.setUsesLanguageCorrection_(False)
    req.setRecognitionLanguages_(["zh-Hans"])
    req.setMinimumTextHeight_(0.005)
    handler = VNImageRequestHandler.alloc().initWithCGImage_options_(img, {})
    err = None
    ok = handler.performRequests_error_([req], err)
    results = req.results() or []
    lines = []
    for obs in results:
        top = obs.topCandidates_(1)
        if not top:
            continue
        cand = top[0]
        text = cand.string()
        if not text.strip():
            continue
        bb = obs.boundingBox()  # normalized, 左下原点
        x0 = bb.origin.x * w
        y0 = (1 - bb.origin.y - bb.size.height) * h
        x1 = x0 + bb.size.width * w
        y1 = y0 + bb.size.height * h
        lines.append((text, x0, y0, x1, y1))
    return lines, w, h


def ocr_pdf(pdf_path, out_json=None, dpi=300, quiet=False):
    import pymupdf
    doc = pymupdf.open(pdf_path)
    pages_data = []
    tmpdir = "/tmp/ocr_tmp"
    os.makedirs(tmpdir, exist_ok=True)
    for i in range(len(doc)):
        page = doc[i]
        pix = page.get_pixmap(dpi=dpi)
        png = f"{tmpdir}/p{i+1}.png"
        pix.save(png)
        lines, w, h = ocr_image(png)
        pages_data.append({"page": i+1, "width": w, "height": h, "lines": lines})
        if not quiet:
            print(f"第{i+1}页: {len(lines)} 文字  ({w}x{h})")
    if out_json:
        parent = os.path.dirname(os.path.abspath(out_json))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(pages_data, f, ensure_ascii=False, indent=1)
        print(f"已保存: {out_json}")
    return pages_data


def build_parser():
    parser = argparse.ArgumentParser(
        prog="vision_ocr.py",
        description="用 macOS Vision 框架对体检报告 PDF 做 OCR，输出每页文字与坐标 JSON",
        epilog="""
示例:
  python3 scripts/vision_ocr.py 体检报告/2022体检报告.pdf ocr/2022.json    # OCR 并写出 JSON
  python3 scripts/vision_ocr.py 体检报告/2022体检报告.pdf --dpi 200 --quiet  # 降低分辨率、不打印逐页进度
  OCR_PDF=report.pdf python3 scripts/vision_ocr.py                         # 沿用环境变量默认输入
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("pdf", nargs="?", default=None,
                        help=f"待 OCR 的 PDF 路径（省略时取 $OCR_PDF，再缺省 {DEFAULT_PDF}）")
    parser.add_argument("out", nargs="?", default=None,
                        help=f"输出 JSON 路径，父目录自动创建（省略时取 $OCR_OUT，再缺省 {DEFAULT_OUT}）")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI,
                        help=f"渲染 DPI，越高越准也越慢（默认 {DEFAULT_DPI}，允许 {DPI_MIN}-{DPI_MAX}）")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="不打印逐页进度（仍打印最终输出路径，便于管道取用）")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    pdf = args.pdf or DEFAULT_PDF
    out = args.out or DEFAULT_OUT
    if args.pdf is not None and not os.path.isfile(pdf):
        parser.error(f"PDF 文件不存在: {pdf}")
    if not os.path.isfile(pdf):
        print(f"[错误] PDF 文件不存在: {pdf}（用位置参数传入，或设置 $OCR_PDF）")
        return 1
    if not (DPI_MIN <= args.dpi <= DPI_MAX):
        parser.error(f"--dpi 需为 {DPI_MIN}-{DPI_MAX} 之间的整数，当前: {args.dpi}")

    try:
        ocr_pdf(pdf, out, dpi=args.dpi, quiet=args.quiet)
    except ImportError as e:
        print(f"[错误] 缺少 OCR 依赖: {e}")
        print("[信息] 安装：pip install pymupdf pyobjc-framework-Vision pyobjc-framework-Quartz（仅 macOS）")
        return 1
    except Exception as e:
        print(f"[错误] OCR 失败: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
