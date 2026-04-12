"""
main.py — FastAPI 入口 (v3 — PRD Master Prompt 严格版)
-------------------------------------------------------
API 列表：
  POST /upload-form                      上传 PDF，分析字段，创建模板
  GET  /templates                        列出所有模板
  GET  /templates/{id}                   模板详情（含字段）
  PUT  /templates/{id}/fields            批量更新字段映射
  GET  /customers                        客户列表
  GET  /customers/{id}                   单个客户完整数据
  POST /fill-form                        执行填表（含验证，写入 fill_jobs）
  GET  /download/{filename}              下载填好的 PDF
  GET  /jobs                             最近填表任务列表
  GET  /jobs/{job_id}                    任务详情（含字段级结果）
  GET  /settings                         读取全局配置
  POST /settings                         更新全局配置（只读字段被忽略）
  GET  /standard-keys                    所有标准字段键
  POST /synonyms                         添加同义词

PRD 严格约束：
  - fill-form 响应只有 pass / fail，无 warning / manual
  - 验证器异常 → 整体 fail（不 fallback 到 pass）
  - fill 失败 → 直接返回 fail（不继续验证）
"""

import os
import uuid
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

# ──────────────────────────────────────────────────────────────
#  路径常量
# ──────────────────────────────────────────────────────────────

BASE_DIR    = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────────────────────
#  Lifespan（替代已弃用的 @app.on_event）
# ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    from modules.template_store import init_database
    init_database()
    logger.info("数据库初始化完成")
    yield

# ──────────────────────────────────────────────────────────────
#  App
# ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Smart Form Filler API",
    description=(
        "智能表格自动填写系统后端 API\n\n"
        "核心约束：输出 PDF 必须以原件为底板，在原件上叠字。\n"
        "render_base = original_pdf（固定，不可修改）。\n"
        "结果只允许 PASS / FAIL，无任何灰色状态。"
    ),
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
#  Pydantic 模型
# ──────────────────────────────────────────────────────────────

class FieldUpdate(BaseModel):
    id: int
    standard_key: Optional[str] = None
    text_align: Optional[str] = None
    align: Optional[str] = None           # 兼容旧前端
    font_size_max: Optional[float] = None
    font_size_min: Optional[float] = None
    font_size_step: Optional[float] = None
    is_confirmed: Optional[int] = None
    raw_label: Optional[str] = None
    field_type: Optional[str] = None
    max_chars: Optional[int] = None
    multiline: Optional[int] = None

class FieldsUpdateRequest(BaseModel):
    fields: list[FieldUpdate]

class FillFormRequest(BaseModel):
    template_id: int
    customer_id: str

class SynonymRequest(BaseModel):
    standard_key: str
    synonym: str

class SettingsUpdateRequest(BaseModel):
    # 字体
    default_font_name: Optional[str] = None
    default_font_size_max: Optional[float] = None
    default_font_size_min: Optional[float] = None
    default_font_size_step: Optional[float] = None
    # Padding
    default_left_padding_px: Optional[float] = None
    default_vertical_strategy: Optional[str] = None
    default_custom_offset: Optional[float] = None
    # 对齐
    default_text_align: Optional[str] = None
    # 失败阈值（PRD v3：替代 overflow_policy + manual_threshold）
    fail_threshold: Optional[int] = None
    # 验证阈值
    verify_pixel_diff_threshold: Optional[float] = None

# ──────────────────────────────────────────────────────────────
#  Health
# ──────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "status" : "ok",
        "message": "Smart Form Filler API v3 — render_base=original_pdf — PASS/FAIL only",
    }

# ──────────────────────────────────────────────────────────────
#  上传表格
# ──────────────────────────────────────────────────────────────

@app.post("/upload-form", tags=["Templates"])
async def upload_form(
    file: UploadFile = File(...),
    template_name: str = Form(""),
    institution: str = Form(""),
):
    """
    上传 PDF，分析字段，创建模板。
    原件 PDF 同时保存到 uploads/ 和 data/forms/{id}/original.pdf。
    """
    suffix        = Path(file.filename).suffix.lower()
    safe_filename = f"{uuid.uuid4().hex}{suffix}"
    upload_path   = UPLOADS_DIR / safe_filename

    try:
        content = await file.read()
        with open(upload_path, "wb") as f:
            f.write(content)
        logger.info(f"文件已保存：{upload_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败：{e}")

    # 分析字段
    try:
        from modules.analyzer import analyze_pdf
        fields = analyze_pdf(str(upload_path))
        logger.info(f"字段分析完成：{len(fields)} 个")
    except Exception as e:
        logger.error(f"字段分析失败：{e}")
        fields = []

    # 标准化
    try:
        from modules.field_normalizer import normalize_fields
        fields = normalize_fields(fields)
    except Exception as e:
        logger.warning(f"字段标准化失败：{e}")

    # 创建模板
    from modules.template_store import create_template, save_fields, copy_to_forms_dir
    name       = template_name or Path(file.filename).stem
    page_count = max((f.get("page_number", 1) for f in fields), default=1)
    template_id = create_template(
        name=name,
        institution=institution,
        source_filename=safe_filename,
        page_count=page_count,
    )

    # 将原件复制到规范路径 data/forms/{id}/original.pdf
    try:
        original_path = copy_to_forms_dir(template_id, str(upload_path))
        logger.info(f"原件已存档：{original_path}")
    except Exception as e:
        logger.warning(f"原件存档失败（不影响功能）：{e}")

    if fields:
        save_fields(template_id, fields)

    return {
        "template_id"  : template_id,
        "template_name": name,
        "institution"  : institution,
        "page_count"   : page_count,
        "field_count"  : len(fields),
        "fields"       : fields,
    }

