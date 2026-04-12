"""
template_store.py
-----------------
负责 SQLite 模板库的所有 CRUD 操作：
  - 初始化数据库（建表）
  - 保存/读取 form_templates
  - 保存/读取/更新 form_fields
  - 读取 field_synonyms（供 field_normalizer 使用）
"""

import sqlite3
import os
from typing import Optional

# 数据库文件路径（相对于 backend/ 目录）
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "templates.db")
INIT_SQL = os.path.join(os.path.dirname(__file__), "..", "database", "init_db.sql")


def get_connection() -> sqlite3.Connection:
    """获取 SQLite 连接，并开启外键支持"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # 让查询结果可通过列名访问
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database():
    """
    首次启动时初始化数据库：执行 init_db.sql 创建表和种子数据。
    若表已存在则跳过（SQL 中有 IF NOT EXISTS）。
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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

def create_template(name: str, institution: str, source_filename: str, page_count: int = 1) -> int:
    """
    插入一条新模板记录，返回新记录的 id。
    """
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO form_templates (name, institution, source_filename, page_count, status)
            VALUES (?, ?, ?, ?, 'draft')
            """,
            (name, institution, source_filename, page_count),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_templates() -> list[dict]:
    """返回所有模板的列表（不含字段详情）"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM form_templates ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_template(template_id: int) -> Optional[dict]:
    """返回单个模板的基本信息（不含字段）"""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM form_templates WHERE id = ?", (template_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_template_status(template_id: int, status: str):
    """更新模板状态：draft | confirmed | active"""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE form_templates SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, template_id),
        )
        conn.commit()
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────
#  form_fields CRUD
# ──────────────────────────────────────────────────────────────

def save_fields(template_id: int, fields: list[dict]):
    """
    批量插入字段记录（分析阶段产生的字段列表）。
    每个 dict 应包含 analyzer.py 输出的字段结构键。
    """
    conn = get_connection()
    try:
        for f in fields:
            conn.execute(
                """
                INSERT INTO form_fields (
                    template_id, page_number, raw_label, standard_key,
                    cell_x0, cell_top, cell_x1, cell_bottom,
                    font_size_max, font_size_min, font_size_step,
                    align, is_confirmed
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    template_id,
                    f.get("page_number", 1),
                    f.get("raw_label", ""),
                    f.get("standard_key", ""),
                    f.get("cell_x0", 0.0),
                    f.get("cell_top", 0.0),
                    f.get("cell_x1", 0.0),
                    f.get("cell_bottom", 0.0),
                    f.get("font_size_max", 10.0),
                    f.get("font_size_min", 6.0),
                    f.get("font_size_step", 0.5),
                    f.get("align", "left"),
                    0,  # 初始未确认
                ),
            )
        conn.commit()
    finally:
        conn.close()


def get_fields(template_id: int) -> list[dict]:
    """获取某模板的所有字段列表"""
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
    """
    更新单个字段的任意列（例如 standard_key、align、font_size_max 等）。
    updates 是一个 {column: value} 字典。
    """
    if not updates:
        return
    allowed_cols = {
        "standard_key", "raw_label", "cell_x0", "cell_top", "cell_x1", "cell_bottom",
        "font_size_max", "font_size_min", "font_size_step", "align",
        "padding_left", "padding_vertical", "is_confirmed", "needs_manual",
    }
    safe = {k: v for k, v in updates.items() if k in allowed_cols}
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


def update_fields_bulk(template_id: int, field_updates: list[dict]):
    """
    批量更新字段（前端模板确认页面提交时调用）。
    每个 dict 必须包含 id 字段及需要更新的其他键。
    """
    for upd in field_updates:
        fid = upd.pop("id", None)
        if fid:
            update_field(fid, upd)


def mark_field_confirmed(field_id: int):
    """标记字段映射已经由用户确认"""
    update_field(field_id, {"is_confirmed": 1})


# ──────────────────────────────────────────────────────────────
#  field_synonyms
# ──────────────────────────────────────────────────────────────

def get_all_synonyms() -> dict[str, list[str]]:
    """
    返回 {standard_key: [synonym, ...]} 字典，
    供 field_normalizer 构建匹配器。
    """
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
    """用户手动添加同义词"""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO field_synonyms (standard_key, synonym, source) VALUES (?,?,?)",
            (standard_key, synonym, source),
        )
        conn.commit()
    finally:
        conn.close()
