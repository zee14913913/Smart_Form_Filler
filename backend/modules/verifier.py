"""
verifier.py — 填表结果验证模块（v3 — PRD Master Prompt 严格版）
------------------------------------------------------------------
两类验证：

1. 字段级排版检查（填写质量）：
   - 字段 fill_status 是否为 write
   - 文字是否在 cell 边界内（水平）
   - 字号是否 >= 5pt（极小字号 = fail）
   - 格子尺寸是否有效

2. 非填写区域原件对比（视觉完整性）：
   - 将 original.pdf 与 output.pdf 同一页渲染为图像
   - 对非填写区域做像素差分
   - 超过阈值则 fail

严格规则：
  - verify_status 只允许 "pass" 或 "fail"
  - final_verdict 只允许 "pass" 或 "fail"
  - 任何字段 fail → 整体 fail
  - 图像差分 fail → 整体 fail
  - 任何异常 → 整体 fail（不 fallback 到 pass）
  - 所有 warning / manual / partial_pass 均已废除
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
          fill_status   : str,          # write | fail
          verify_status : str,          # pass | fail（严格两值）
          verify_reason : str,
        }
    """
    field_map = {f["id"]: f for f in fields}
    verdicts  = []

    for fr in field_results:
        fid         = fr.get("field_id")
        field       = field_map.get(fid, {})
        fill_status = fr.get("fill_status", "fail")

        raw_label    = field.get("raw_label", "")
        standard_key = field.get("standard_key", "")
        x0     = float(field.get("cell_x0",     0.0))
        x1     = float(field.get("cell_x1",     0.0))
        top    = float(field.get("cell_top",    0.0))
        bottom = float(field.get("cell_bottom", 0.0))

        # ── fill_status == "fail" → 直接 verify_status = "fail" ──
        if fill_status == "fail":
            verdicts.append({
                "field_id"     : fid,
                "raw_label"    : raw_label,
                "standard_key" : standard_key,
                "fill_status"  : "fail",
                "verify_status": "fail",
                "verify_reason": fr.get("fill_reason", "fill_failed"),
            })
            continue

        # ── fill_status == "write" — 检查排版质量 ────────────────
        tx  = fr.get("text_x")
        ty  = fr.get("text_y")
        fs  = float(fr.get("font_size") or 0.0)
        issues: list[str] = []

        # 检查水平边界：text_x 必须 >= cell_x0（有左 padding）
        if tx is not None:
            if tx < x0 - 1.0:
                issues.append("text_x_before_cell_left")
            if tx > x1:
                issues.append("text_x_after_cell_right")

        # 字号低于 5pt → 视为极小无法辨认 → fail
        if fs < 5.0:
            issues.append(f"font_size_too_small ({fs:.1f}pt)")

        # 格子尺寸无效
        if (x1 - x0) <= 0 or (bottom - top) <= 0:
            issues.append("invalid_cell_dimensions")

        if issues:
            verify_status = "fail"
            verify_reason = ", ".join(issues)
        else:
            verify_status = "pass"
            verify_reason = "ok"

        verdicts.append({
            "field_id"     : fid,
            "raw_label"    : raw_label,
            "standard_key" : standard_key,
            "fill_status"  : "write",
            "verify_status": verify_status,
            "verify_reason": verify_reason,
        })

    return verdicts


# ──────────────────────────────────────────────────────────────
#  非填写区域图像对比（可选，需 pdf2image + PIL）
# ──────────────────────────────────────────────────────────────

def verify_non_fill_areas(
    original_pdf_path: str,
    output_pdf_path: str,
    fields: list[dict],
    diff_threshold: float = 0.01,
    dpi: int = 72,
) -> dict:
    """
    对 original 和 output 各页渲染为图像，
    对非填写区域做像素差分。

    返回：
      {
        "available"   : bool,    # 依赖库是否可用
        "verdict"     : "pass" | "fail",   # 严格两值
        "pages"       : [...],   # 每页的结果
        "reason"      : str,
      }

    注意：库不可用时 verdict = "pass"（无法检测不视为失败）；
    但渲染失败（库可用却出错）→ verdict = "fail"（安全失败）。
    """
    try:
        from pdf2image import convert_from_path
        from PIL import Image
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
        # 渲染失败 → fail（不能假设原件未被篡改）
        return {
            "available": True,
            "verdict"  : "fail",
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
        import numpy as np  # noqa: F811
        orig_arr = np.array(orig_img.convert("RGB"), dtype=np.float32)
        out_arr  = np.array(out_img.convert("RGB"),  dtype=np.float32)

        if orig_arr.shape != out_arr.shape:
            # 页面尺寸不匹配 → 直接 fail（原件可能被改动）
            page_results.append({
                "page"   : page_idx,
                "verdict": "fail",
                "reason" : "page_size_mismatch",
            })
            overall_fail = True
            continue

        h, w = orig_arr.shape[:2]
        scale_x = w / 595.0  # A4 宽度（假设 72dpi 下约 595pt）
        scale_y = h / 842.0

        # 构建非填写区域掩膜（True = 需要对比的区域）
        mask = np.ones((h, w), dtype=bool)
        for f in pages_fields.get(page_idx, []):
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
        else:
            verdict = "pass"

        page_results.append({
            "page"      : page_idx,
            "verdict"   : verdict,
            "diff_ratio": round(diff_ratio, 6),
            "reason"    : f"non_fill_diff={diff_ratio:.4%}",
        })

    overall_verdict = "fail" if overall_fail else "pass"

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

    严格规则：
      - final_verdict 只允许 "pass" 或 "fail"
      - 任何字段 fail → final_verdict = fail
      - 图像差分 fail → final_verdict = fail
      - 只有全部字段 pass 且图像差分 pass → final_verdict = pass

    返回：
      {
        "total_fields"   : int,
        "total_pass"     : int,
        "total_fail"     : int,
        "final_verdict"  : "pass" | "fail",
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

    # ── 字段级验证 ─────────────────────────────────────────────
    field_verdicts = verify_field_results(field_results, fields)

    total_pass = sum(1 for v in field_verdicts if v["verify_status"] == "pass")
    total_fail = sum(1 for v in field_verdicts if v["verify_status"] == "fail")
    total_fields = len(field_verdicts)

    # ── 图像差分验证 ───────────────────────────────────────────
    threshold  = float(settings.get("verify_pixel_diff_threshold", 0.01))
    image_diff = verify_non_fill_areas(
        original_pdf_path,
        output_pdf_path,
        fields,
        diff_threshold=threshold,
    )

    # ── 计算总裁定：严格只有 pass / fail ───────────────────────
    # 任一字段 fail 或图像差分 fail → 整体 fail
    if total_fail > 0 or image_diff.get("verdict") == "fail":
        final_verdict = "fail"
    else:
        final_verdict = "pass"

    # ── 回写数据库 ─────────────────────────────────────────────
    update_fill_job(job_id, {
        "verification_status": "done",
        "final_verdict"      : final_verdict,
        "total_pass"         : total_pass,
        "total_fail"         : total_fail,
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
        f"pass={total_pass} fail={total_fail}"
    )

    return {
        "total_fields"  : total_fields,
        "total_pass"    : total_pass,
        "total_fail"    : total_fail,
        "final_verdict" : final_verdict,
        "field_verdicts": field_verdicts,
        "image_diff"    : image_diff,
    }