# ──────────────────────────────────────────────────────────────
#  模板 CRUD
# ──────────────────────────────────────────────────────────────

@app.get("/templates", tags=["Templates"])
async def get_templates():
    from modules.template_store import list_templates
    return list_templates()


@app.get("/templates/{template_id}", tags=["Templates"])
async def get_template(template_id: int):
    from modules.template_store import get_template as _get, get_fields
    template = _get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    fields = get_fields(template_id)
    return {**template, "fields": fields}


@app.put("/templates/{template_id}/fields", tags=["Templates"])
async def update_template_fields(template_id: int, req: FieldsUpdateRequest):
    from modules.template_store import update_field, update_template_status, get_template
    for upd in req.fields:
        data = (
            upd.model_dump(exclude_none=True)
            if hasattr(upd, "model_dump")
            else upd.dict(exclude_none=True)
        )
        fid = data.pop("id")
        if data:
            update_field(fid, data)
    # 若模板仍是 draft，更新为 confirmed
    template = get_template(template_id)
    if template and template.get("status") == "draft":
        update_template_status(template_id, "confirmed")
    return {"success": True, "updated_count": len(req.fields)}

# ──────────────────────────────────────────────────────────────
#  客户数据
# ──────────────────────────────────────────────────────────────

@app.get("/customers", tags=["Customers"])
async def get_customers():
    from modules.excel_reader import list_customers
    return list_customers()


@app.get("/customers/{customer_id}", tags=["Customers"])
async def get_customer(customer_id: str):
    from modules.excel_reader import get_customer as _get
    data = _get(customer_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"客户 {customer_id} 不存在")
    return data

# ──────────────────────────────────────────────────────────────
#  填表执行（PRD v3 严格版）
# ──────────────────────────────────────────────────────────────

