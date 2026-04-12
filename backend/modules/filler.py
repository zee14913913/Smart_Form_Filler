"""
filler.py — PDF 精准回填引擎（v3）
------------------------------------
核心规则（PRD Master Prompt 严格版）：
  - 输出必须以 original.pdf 为底板，在其上叠加文字层。
  - 严禁创建空白 PDF 再重绘表格。
  - 所有排版参数从 system_settings 读取；字段级参数可覆盖全局。
  - 只允许两种 compute_layout 结果：
      "write"  — 正常写入
      "fail"   — 任何原因导致无法写入（值为空、超长、格子无效、字号最小仍溢出）
  - 任何 manual / skip / warning 状态均已废除。

流程：
  1. 读取 system_settings 全局配置
  2. 对每个字段调用 compute_layout() 计算排版
  3. status="write" → ReportLab 在透明 overlay 上绘字
  4. status="fail"  → 该字段不写入，记录 fail 原因
  5. 用 pypdf 将 overlay 合并到 original.pdf 各页
  6. 返回 fill_result（含字段级结果列表，供 verifier 使用）
"""

import io
import os
import logging
from pathlib import Path
from typing import Optional

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  字体注册
# ──────────────────────────────────────────────────────────────

_REGISTERED_FONTS: set[str] = set()
DEFAULT_FONT = "Helvetica"


