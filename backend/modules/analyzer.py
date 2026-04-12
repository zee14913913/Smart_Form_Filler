"""
analyzer.py
-----------
文档分析引擎：上传 PDF 或图片后，自动识别所有填写格子的：
  - 精确坐标（cell_x0, cell_top, cell_x1, cell_bottom）
  - 旁边的标签文字（raw_label）
  - 所在页码（page_number）

支持两种输入：
  A. 数字 PDF（可选中文字）：使用 pdfplumber 提取表格格线
  B. 扫描 PDF / 图片 PDF：使用 pdf2image → OpenCV 格线检测 + pytesseract OCR

输出统一格式 list[dict]，每个 dict 包含：
  {
      "page_number": int,
      "cell_x0": float,   # PDF 点坐标（1pt = 1/72 英寸）
      "cell_top": float,
      "cell_x1": float,
      "cell_bottom": float,
      "raw_label": str,   # 格子旁的标签文字（可能为空）
      "cell_width": float,
      "cell_height": float,
  }
"""

import os
import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  主入口
# ──────────────────────────────────────────────────────────────

def analyze_pdf(file_path: str) -> list[dict]:
    """
    分析 PDF 文件，返回所有检测到的填写字段列表。
    自动判断数字 PDF 还是扫描 PDF。
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")

    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"):
        # 图片直接走 OCR 路径
        return _analyze_image(file_path)
    elif suffix == ".pdf":
        if _is_digital_pdf(file_path):
            logger.info("检测为数字 PDF，使用 pdfplumber 提取")
            return _analyze_digital_pdf(file_path)
        else:
            logger.info("检测为扫描 PDF，使用 OCR 模式")
            return _analyze_scanned_pdf(file_path)
    else:
        raise ValueError(f"不支持的文件格式：{suffix}")


# ──────────────────────────────────────────────────────────────
#  数字 PDF 判断
# ──────────────────────────────────────────────────────────────

def _is_digital_pdf(file_path: str) -> bool:
    """
    判断 PDF 是否包含可提取文本（数字 PDF）。
    策略：用 pdfplumber 读第一页，若文字字符数 > 50 则视为数字 PDF。
    """
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                return False
            text = pdf.pages[0].extract_text() or ""
            return len(text.strip()) > 50
    except Exception as e:
        logger.warning(f"pdfplumber 判断失败，降级到 OCR 模式：{e}")
        return False


# ──────────────────────────────────────────────────────────────
#  数字 PDF 分析（pdfplumber）
# ──────────────────────────────────────────────────────────────

def _analyze_digital_pdf(file_path: str) -> list[dict]:
    """
    使用 pdfplumber 提取数字 PDF 的表格格线，识别填写格子。
    
    策略：
    1. 提取每页所有矩形线框（rects）
    2. 过滤出符合"填写格子"特征的矩形（高度 8-40pt、宽度 40-500pt）
    3. 在格子的左侧/上方寻找最近的文字作为 raw_label
    """
    import pdfplumber

    fields: list[dict] = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_height = page.height
            # 提取所有矩形框
            rects = page.rects or []
            words = page.extract_words() or []

            for rect in rects:
                x0 = rect.get("x0", 0)
                top = rect.get("top", 0)
                x1 = rect.get("x1", 0)
                bottom = rect.get("bottom", 0)

                w = x1 - x0
                h = bottom - top

                # 过滤：宽度 30-600pt，高度 6-60pt（填写格特征）
                if not (30 <= w <= 600 and 6 <= h <= 60):
                    continue

                # 寻找标签：在格子左边或上方找最近的文字
                raw_label = _find_nearby_label(words, x0, top, x1, bottom)

                fields.append({
                    "page_number": page_num,
                    "cell_x0": round(x0, 2),
                    "cell_top": round(top, 2),
                    "cell_x1": round(x1, 2),
                    "cell_bottom": round(bottom, 2),
                    "cell_width": round(w, 2),
                    "cell_height": round(h, 2),
                    "raw_label": raw_label,
                })

    # 去重：完全相同坐标的格子（pdfplumber 有时会重复）
    fields = _deduplicate_fields(fields)
    logger.info(f"数字 PDF 分析完成，共发现 {len(fields)} 个字段")
    return fields


def _find_nearby_label(words: list[dict], x0: float, top: float, x1: float, bottom: float) -> str:
    """
    在 words 列表中查找格子上方或左侧的全部标签词汇，拼接为完整标签字符串。

    策略（改进版）：
    1. 优先找格子正上方一行（top - 20pt 到 top）内、水平与格子重叠的所有词，
       按 x0 排序后拼接成完整标签。
    2. 若上方无词，再找同行左侧最近的词。
    """
    mid_y = (top + bottom) / 2

    # ── 策略 1：格子正上方一行内的所有词 ──────────────────────────
    label_row_top = top - 22      # 向上最多 22pt（约一行文字高度）
    label_row_bottom = top        # 不超过格子顶部
    above_words = []
    for word in words:
        wx0 = word.get("x0", 0)
        wx1 = word.get("x1", 0)
        wtop = word.get("top", 0)
        wbottom = word.get("bottom", 0)
        text = word.get("text", "").strip()
        if not text:
            continue
        # 垂直上方范围
        if label_row_top <= wtop <= label_row_bottom:
            # 水平：从格子左边 x0 起，最多延伸到格子右边 x1 + 20pt
            if wx0 >= x0 - 5 and wx1 <= x1 + 20:
                above_words.append((wx0, text))

    if above_words:
        above_words.sort(key=lambda t: t[0])
        return " ".join(t[1] for t in above_words)

    # ── 策略 2：同行左侧最近的单词 ────────────────────────────────
    best_label = ""
    best_dist = float("inf")
    for word in words:
        wx0 = word.get("x0", 0)
        wx1 = word.get("x1", 0)
        wtop = word.get("top", 0)
        wbottom = word.get("bottom", 0)
        text = word.get("text", "").strip()
        if not text:
            continue
        wmid_y = (wtop + wbottom) / 2
        if wx1 <= x0 + 2 and abs(wmid_y - mid_y) <= 8:
            dist = x0 - wx1
            if dist < best_dist:
                best_dist = dist
                best_label = text

    return best_label


# ──────────────────────────────────────────────────────────────
#  扫描 PDF 分析（OCR）
# ──────────────────────────────────────────────────────────────

def _analyze_scanned_pdf(file_path: str) -> list[dict]:
    """
    使用 pdf2image 将 PDF 转为图片，再通过 OpenCV + pytesseract 识别格线与文字。
    
    TODO（生产部署）：
    - 确认 Tesseract 已安装并配置 TESSDATA_PREFIX 环境变量
    - pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'
    - 可添加中文语言包：tessdata/chi_sim.traineddata
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise RuntimeError("请安装 pdf2image：pip install pdf2image（同时需要系统安装 poppler）")

    # TODO: 生产环境需配置 poppler_path（Windows）或确认 Linux 已安装
    images = convert_from_path(file_path, dpi=150)
    
    fields: list[dict] = []
    for page_num, img in enumerate(images, start=1):
        page_fields = _analyze_image_pil(img, page_num)
        fields.extend(page_fields)

    logger.info(f"扫描 PDF 分析完成，共发现 {len(fields)} 个字段")
    return fields


