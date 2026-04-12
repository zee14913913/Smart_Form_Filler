"""
filler.py
---------
PDF 精准回填引擎。

核心算法（按蓝图 §3.5）：
  1. 读取模板字段列表（坐标 + standard_key + 排版参数）
  2. 从客户数据 dict 中取出对应值
  3. 在透明 ReportLab overlay 上，按以下规则绘制每段文字：
     - 水平：x_start = cell_x0 + padding_left（≈ 一个字宽）
     - 垂直：y_center = cell_top + (cell_height - font_size) / 2
     - 字体从 font_size_max 开始，每次减 font_size_step，
       直到字符串宽度 ≤ 可用宽度（cell_width - padding_left - 2pt 右边距）
     - 若降到 font_size_min 仍放不下 → 标记 needs_manual=True，跳过该字段
  4. 将 overlay 与原 PDF 逐页合并，输出到 output_path

字体说明：
  - 中文内容需要内嵌中文字体；本实现使用 ReportLab 内置的 Helvetica 作为回退。
  - 生产环境建议注册支持中英文的 TTF 字体（如 NotoSansSC），
    放置于 backend/fonts/ 目录，然后取消注释下方 TODO 行。
"""

import io
import os
import logging
from pathlib import Path
from typing import Optional

from reportlab.pdfgen import canvas
from reportlab.lib.units import pt
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  字体注册
# ──────────────────────────────────────────────────────────────

FONT_NAME = "Helvetica"   # 默认回退字体（ASCII）

# TODO（生产部署）：注册支持中文的 TTF 字体
# FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
# FONT_PATH = os.path.join(FONT_DIR, "NotoSansSC-Regular.ttf")
# if os.path.exists(FONT_PATH):
#     pdfmetrics.registerFont(TTFont("NotoSansSC", FONT_PATH))
#     FONT_NAME = "NotoSansSC"


def _get_string_width(text: str, font_name: str, font_size: float) -> float:
    """计算字符串在指定字体和字号下的宽度（pt）"""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    return stringWidth(text, font_name, font_size)


# ──────────────────────────────────────────────────────────────
#  核心对外接口
# ──────────────────────────────────────────────────────────────

def fill_pdf(
    template_id: int,
    customer_data: dict,
    output_path: str,
    source_pdf_path: Optional[str] = None,
) -> dict:
    """
    主函数：将客户数据填入 PDF 模板并保存到 output_path。

    参数：
      template_id     — 模板 ID（从 SQLite 读取字段列表）
      customer_data   — {standard_key: value} 字典（来自 excel_reader）
      output_path     — 输出 PDF 文件路径
      source_pdf_path — 原始空白 PDF 路径（若为 None，从 uploads/ 自动找）

    返回：
      {
          "success": bool,
          "output_path": str,
          "filled_count": int,      # 成功填写字段数
          "manual_count": int,      # 需人工处理字段数
          "skipped_count": int,     # 无匹配值字段数
          "manual_fields": [...]    # 需人工处理的字段 raw_label 列表
      }
    """
    from modules.template_store import get_fields, get_template, update_field

    # 1. 读取模板信息
    template = get_template(template_id)
    if not template:
        raise ValueError(f"模板 {template_id} 不存在")

    # 2. 确定源 PDF 路径
    if source_pdf_path is None:
        source_pdf_path = _find_source_pdf(template)
    if not os.path.exists(source_pdf_path):
        raise FileNotFoundError(f"源 PDF 文件不存在：{source_pdf_path}")

    # 3. 读取字段列表
    fields = get_fields(template_id)
    if not fields:
        raise ValueError(f"模板 {template_id} 没有字段记录")

    # 4. 读取原始 PDF 页面信息
    reader = PdfReader(source_pdf_path)
    page_count = len(reader.pages)

    # 5. 按页分组字段
    pages_fields: dict[int, list[dict]] = {}
    for f in fields:
        pg = f.get("page_number", 1)
        pages_fields.setdefault(pg, []).append(f)

    # 6. 为每页生成 overlay
    overlays: dict[int, io.BytesIO] = {}
    filled_count = 0
    manual_count = 0
    skipped_count = 0
    manual_fields = []

    for page_idx in range(page_count):
        page_num = page_idx + 1
        pdf_page = reader.pages[page_idx]
        page_width = float(pdf_page.mediabox.width)
        page_height = float(pdf_page.mediabox.height)

        page_fields = pages_fields.get(page_num, [])
        if not page_fields:
            continue

        overlay_buf = io.BytesIO()
        c = canvas.Canvas(overlay_buf, pagesize=(page_width, page_height))

        for field in page_fields:
            std_key = field.get("standard_key", "")
            if not std_key:
                skipped_count += 1
                continue

            # 从客户数据中取值（支持带/不带 customer. 前缀）
            value = _get_field_value(customer_data, std_key)
            if value is None or value == "":
                skipped_count += 1
                continue

            result = _draw_text_in_cell(c, field, value, page_height)
            if result == "filled":
                filled_count += 1
            elif result == "manual":
                manual_count += 1
                manual_fields.append(field.get("raw_label", std_key))
                # 标记数据库
                update_field(field["id"], {"needs_manual": 1})

        c.save()
        overlay_buf.seek(0)
        overlays[page_num] = overlay_buf

    # 7. 合并 overlay 与原 PDF
    writer = PdfWriter()
    for page_idx in range(page_count):
        page_num = page_idx + 1
        original_page = reader.pages[page_idx]

        if page_num in overlays:
            overlay_reader = PdfReader(overlays[page_num])
            overlay_page = overlay_reader.pages[0]
            original_page.merge_page(overlay_page)

        writer.add_page(original_page)

    # 8. 写出文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f_out:
        writer.write(f_out)

    logger.info(
        f"填表完成：template_id={template_id}, "
        f"filled={filled_count}, manual={manual_count}, skipped={skipped_count}"
    )

    return {
        "success": True,
        "output_path": output_path,
        "filled_count": filled_count,
        "manual_count": manual_count,
        "skipped_count": skipped_count,
        "manual_fields": manual_fields,
    }


