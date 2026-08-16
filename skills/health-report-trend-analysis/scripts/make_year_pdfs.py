#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将各年度多张 JPG 体检报告照片合成单份 PDF
- 2015-2020 每年多张 4032x3024 横拍照片（文字顺时针旋转 90°）
- 逆时针旋转 90° 校正为竖版后合成 PDF
- 输出到 体检报告/YYYY体检报告.pdf
"""
import os
from PIL import Image

REPORT_DIR = os.environ.get("REPORT_DIR", "体检报告")  # 可配：REPORT_DIR 指向报告目录

def make_pdf(year):
    folder = os.path.join(REPORT_DIR, f"{year}体检报告")
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
    out_path = os.path.join(REPORT_DIR, f"{year}体检报告.pdf")
    images[0].save(out_path, "PDF", save_all=True, append_images=images[1:], resolution=150)
    size = os.path.getsize(out_path) / 1024 / 1024
    return out_path, len(images), size

def main():
    for year in [2015, 2016, 2017, 2018, 2019, 2020]:
        result = make_pdf(year)
        if result:
            path, n, size = result
            print(f"✓ {year}: {n} 张图 → {path} ({size:.1f} MB)")
        else:
            print(f"✗ {year}: 无文件")

if __name__ == "__main__":
    main()