def _ensure_font(font_name: str) -> str:
    """
    确保字体已注册。若字体是 Helvetica 等内置字体，直接返回。
    若是 TTF 路径，尝试注册。
    失败时回退到 Helvetica。
    """
    if font_name in ("Helvetica", "Times-Roman", "Courier"):
        return font_name
    if font_name in _REGISTERED_FONTS:
        return font_name
    # 尝试在 backend/fonts/ 找同名 TTF
    fonts_dir = os.path.join(os.path.dirname(__file__), "..", "fonts")
    candidates = [
        os.path.join(fonts_dir, f"{font_name}.ttf"),
        os.path.join(fonts_dir, f"{font_name}-Regular.ttf"),
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                _REGISTERED_FONTS.add(font_name)
                logger.info(f"已注册字体：{font_name} from {path}")
                return font_name
            except Exception as e:
                logger.warning(f"字体注册失败 {path}: {e}")
    logger.warning(f"字体 '{font_name}' 不可用，回退到 Helvetica")
    return DEFAULT_FONT


# ──────────────────────────────────────────────────────────────
#  compute_layout — PRD Master Prompt 严格两值逻辑
# ──────────────────────────────────────────────────────────────

def compute_layout(field: dict, value: str, settings: dict) -> dict:
    """
    根据字段坐标、值、全局 settings（以及字段级覆盖）计算排版参数。

    返回字典：
      status       : "write" | "fail"   ← 严格两值，无 manual/skip/warning
      font_name    : str
      font_size    : float
      text_x       : float   (ReportLab 坐标系，原点左下角)
      align        : str
      reason       : str     (状态原因，调试用)

    fail 触发条件（任一即 fail）：
      - 值为空
      - 字符数超过 fail_threshold（字段级 max_chars 或全局 fail_threshold）
      - 格子宽度或高度 <= 0（无效格子）
      - 字号从 size_max 缩到 size_min 后文字仍然溢出格子
    """
    # ── 1. 空值 → fail ──────────────────────────────────────────
    if value is None or str(value).strip() == "":
        return {"status": "fail", "reason": "no_value"}

    value = str(value).strip()

    # ── 2. 字符数阈值检查 ────────────────────────────────────────
    # 字段级 max_chars 优先；其次读全局 fail_threshold
    max_chars = int(field.get("max_chars") or 0)
    if max_chars <= 0:
        max_chars = int(settings.get("fail_threshold", 200))
    if max_chars > 0 and len(value) > max_chars:
        return {
            "status": "fail",
            "reason": f"char_limit_exceeded ({len(value)} > {max_chars})",
        }

    # ── 3. 读取坐标（pdfplumber top-down 系）────────────────────
    x0     = float(field.get("cell_x0", 0.0))
    top    = float(field.get("cell_top", 0.0))
    x1     = float(field.get("cell_x1", 0.0))
    bottom = float(field.get("cell_bottom", 0.0))

    cell_width  = x1 - x0
    cell_height = bottom - top

    # 无效格子 → fail
    if cell_width <= 0 or cell_height <= 0:
        return {"status": "fail", "reason": "invalid_cell_size"}

    # ── 4. 字体参数（字段级覆盖 > settings 全局）───────────────
    font_name  = _ensure_font(
        field.get("font_name") or settings.get("default_font_name", DEFAULT_FONT)
    )
    size_max   = float(field.get("font_size_max") or settings.get("default_font_size_max", 11.0))
    size_min   = float(field.get("font_size_min") or settings.get("default_font_size_min", 6.0))
    size_step  = float(field.get("font_size_step") or settings.get("default_font_size_step", 0.5))

    # ── 5. 对齐方式 ──────────────────────────────────────────────
    # 字段级 text_align 或 align 均接受；回退到 settings 全局
    align = (
        field.get("text_align")
        or field.get("align")
        or settings.get("default_text_align", "left")
    )

    # ── 6. 左侧 padding（pt）────────────────────────────────────
    # 字段级 padding_left_px 若 > 0 则覆盖全局
    left_padding = float(field.get("padding_left_px") or 0)
    if left_padding <= 0:
        left_padding = float(settings.get("default_left_padding_px", 4.0))

    # ── 7. 字号自适应收缩循环 ────────────────────────────────────
    font_size = size_max
    chosen_size: Optional[float] = None

    while font_size >= size_min - 0.001:
        available = cell_width - left_padding - 2.0   # 2pt 右边安全边距
        if available <= 0:
            available = cell_width - 2.0
        w = stringWidth(value, font_name, font_size)
        if w <= available:
            chosen_size = font_size
            break
        font_size = round(font_size - size_step, 3)

    # 即使到了最小字号仍溢出 → fail（不写入任何残缺内容）
    if chosen_size is None:
        return {
            "status": "fail",
            "reason": f"overflow_at_min_size ({size_min}pt)",
        }

    # ── 8. 水平位置 ──────────────────────────────────────────────
    if align == "center":
        text_x = x0 + cell_width / 2.0
    elif align == "right":
        text_x = x1 - 2.0
    else:
        text_x = x0 + left_padding

    # ── 9. 垂直策略 ──────────────────────────────────────────────
    vertical_strategy = (
        field.get("padding_vertical_strategy")
        or settings.get("default_vertical_strategy", "center_baseline")
    )
    custom_offset = float(settings.get("default_custom_offset", 0.0))

    return {
        "status"           : "write",
        "font_name"        : font_name,
        "font_size"        : chosen_size,
        "text_x"           : text_x,
        "align"            : align,
        # 垂直信息（top-down，转换在 _draw_overlay 时进行）
        "cell_top"         : top,
        "cell_bottom"      : bottom,
        "cell_height"      : cell_height,
        "vertical_strategy": vertical_strategy,
        "custom_offset"    : custom_offset,
        "reason"           : "ok",
    }


def _baseline_y_rl(layout: dict, page_height: float) -> float:
    """
    将 pdfplumber top-down 坐标转换为 ReportLab bottom-up baseline。
    """
    cell_top    = layout["cell_top"]
    cell_bottom = layout["cell_bottom"]
    cell_height = layout["cell_height"]
    font_size   = layout["font_size"]
    strategy    = layout.get("vertical_strategy", "center_baseline")
    offset      = layout.get("custom_offset", 0.0)

    rl_bottom = page_height - cell_bottom  # 格子底部在 RL 坐标的 y
    rl_top    = page_height - cell_top     # 格子顶部在 RL 坐标的 y

    if strategy == "top":
        # 文字基线紧贴格子顶部内侧
        baseline = rl_top - font_size * 0.8
    elif strategy == "custom_offset":
        baseline = rl_bottom + (cell_height / 2) + offset
    else:
        # center_baseline（默认）：视觉上垂直居中
        # ReportLab baseline 在字符底部；视觉中心 ≈ baseline + 0.3*font_size
        baseline = rl_bottom + (cell_height - font_size) / 2.0

    return baseline


# ──────────────────────────────────────────────────────────────
#  fill_pdf — 主入口
# ──────────────────────────────────────────────────────────────

def fill_pdf(
    template_id: int,
    customer_data: dict,
    output_path: str,
    source_pdf_path: Optional[str] = None,
    job_id: Optional[int] = None,
) -> dict:
    """
    将客户数据填入 original.pdf，生成叠字后的 PDF。

    参数：
      template_id     — 模板 ID
      customer_data   — {standard_key: value}
      output_path     — 输出 PDF 路径
      source_pdf_path — 原件 PDF 路径（None 则从模板记录中读取）
      job_id          — fill_jobs 的 ID（可选，用于保存字段结果）

    返回：
      {
        "success"       : bool,
        "output_path"   : str,
        "write_count"   : int,    # 成功写入字段数
        "fail_count"    : int,    # 失败字段数
        "fail_fields"   : list[str],  # 失败字段标签列表
        "field_results" : list[dict], # 每个字段的详细结果（供 verifier 使用）
      }
    """
    from modules.template_store import (
        get_fields, get_template,
        get_settings, save_job_fields,
    )

    # ── 读取模板 ────────────────────────────────────────────────
    template = get_template(template_id)
    if not template:
        raise ValueError(f"模板 {template_id} 不存在")

    # ── 确定原件 PDF 路径 ────────────────────────────────────────
    from modules.template_store import resolve_original_pdf
    if source_pdf_path is None:
        source_pdf_path = resolve_original_pdf(template)
    if not source_pdf_path or not os.path.exists(source_pdf_path):
        raise FileNotFoundError(f"原件 PDF 不存在：{source_pdf_path}")

    # ── 读取全局 settings ────────────────────────────────────────
    settings = get_settings()

    # ── 读取字段列表 ─────────────────────────────────────────────
    fields = get_fields(template_id)
    if not fields:
        raise ValueError(f"模板 {template_id} 没有字段记录")

    # ── 打开原件 PDF ─────────────────────────────────────────────
    reader     = PdfReader(source_pdf_path)
    page_count = len(reader.pages)

    # ── 按页分组 ─────────────────────────────────────────────────
    pages_fields: dict[int, list[dict]] = {}
    for f in fields:
        pg = f.get("page_number", 1)
        pages_fields.setdefault(pg, []).append(f)

    # ── 逐页生成 overlay ─────────────────────────────────────────
    overlays: dict[int, io.BytesIO] = {}
    write_count  = 0
    fail_count   = 0
    fail_fields: list[str] = []
    field_results: list[dict] = []

    for page_idx in range(page_count):
        page_num  = page_idx + 1
        pdf_page  = reader.pages[page_idx]
        pg_width  = float(pdf_page.mediabox.width)
        pg_height = float(pdf_page.mediabox.height)

        page_fields = pages_fields.get(page_num, [])
        if not page_fields:
            continue

        overlay_buf = io.BytesIO()
        c = canvas.Canvas(overlay_buf, pagesize=(pg_width, pg_height))

        for field in page_fields:
            std_key = field.get("standard_key", "")
            if not std_key:
                # 无 standard_key → 直接 fail（无法知道填什么）
                fail_count += 1
                field_results.append({
                    "field_id"   : field["id"],
                    "value"      : "",
                    "fill_status": "fail",
                    "fill_reason": "no_standard_key",
                    "font_size"  : None,
                    "text_x"     : None,
                    "text_y"     : None,
                })
                continue

            value = _get_field_value(customer_data, std_key)

            # compute_layout — 只返回 write 或 fail
            layout = compute_layout(field, value or "", settings)

            fr: dict = {
                "field_id"   : field["id"],
                "value"      : value or "",
                "fill_status": layout["status"],
                "fill_reason": layout.get("reason", ""),
                "font_size"  : layout.get("font_size"),
                "text_x"     : layout.get("text_x"),
                "text_y"     : None,
            }

            if layout["status"] == "write":
                baseline = _baseline_y_rl(layout, pg_height)
                fr["text_y"] = baseline

                # 绘制文字到 overlay
                fn   = layout["font_name"]
                fs   = layout["font_size"]
                tx   = layout["text_x"]
                algn = layout["align"]

                c.setFillColorRGB(0.08, 0.08, 0.08)
                c.setFont(fn, fs)

                if algn == "center":
                    c.drawCentredString(tx, baseline, value)
                elif algn == "right":
                    c.drawRightString(tx, baseline, value)
                else:
                    c.drawString(tx, baseline, value)

                write_count += 1

            else:  # status == "fail"
                fail_count += 1
                label = field.get("raw_label") or std_key
                fail_fields.append(label)

            field_results.append(fr)

        c.save()
        overlay_buf.seek(0)
        overlays[page_num] = overlay_buf

    # ── 合并 overlay 到原件 PDF ──────────────────────────────────
    writer = PdfWriter()
    for page_idx in range(page_count):
        page_num      = page_idx + 1
        original_page = reader.pages[page_idx]

        if page_num in overlays:
            ov_reader = PdfReader(overlays[page_num])
            ov_page   = ov_reader.pages[0]
            original_page.merge_page(ov_page)

        writer.add_page(original_page)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f_out:
        writer.write(f_out)

    logger.info(
        f"[fill_pdf] template={template_id} write={write_count} "
        f"fail={fail_count} → {output_path}"
    )

    # ── 保存字段级结果（若有 job_id）────────────────────────────
    if job_id is not None:
        save_job_fields(job_id, field_results)

    return {
        "success"      : True,
        "output_path"  : output_path,
        "write_count"  : write_count,
        "fail_count"   : fail_count,
        "fail_fields"  : fail_fields,
        "field_results": field_results,
    }


# ──────────────────────────────────────────────────────────────
#  辅助
# ──────────────────────────────────────────────────────────────

def _get_field_value(customer_data: dict, standard_key: str) -> Optional[str]:
    if standard_key in customer_data:
        v = customer_data[standard_key]
        return str(v).strip() if v is not None else None
    bare = standard_key.replace("customer.", "")
    v = customer_data.get(bare)
    return str(v).strip() if v is not None else None