@app.post("/fill-form", tags=["Fill"])
async def fill_form(req: FillFormRequest):
    """
    执行填表：
      1. 读取模板 original_pdf_path（在原件上叠字）
      2. 写入 fill_jobs 记录
      3. 调用 filler.fill_pdf()
      4. 调用 verifier.verify_job()
      5. 返回包含验证摘要的完整结果

    PRD 严格约束：
      - fill 失败 → 直接返回 HTTP 500 + fail（不继续验证）
      - verifier 异常 → 整体 fail（不 fallback 到 pass）
      - 响应字段只有 pass/fail 计数，无 warning/manual
    """
    from modules.excel_reader import get_customer as _get_customer
    from modules.template_store import (
        get_template as _get_template, resolve_original_pdf,
        create_fill_job, update_fill_job,
    )
    from modules.verifier import verify_job

    # 验证客户
    customer_data = _get_customer(req.customer_id)
    if customer_data is None:
        raise HTTPException(status_code=404, detail=f"客户 {req.customer_id} 不存在")

    # 验证模板
    template = _get_template(req.template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"模板 {req.template_id} 不存在")

    # 确定原件路径
    original_pdf = resolve_original_pdf(template)
    if not original_pdf:
        raise HTTPException(
            status_code=404,
            detail=f"原件 PDF 不存在（template_id={req.template_id}）。请重新上传模板。"
        )

    # 构建输出路径
    output_filename = f"filled_{req.template_id}_{req.customer_id}_{uuid.uuid4().hex[:8]}.pdf"
    output_path     = str(OUTPUTS_DIR / output_filename)

    # 创建 fill_job 记录
    from modules.template_store import get_fields
    fields  = get_fields(req.template_id)
    job_id  = create_fill_job(
        template_id       = req.template_id,
        customer_ref      = req.customer_id,
        customer_name     = customer_data.get("full_name", ""),
        total_fields      = len(fields),
        original_pdf_path = original_pdf,
    )

    # ── 执行填表 ─────────────────────────────────────────────────
    # PRD：fill 失败 → 直接 fail，不继续
    try:
        from modules.filler import fill_pdf
        fill_result = fill_pdf(
            template_id     = req.template_id,
            customer_data   = customer_data,
            output_path     = output_path,
            source_pdf_path = original_pdf,
            job_id          = job_id,
        )
    except Exception as e:
        update_fill_job(job_id, {"status": "failed", "final_verdict": "fail"})
        logger.error(f"填表失败：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"填表失败：{e}")

    # 更新 job 基本结果（PRD v3 列名：total_pass/total_fail）
    write_count = fill_result["write_count"]
    fail_count  = fill_result["fail_count"]
    update_fill_job(job_id, {
        "output_path"    : output_path,
        "output_filename": output_filename,
        "status"         : "done",
        "total_fields"   : len(fields),
        "total_pass"     : write_count,   # 初步 pass = 写入数；verifier 可能降级
        "total_fail"     : fail_count,
    })

    # ── 执行验证 ─────────────────────────────────────────────────
    # PRD：verifier 异常 → fail（不 fallback 到 pass）
    try:
        from modules.template_store import get_settings
        settings     = get_settings()
        verification = verify_job(
            job_id            = job_id,
            template_id       = req.template_id,
            original_pdf_path = original_pdf,
            output_pdf_path   = output_path,
            field_results     = fill_result["field_results"],
            settings          = settings,
        )
    except Exception as e:
        logger.error(f"验证失败（视为 fail）：{e}", exc_info=True)
        # 验证异常 → 整体 fail
        verification = {
            "total_fields"  : len(fields),
            "total_pass"    : 0,
            "total_fail"    : len(fields),
            "final_verdict" : "fail",
            "field_verdicts": [],
            "image_diff"    : {"available": False, "verdict": "fail", "pages": []},
        }
        update_fill_job(job_id, {
            "verification_status": "error",
            "final_verdict"      : "fail",
            "total_fail"         : len(fields),
        })

    # 用验证结果更新最终计数
    update_fill_job(job_id, {
        "total_pass"         : verification["total_pass"],
        "total_fail"         : verification["total_fail"],
        "verification_status": "done",
        "final_verdict"      : verification["final_verdict"],
    })

    # ── 构造响应（PRD v3：无任何灰色字段）───────────────────────
    return {
        # 填表基本结果
        "job_id"         : job_id,
        "download_url"   : f"/download/{output_filename}",
        "output_filename": output_filename,
        "write_count"    : write_count,
        "fail_count"     : fail_count,
        "fail_fields"    : fill_result["fail_fields"],
        # 验证摘要（严格 pass/fail）
        "verification": {
            "total_fields"       : verification["total_fields"],
            "total_pass"         : verification["total_pass"],
            "total_fail"         : verification["total_fail"],
            "final_verdict"      : verification["final_verdict"],
            "image_diff_available": verification["image_diff"].get("available", False),
            "image_diff_verdict"  : verification["image_diff"].get("verdict", "fail"),
        },
        "field_verdicts": verification.get("field_verdicts", []),
    }


@app.get("/download/{filename}", tags=["Fill"])
async def download_file(filename: str):
    file_path = OUTPUTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
    )

# ──────────────────────────────────────────────────────────────
#  Fill Jobs（Phase 4 v3）
# ──────────────────────────────────────────────────────────────

@app.get("/jobs", tags=["Jobs"])
async def list_jobs(limit: int = 20):
    """返回最近 fill_jobs 列表，供 Dashboard 展示。"""
    from modules.template_store import list_fill_jobs
    return list_fill_jobs(limit=limit)


@app.get("/jobs/{job_id}", tags=["Jobs"])
async def get_job(job_id: int):
    """返回单个任务详情（含字段级验证结果）。"""
    from modules.template_store import get_fill_job, get_job_fields
    job = get_fill_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    job_fields = get_job_fields(job_id)
    return {**job, "field_results": job_fields}

# ──────────────────────────────────────────────────────────────
#  Settings（PRD v3）
# ──────────────────────────────────────────────────────────────

@app.get("/settings", tags=["Settings"])
async def get_settings():
    """返回全局配置（含固定只读字段）。"""
    from modules.template_store import get_settings as _get
    return _get()


@app.post("/settings", tags=["Settings"])
async def update_settings(req: SettingsUpdateRequest):
    """
    更新可变配置项。
    render_base / allow_custom_drawn_templates / allow_modify_original_content
    这三个字段为固定值，即使传入也会被忽略。
    overflow_policy / manual_threshold 已废除，传入会被忽略。
    """
    from modules.template_store import update_settings as _update
    data = (
        req.model_dump(exclude_none=True)
        if hasattr(req, "model_dump")
        else req.dict(exclude_none=True)
    )
    updated = _update(data)
    return updated

# ──────────────────────────────────────────────────────────────
#  辅助接口
# ──────────────────────────────────────────────────────────────

@app.get("/standard-keys", tags=["Meta"])
async def get_standard_keys():
    from modules.field_normalizer import get_all_standard_keys
    return {"keys": get_all_standard_keys()}


@app.post("/synonyms", tags=["Meta"])
async def add_synonym(req: SynonymRequest):
    from modules.template_store import add_synonym as _add
    from modules.field_normalizer import invalidate_cache
    _add(req.standard_key, req.synonym, source="user")
    invalidate_cache()
    return {"success": True}

# ──────────────────────────────────────────────────────────────
#  直接运行（开发用）
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