# ──────────────────────────────────────────────────────────────
#  文字绘制核心
# ──────────────────────────────────────────────────────────────

def _draw_text_in_cell(c, field: dict, value: str, page_height: float) -> str:
    """
    在 ReportLab canvas 上的指定格子区域内绘制文字。

    坐标说明：
      - PDF 坐标系：原点在左下角，y 轴向上。
      - pdfplumber/analyzer 使用的是"top-left 原点"坐标（y 轴向下）。
      - 需要将 top/bottom 转换：rl_y = page_height - pdf_top

    返回值：
      "filled"  — 成功绘制
      "manual"  — 字体降到最小仍放不下，需人工处理
    """
    x0 = field.get("cell_x0", 0.0)
    top = field.get("cell_top", 0.0)           # pdfplumber 坐标（从上往下）
    x1 = field.get("cell_x1", 0.0)
    bottom = field.get("cell_bottom", 0.0)

    font_size_max = field.get("font_size_max", 10.0)
    font_size_min = field.get("font_size_min", 6.0)
    font_size_step = field.get("font_size_step", 0.5)
    align = field.get("align", "left")

    cell_width = x1 - x0
    cell_height = bottom - top

    # 可用宽度：左侧留一个字宽（≈ font_size），右侧留 2pt
    # 初始以 font_size_max 估算 padding_left
    padding_left_ratio = 1.0   # 左侧留 1 个字宽

    # 尝试从最大字号开始
    font_size = font_size_max
    chosen_size = None
    while font_size >= font_size_min:
        padding_left = font_size * padding_left_ratio   # 左边留一个字宽
        available_width = cell_width - padding_left - 2.0  # 右边 2pt 安全边距
        if available_width <= 0:
            available_width = cell_width - 2.0
            padding_left = 0.0

        text_width = _get_string_width(value, FONT_NAME, font_size)
        if text_width <= available_width:
            chosen_size = font_size
            break
        font_size = round(font_size - font_size_step, 2)

    if chosen_size is None:
        # 降到最小字号后仍放不下
        return "manual"

    # 重新计算最终 padding_left
    final_padding_left = chosen_size * padding_left_ratio
    available_width = cell_width - final_padding_left - 2.0

    # 将 pdfplumber top-down 坐标转换为 ReportLab bottom-up 坐标
    # cell 顶部在 ReportLab 中的 y 坐标
    rl_cell_top = page_height - top
    rl_cell_bottom = page_height - bottom

    # 垂直居中：文字基线 = rl_cell_bottom + (cell_height - chosen_size) / 2
    # ReportLab 文字基线在字符底部，descent 约为字号的 0.2
    text_baseline = rl_cell_bottom + (cell_height - chosen_size) / 2

    # 水平对齐
    if align == "center":
        text_x = x0 + cell_width / 2
    elif align == "right":
        text_x = x1 - 2.0
    else:  # left（默认）
        text_x = x0 + final_padding_left

    # 设置字体颜色（深灰/黑）
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setFont(FONT_NAME, chosen_size)

    if align == "center":
        c.drawCentredString(text_x, text_baseline, value)
    elif align == "right":
        c.drawRightString(text_x, text_baseline, value)
    else:
        c.drawString(text_x, text_baseline, value)

    return "filled"


# ──────────────────────────────────────────────────────────────
#  辅助函数
# ──────────────────────────────────────────────────────────────

def _get_field_value(customer_data: dict, standard_key: str) -> Optional[str]:
    """
    从客户数据中获取字段值，支持两种键格式：
      - "customer.full_name"
      - "full_name"
    """
    if standard_key in customer_data:
        return customer_data[standard_key] or None
    # 尝试去掉前缀
    bare_key = standard_key.replace("customer.", "")
    return customer_data.get(bare_key) or None


def _find_source_pdf(template: dict) -> str:
    """根据模板记录推断源 PDF 路径"""
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    filename = template.get("source_filename", "")
    if filename:
        candidate = os.path.join(uploads_dir, filename)
        if os.path.exists(candidate):
            return candidate
    # 找不到时返回一个路径（会触发 FileNotFoundError）
    return os.path.join(uploads_dir, filename)
