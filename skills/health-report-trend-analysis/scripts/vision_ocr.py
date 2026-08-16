#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
macOS Vision framework OCR（中文 + 英文）
输入：PDF 路径
输出：每页文字列表 [(text, x0, y0, x1, y1), ...] 像素坐标（左上原点）
"""
import sys, os, json
import pymupdf
from Foundation import NSURL
from Vision import VNImageRequestHandler, VNRecognizeTextRequest
from Quartz import CGImageSourceCreateWithURL, CGImageSourceCreateImageAtIndex, CGImageGetWidth, CGImageGetHeight

def ocr_image(png_path):
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

def ocr_pdf(pdf_path, out_json=None, dpi=300):
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
        print(f"第{i+1}页: {len(lines)} 文字  ({w}x{h})")
    if out_json:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(pages_data, f, ensure_ascii=False, indent=1)
        print(f"已保存: {out_json}")
    return pages_data

if __name__ == "__main__":
    pdf = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OCR_PDF", "report.pdf")  # 必填：PDF 路径
    out = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("OCR_OUT", "ocr_output.json")  # 可配：输出路径
    ocr_pdf(pdf, out)