def _analyze_image(file_path: str) -> list[dict]:
    """分析单张图片文件"""
    from PIL import Image
    img = Image.open(file_path)
    return _analyze_image_pil(img, page_number=1)


def _analyze_image_pil(img, page_number: int) -> list[dict]:
    """
    用 OpenCV 格线检测 + pytesseract OCR 分析单张图片。
    坐标单位：PDF 点（72dpi）—— 通过 dpi=150 换算：pt = px * 72 / 150
    """
    import numpy as np
    import cv2
    try:
        import pytesseract
    except ImportError:
        raise RuntimeError("请安装 pytesseract 并安装 Tesseract OCR")

    # PIL → numpy BGR
    img_np = np.array(img.convert("RGB"))
    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    h_img, w_img = gray.shape

    # 二值化
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    # 形态学检测水平线和垂直线
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
    horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)
    vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)

    # 合并格线
    grid = cv2.add(horizontal_lines, vertical_lines)
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # DPI 换算系数（150dpi → 72pt）
    scale = 72.0 / 150.0

    # OCR 全页文字（用于标签提取）
    # TODO: 生产环境添加 lang='chi_sim+eng' 支持中文
    try:
        ocr_data = pytesseract.image_to_data(
            img,
            output_type=pytesseract.Output.DICT,
            config="--psm 11",
        )
    except Exception as e:
        logger.warning(f"OCR 识别失败（可能未安装 Tesseract）：{e}")
        ocr_data = {"text": [], "left": [], "top": [], "width": [], "height": [], "conf": []}

    # 构建 word 列表
    ocr_words = []
    for i, text in enumerate(ocr_data.get("text", [])):
        if text.strip() and int(ocr_data["conf"][i]) > 30:
            ocr_words.append({
                "x0": ocr_data["left"][i],
                "top": ocr_data["top"][i],
                "x1": ocr_data["left"][i] + ocr_data["width"][i],
                "bottom": ocr_data["top"][i] + ocr_data["height"][i],
                "text": text.strip(),
            })

    fields = []
    for cnt in contours:
        rx, ry, rw, rh = cv2.boundingRect(cnt)
        # 过滤太小或太大的格子（像素单位）
        if not (60 <= rw <= 1200 and 15 <= rh <= 120):
            continue

        # 转换为 PDF 点坐标
        x0_pt = rx * scale
        top_pt = ry * scale
        x1_pt = (rx + rw) * scale
        bottom_pt = (ry + rh) * scale

        # 在 OCR 词列表里寻找标签（像素坐标）
        raw_label = _find_ocr_label(ocr_words, rx, ry, rx + rw, ry + rh)

        fields.append({
            "page_number": page_number,
            "cell_x0": round(x0_pt, 2),
            "cell_top": round(top_pt, 2),
            "cell_x1": round(x1_pt, 2),
            "cell_bottom": round(bottom_pt, 2),
            "cell_width": round(rw * scale, 2),
            "cell_height": round(rh * scale, 2),
            "raw_label": raw_label,
        })

    return _deduplicate_fields(fields)


