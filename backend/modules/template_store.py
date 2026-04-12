"""
template_store.py
-----------------
负责 SQLite 模板库的所有 CRUD 操作：
  - 初始化数据库（建表）
  - form_templates CRUD（含 original_pdf_path）
  - form_fields CRUD（含 field_type / max_chars / multiline）
  - field_synonyms CRUD
  - system_settings 读写（fail_threshold，无 overflow_policy/manual_threshold）
  - fill_jobs / fill_job_fields 读写（total_pass/total_fail，无 warning/manual 计数）
"""

import sqlite3
import os
import shutil
from pathlib import Path
from typing import Optional

# 数据库文件路径
DB_PATH  = os.path.join(os.path.dirname(__file__), "..", "database", "templates.db")
INIT_SQL = os.path.join(os.path.dirname(__file__), "..", "database", "init_db.sql")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "forms")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """首次启动时初始化数据库，执行 init_db.sql。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(INIT_SQL, "r", encoding="utf-8") as f:
        sql_script = f.read()
    conn = get_connection()
    try:
        conn.executescript(sql_script)
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
#  form_templates CRUD
# ──────────────────────────────────────────────────────────────

def create_template(
    name: str,
    institution: str,
    source_filename: str,
    page_count: int = 1,
    original_pdf_path: Optional[str] = None,
) -> int:
    """
    插入新模板，返回 id。
    original_pdf_path 若传入则直接记录；
    若为 None，在创建后由调用方调用 set_original_pdf_path() 更新。
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO form_templates
                (name, institution, source_filename, page_count, status, original_pdf_path)
            VALUES (?, ?, ?, ?, 'draft', ?)
            """,
            (name, institution, source_filename, page_count, original_pdf_path),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def set_original_pdf_path(template_id: int, original_pdf_path: str):
    """更新模板的 original_pdf_path 字段。"""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE form_templates SET original_pdf_path = ?, updated_at = datetime('now') WHERE id = ?",
            (original_pdf_path, template_id),
        )
        conn.commit()
    finally:
        conn.close()


def copy_to_forms_dir(template_id: int, src_path: str) -> str:
    """
    将原件 PDF 复制到 data/forms/{template_id}/original.pdf，
    并更新数据库中的 original_pdf_path。
    返回目标路径（绝对路径）。
    """
    dest_dir = os.path.join(DATA_DIR, str(template_id))
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, "original.pdf")
    shutil.copy2(src_path, dest_path)
    set_original_pdf_path(template_id, dest_path)
    return dest_path


def list_templates() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM form_templates ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_template(template_id: int) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM form_templates WHERE id = ?", (template_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_template_status(template_id: int, status: str):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE form_templates SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, template_id),
        )
        conn.commit()
    finally:
        conn.close()


def resolve_original_pdf(template: dict) -> Optional[str]:
    """
    优先返回 original_pdf_path；
    若该字段为空则回退到 uploads/{source_filename}（兼容旧数据）。
    """
    op = template.get("original_pdf_path")
    if op and os.path.exists(op):
        return op
    # 旧路径兼容
    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    sf = template.get("source_filename", "")
    fallback = os.path.join(uploads_dir, sf)
    if sf and os.path.exists(fallback):
        return fallback
    return None


# ──────────────────────────────────────────────────────────────
#  form_fields CRUD
# ──────────────────────────────────────────────────────────────

def save_fields(template_id: int, fields: list[dict]):
    """
    批量保存字段到 form_fields 表。
    支持 PRD v3 新增列：field_type / max_chars / multiline。
    """
    conn = get_connection()
    try:
        for f in fields:
            conn.execute(
                """
                INSERT INTO form_fields (
                    template_id, page_number, raw_label, standard_key,
                    field_type, max_chars, multiline,
                    cell_x0, cell_top, cell_x1, cell_bottom,
                    font_size_max, font_size_min, font_size_step,
                    text_align, padding_left_px, padding_vertical_strategy,
                    is_confirmed
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    template_id,
                    f.get("page_number", 1),
                    f.get("raw_label", ""),
                    f.get("standard_key", ""),
                    f.get("field_type", "text"),
                    f.get("max_chars", 0),
                    f.get("multiline", 0),
                    f.get("cell_x0", 0.0),
                    f.get("cell_top", 0.0),
                    f.get("cell_x1", 0.0),
                    f.get("cell_bottom", 0.0),
                    f.get("font_size_max", 10.0),
                    f.get("font_size_min", 6.0),
                    f.get("font_size_step", 0.5),
                    f.get("text_align") or f.get("align", "left"),
                    f.get("padding_left_px", 0.0),
                    f.get("padding_vertical_strategy", ""),
                    0,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_fields(template_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM form_fields WHERE template_id = ? ORDER BY page_number, cell_top",
            (template_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_field(field_id: int, updates: dict):
    if not updates:
        return
    allowed_cols = {
        "standard_key", "raw_label", "field_type", "max_chars", "multiline",
        "cell_x0", "cell_top", "cell_x1", "cell_bottom",
        "font_size_max", "font_size_min", "font_size_step",
        "text_align", "padding_left_px", "padding_vertical_strategy",
        "is_confirmed",
        # 兼容旧调用（align → text_align 已统一，但保留 align 作为别名）
        "align",
    }
    safe = {k: v for k, v in updates.items() if k in allowed_cols}
    # 把旧字段名 align 映射到 text_align
    if "align" in safe and "text_align" not in safe:
        safe["text_align"] = safe.pop("align")
    elif "align" in safe:
        safe.pop("align")
    if not safe:
        return
    set_clause = ", ".join(f"{k} = ?" for k in safe)
    values = list(safe.values()) + [field_id]
    conn = get_connection()
    try:
        conn.execute(f"UPDATE form_fields SET {set_clause} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def mark_field_confirmed(field_id: int):
    update_field(field_id, {"is_confirmed": 1})


# ──────────────────────────────────────────────────────────────
#  field_synonyms
# ──────────────────────────────────────────────────────────────

def get_all_synonyms() -> dict[str, list[str]]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT standard_key, synonym FROM field_synonyms"
        ).fetchall()
        result: dict[str, list[str]] = {}
        for r in rows:
            result.setdefault(r["standard_key"], []).append(r["synonym"])
        return result
    finally:
        conn.close()


def add_synonym(standard_key: str, synonym: str, source: str = "user"):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO field_synonyms (standard_key, synonym, source) VALUES (?,?,?)",
            (standard_key, synonym, source),
        )
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
#  system_settings
# ──────────────────────────────────────────────────────────────

# PRD v3：移除 overflow_policy / manual_threshold；新增 fail_threshold
SETTINGS_MUTABLE_COLS = {
    "default_font_name",
    "default_font_size_max",
    "default_font_size_min",
    "default_font_size_step",
    "default_left_padding_px",
    "default_vertical_strategy",
    "default_custom_offset",
    "default_text_align",
    "fail_threshold",
    "verify_pixel_diff_threshold",
}

# 固定只读字段（不允许前端修改）
SETTINGS_READONLY = {
    "render_base"                : "original_pdf",
    "allow_custom_drawn_templates": 0,
    "allow_modify_original_content": 0,
}


def get_settings() -> dict:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM system_settings WHERE id = 1").fetchone()
        if row:
            d = dict(row)
            # 强制覆盖只读字段
            d.update(SETTINGS_READONLY)
            return d
        return {}
    finally:
        conn.close()


def update_settings(updates: dict) -> dict:
    """
    更新可变配置项，忽略只读字段和未知字段。
    返回更新后的完整配置。
    """
    safe = {k: v for k, v in updates.items() if k in SETTINGS_MUTABLE_COLS}
    if safe:
        set_clause = ", ".join(f"{k} = ?" for k in safe)
        set_clause += ", updated_at = datetime('now')"
        values = list(safe.values())
        conn = get_connection()
        try:
            conn.execute(
                f"UPDATE system_settings SET {set_clause} WHERE id = 1", values
            )
            conn.commit()
        finally:
            conn.close()
    return get_settings()


# ──────────────────────────────────────────────────────────────
#  fill_jobs
# ──────────────────────────────────────────────────────────────

def create_fill_job(
    template_id: int,
    customer_ref: str,
    customer_name: str = "",
    total_fields: int = 0,
    original_pdf_path: str = "",
) -> int:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO fill_jobs
                (template_id, customer_ref, customer_name, status,
                 total_fields, original_pdf_path)
            VALUES (?, ?, ?, 'running', ?, ?)
            """,
            (template_id, customer_ref, customer_name, total_fields, original_pdf_path),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_fill_job(job_id: int, updates: dict):
    """
    允许更新的列（PRD v3）：
      output_path, output_filename, status,
      total_fields, total_pass, total_fail,
      verification_status, final_verdict
    已移除：filled_count, skipped_count, manual_count,
            verification_verdict, pass_count, warning_count, fail_count
    """
    allowed = {
        "output_path", "output_filename", "status",
        "total_fields", "total_pass", "total_fail",
        "verification_status", "final_verdict",
        "original_pdf_path",
    }
    safe = {k: v for k, v in updates.items() if k in allowed}
    if not safe:
        return
    set_clause = ", ".join(f"{k} = ?" for k in safe)
    set_clause += ", updated_at = datetime('now')"
    values = list(safe.values()) + [job_id]
    conn = get_connection()
    try:
        conn.execute(f"UPDATE fill_jobs SET {set_clause} WHERE id = ?", values)
        conn.commit()
    finally:
        conn.close()


def get_fill_job(job_id: int) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM fill_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_fill_jobs(limit: int = 20) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT j.*, t.name AS template_name
            FROM fill_jobs j
            LEFT JOIN form_templates t ON t.id = j.template_id
            ORDER BY j.created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_job_fields(job_id: int, field_results: list[dict]):
    """
    批量保存 fill_job_fields（每个字段的填写结果）。
    列名对齐 PRD v3：fill_status / fill_reason（原 status/reason）。
    """
    conn = get_connection()
    try:
        for fr in field_results:
            conn.execute(
                """
                INSERT INTO fill_job_fields
                    (job_id, field_id, value, fill_status, fill_reason, font_size, text_x, text_y)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    fr.get("field_id"),
                    fr.get("value", ""),
                    fr.get("fill_status", "fail"),
                    fr.get("fill_reason", ""),
                    fr.get("font_size"),
                    fr.get("text_x"),
                    fr.get("text_y"),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_job_fields(job_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT jf.*, ff.raw_label, ff.standard_key,
                   ff.cell_x0, ff.cell_top, ff.cell_x1, ff.cell_bottom
            FROM fill_job_fields jf
            LEFT JOIN form_fields ff ON ff.id = jf.field_id
            WHERE jf.job_id = ?
            ORDER BY ff.page_number, ff.cell_top
            """,
            (job_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_job_field_verify(job_id: int, field_id: int, verify_status: str, verify_reason: str):
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE fill_job_fields
            SET verify_status = ?, verify_reason = ?
            WHERE job_id = ? AND field_id = ?
            """,
            (verify_status, verify_reason, job_id, field_id),
        )
        conn.commit()
    finally:
        conn.close()
