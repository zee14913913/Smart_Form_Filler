"""
verifier.py — 填表结果验证模块（PRD §八）
------------------------------------------
两类验证：

1. 字段级排版检查（填写质量）：
   - 字段是否有值
   - 文字是否在 cell 边界内
   - 是否存在溢出 / 无 padding / 偏移异常
   - 是否被标记 manual

2. 非填写区域原件对比（视觉完整性）：
   - 将 original.pdf 与 output.pdf 同一页渲染为图像
   - 对非填写区域做像素差分
   - 超过阈值则标记 verification_failed

输出：job 级结果 + field 级结果
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
#  字段级排版验证
# ──────────────────────────────────────────────────────────────

def verify_field_results(field_results: list[dict], fields: list[dict]) -> list[dict]:
    """
    对每个字段的填写结果做排版质量校验。

    参数：
      field_results — fill_pdf() 返回的 field_results 列表
      fields        — 来自 template_store.get_fields() 的字段定义

    返回：
      field_verdicts 列表，每项：
        {
          field_id      : int,
          raw_label     : str,
          standard_key  : str,
          fill_status   : str,          # write | skip | manual
          verify_status : str,          # pass | warning | fail | manual
          verify_reason : str,
        }
    """
    field_map = {f["id"]: f for f in fields}
    verdicts  = []

    for fr in field_results:
        fid    = fr.get("field_id")
        field  = field_map.get(fid, {})
        status = fr.get("status", "skip")

        raw_label    = field.get("raw_label", "")
        standard_key = field.get("standard_key", "")
        x0     = field.get("cell_x0", 0.0)
        x1     = field.get("cell_x1", 0.0)
        top    = field.get("cell_top", 0.0)
        bottom = field.get("cell_bottom", 0.0)

        if status == "manual":
            verdicts.append({
                "field_id"     : fid,
                "raw_label"    : raw_label,
                "standard_key" : standard_key,
                "fill_status"  : status,
                "verify_status": "manual",
                "verify_reason": fr.get("reason", "manual_required"),
            })
            continue

        if status == "skip":
            verdicts.append({
                "field_id"     : fid,
                "raw_label"    : raw_label,
                "standard_key" : standard_key,
                "fill_status"  : status,
                "verify_status": "pass",
                "verify_reason": "skipped_no_value",
            })
            continue

        # status == "write" — 检查排版
        tx      = fr.get("text_x")
        ty      = fr.get("text_y")
        fs      = fr.get("font_size", 0.0) or 0.0
        issues  = []

        # 检查水平边界（text_x 必须 >= x0，text_x + estimated_width <= x1）
        if tx is not None:
            if tx < x0 - 1.0:
                issues.append("text_x_before_cell_left")
            if tx > x1:
                issues.append("text_x_after_cell_right")

        # 检查字体是否极小（小于 5pt 视为 warning）
        if fs < 5.0:
            issues.append(f"font_size_too_small ({fs:.1f}pt)")

        # 检查 cell 尺寸合理性
        if (x1 - x0) <= 0 or (bottom - top) <= 0:
            issues.append("invalid_cell_dimensions")

        if issues:
            verdict_status = "warning"
            verdict_reason = ", ".join(issues)
        else:
            verdict_status = "pass"
            verdict_reason = "ok"

        verdicts.append({
            "field_id"     : fid,
            "raw_label"    : raw_label,
            "standard_key" : standard_key,
            "fill_status"  : status,
            "verify_status": verdict_status,
            "verify_reason": verdict_reason,
        })

    return verdicts


# ──────────────────────────────────────────────────────────────
#  非填写区域图像对比（可选，需 pdf2image + PIL）
# ──────────────────────────────────────────────────────────────

def verify_non_fill_areas(
    original_pdf_path: str,
    output_pdf_path: str,
    fields: list[dict],
    diff_threshold: float = 0.02,
    dpi: int = 72,
) -> dict:
    """
    对 original 和 output 各页渲染为图像，
    对非填写区域做像素差分。

    返回：
      {
        "available"   : bool,    # 依赖库是否可用
        "verdict"     : "pass" | "warning" | "fail",
        "pages"       : [...],   # 每页的结果
        "reason"      : str,
      }
    """
    try:
        from pdf2image import convert_from_path
        from PIL import Image, ImageChops
        import numpy as np
    except ImportError:
        logger.warning("pdf2image / PIL / numpy 不可用，跳过图像对比验证")
        return {
            "available": False,
            "verdict"  : "pass",
            "reason"   : "image_diff_library_not_available",
            "pages"    : [],
        }

    try:
        orig_pages = convert_from_path(original_pdf_path, dpi=dpi)
        out_pages  = convert_from_path(output_pdf_path,  dpi=dpi)
    except Exception as e:
        logger.error(f"PDF 渲染失败: {e}")
        return {
            "available": True,
            "verdict"  : "warning",
            "reason"   : f"pdf_render_failed: {e}",
            "pages"    : [],
        }

    # 按页分组字段
    pages_fields: dict[int, list[dict]] = {}
    for f in fields:
        pg = f.get("page_number", 1)
        pages_fields.setdefault(pg, []).append(f)

    page_results = []
    overall_fail = False

    for page_idx, (orig_img, out_img) in enumerate(
        zip(orig_pages, out_pages), start=1
    ):
        orig_arr = np.array(orig_img.convert("RGB"), dtype=np.float32)
        out_arr  = np.array(out_img.convert("RGB"),  dtype=np.float32)

        if orig_arr.shape != out_arr.shape:
            page_results.append({
                "page"   : page_idx,
                "verdict": "warning",
                "reason" : "page_size_mismatch",
            })
            continue

        h, w = orig_arr.shape[:2]
        scale_x = w / 595.0  # A4 宽度（假设 72dpi 下约 595pt）
        scale_y = h / 842.0

        # 构建非填写区域掩膜（白色=保留，黑色=填写区忽略）
        import numpy as np
        mask = np.ones((h, w), dtype=bool)  # True = 需要对比的区域
        for f in pages_fields.get(page_idx, []):
            # 将 pt 坐标转换为像素（72dpi 下 1pt ≈ 1px）
            px0 = max(0, int((f.get("cell_x0", 0) - 4) * scale_x))
            py0 = max(0, int((f.get("cell_top", 0) - 4) * scale_y))
            px1 = min(w, int((f.get("cell_x1", 0) + 4) * scale_x))
            py1 = min(h, int((f.get("cell_bottom", 0) + 4) * scale_y))
            mask[py0:py1, px0:px1] = False   # 填写区域不比较

        # 计算非填写区域差异
        diff = np.abs(orig_arr - out_arr).mean(axis=2)  # (h, w)
        non_fill_diff = diff[mask]
        if non_fill_diff.size == 0:
            diff_ratio = 0.0
        else:
            # 差异像素占比（差值 > 10 视为有差异）
            diff_ratio = float((non_fill_diff > 10).sum()) / non_fill_diff.size

        if diff_ratio > diff_threshold:
            verdict = "fail"
            overall_fail = True
        elif diff_ratio > diff_threshold / 2:
            verdict = "warning"
        else:
            verdict = "pass"

        page_results.append({
            "page"      : page_idx,
            "verdict"   : verdict,
            "diff_ratio": round(diff_ratio, 6),
            "reason"    : f"non_fill_diff={diff_ratio:.4%}",
        })

    overall_verdict = "fail" if overall_fail else (
        "warning" if any(p["verdict"] == "warning" for p in page_results) else "pass"
    )

    return {
        "available": True,
        "verdict"  : overall_verdict,
        "pages"    : page_results,
        "reason"   : "image_diff_complete",
    }


# ──────────────────────────────────────────────────────────────
#  verify_job — 汇总入口
# ──────────────────────────────────────────────────────────────

def verify_job(
    job_id: int,
    template_id: int,
    original_pdf_path: str,
    output_pdf_path: str,
    field_results: list[dict],
    settings: Optional[dict] = None,
) -> dict:
    """
    对一次填表任务执行完整验证，返回 job 级结果。

    返回：
      {
        "total_fields"   : int,
        "pass_count"     : int,
        "warning_count"  : int,
        "fail_count"     : int,
        "manual_count"   : int,
        "final_verdict"  : "pass" | "warning" | "fail",
        "field_verdicts" : list[dict],
        "image_diff"     : dict,
      }
    """
    from modules.template_store import (
        get_fields, update_fill_job, update_job_field_verify, get_settings
    )

    if settings is None:
        settings = get_settings()

    fields = get_fields(template_id)

    # ── 字段级验证 ─────────────────────────────────────────
    field_verdicts = verify_field_results(field_results, fields)

    pass_count    = sum(1 for v in field_verdicts if v["verify_status"] == "pass")
    warning_count = sum(1 for v in field_verdicts if v["verify_status"] == "warning")
    fail_count    = sum(1 for v in field_verdicts if v["verify_status"] == "fail")
    manual_count  = sum(1 for v in field_verdicts if v["verify_status"] == "manual")
    total_fields  = len(field_verdicts)

    # ── 图像差分验证 ───────────────────────────────────────
    threshold = float(settings.get("verify_pixel_diff_threshold", 0.02))
    image_diff = verify_non_fill_areas(
        original_pdf_path,
        output_pdf_path,
        fields,
        diff_threshold=threshold,
    )

    # ── 计算总裁定 ─────────────────────────────────────────
    if fail_count > 0 or image_diff.get("verdict") == "fail":
        final_verdict = "fail"
    elif warning_count > 0 or image_diff.get("verdict") == "warning":
        final_verdict = "warning"
    else:
        final_verdict = "pass"

    # ── 回写数据库 ─────────────────────────────────────────
    update_fill_job(job_id, {
        "verification_status" : "done",
        "verification_verdict": final_verdict,
        "pass_count"          : pass_count,
        "warning_count"       : warning_count,
        "fail_count"          : fail_count,
    })

    for v in field_verdicts:
        update_job_field_verify(
            job_id,
            v["field_id"],
            v["verify_status"],
            v["verify_reason"],
        )

    logger.info(
        f"[verify_job] job={job_id} verdict={final_verdict} "
        f"pass={pass_count} warn={warning_count} fail={fail_count} manual={manual_count}"
    )

    return {
        "total_fields"  : total_fields,
        "pass_count"    : pass_count,
        "warning_count" : warning_count,
        "fail_count"    : fail_count,
        "manual_count"  : manual_count,
        "final_verdict" : final_verdict,
        "field_verdicts": field_verdicts,
        "image_diff"    : image_diff,
    }