def _find_ocr_label(words: list[dict], x0: float, top: float, x1: float, bottom: float) -> str:
    """在 OCR 词列表中寻找格子左侧或上方的标签（像素坐标版）"""
    best_label = ""
    best_dist = float("inf")
    mid_y = (top + bottom) / 2

    for word in words:
        wx0 = word["x0"]
        wx1 = word["x1"]
        wtop = word["top"]
        wbottom = word["bottom"]
        text = word["text"]
        wmid_y = (wtop + wbottom) / 2

        # 左侧标签
        if wx1 <= x0 + 5 and abs(wmid_y - mid_y) <= 15:
            dist = x0 - wx1
            if 0 <= dist < best_dist:
                best_dist = dist
                best_label = text

        # 上方标签
        elif wtop < top and top - wbottom <= 30:
            if wx0 < x1 and wx1 > x0:
                dist = top - wbottom
                if dist < best_dist:
                    best_dist = dist
                    best_label = text

    return best_label


# ──────────────────────────────────────────────────────────────
#  工具函数
# ──────────────────────────────────────────────────────────────

def _deduplicate_fields(fields: list[dict]) -> list[dict]:
    """
    去除坐标几乎相同的重复格子（允许 2pt 误差）。
    保留第一次出现的记录。
    """
    seen = []
    result = []
    for f in fields:
        key = (
            f["page_number"],
            round(f["cell_x0"] / 2) * 2,
            round(f["cell_top"] / 2) * 2,
        )
        if key not in seen:
            seen.append(key)
            result.append(f)
    return result
