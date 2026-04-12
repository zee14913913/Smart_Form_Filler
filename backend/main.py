"""
main.py — FastAPI 入口
----------------------
启动方式：
  cd backend
  uvicorn main:app --reload --port 8000

API 列表：
  POST /upload-form                        上传 PDF，分析字段，创建模板
  GET  /templates                          列出所有模板
  GET  /templates/{template_id}            读取模板详情（含字段列表）
  PUT  /templates/{template_id}/fields     批量更新字段映射/排版参数
  GET  /customers                          从 Excel 读取客户列表
  GET  /customers/{customer_id}            读取单个客户完整数据
  POST /fill-form                          执行填表，返回下载链接
  GET  /download/{filename}               下载已生成的 PDF
  GET  /standard-keys                     返回所有标准字段键列表
  POST /synonyms                          添加自定义同义词
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ──────────────────────────────────────────────────────────────
#  日志
# ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

# ──────────────────────────────────────────────────────────────
#  路径常量
# ──────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
UPLOADS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────────────────────
#  App 初始化
# ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="Smart Form Filler API",
    description="智能表格自动填写系统后端 API",
    version="1.0.0",
)

# 允许前端 Next.js dev server 跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────
#  启动事件：初始化数据库
# ──────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化 SQLite 数据库"""
    from modules.template_store import init_database
    init_database()
    logger.info("数据库初始化完成")


# ──────────────────────────────────────────────────────────────
#  Pydantic 数据模型
# ──────────────────────────────────────────────────────────────

class FieldUpdate(BaseModel):
    id: int
    standard_key: Optional[str] = None
    align: Optional[str] = None
    font_size_max: Optional[float] = None
    font_size_min: Optional[float] = None
    font_size_step: Optional[float] = None
    is_confirmed: Optional[int] = None
    raw_label: Optional[str] = None


class FieldsUpdateRequest(BaseModel):
    fields: list[FieldUpdate]


class FillFormRequest(BaseModel):
    template_id: int
    customer_id: str


class SynonymRequest(BaseModel):
    standard_key: str
    synonym: str


# ──────────────────────────────────────────────────────────────
#  API 路由
# ──────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Smart Form Filler API is running"}


# ── 上传表格 ──────────────────────────────────────────────────

@app.post("/upload-form", tags=["Templates"])
async def upload_form(
    file: UploadFile = File(...),
    template_name: str = Form(""),
    institution: str = Form(""),
):
    """
    上传 PDF/图片表格文件，自动分析字段，创建模板记录。

    返回：
      template_id, template_name, fields（字段列表含坐标和初步映射）
    """
    # 1. 保存上传文件
    suffix = Path(file.filename).suffix.lower()
    safe_filename = f"{uuid.uuid4().hex}{suffix}"
    save_path = UPLOADS_DIR / safe_filename

    try:
        content = await file.read()
        with open(save_path, "wb") as f:
            f.write(content)
        logger.info(f"文件已保存：{save_path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败：{e}")

    # 2. 分析字段
    try:
        from modules.analyzer import analyze_pdf
        fields = analyze_pdf(str(save_path))
        logger.info(f"字段分析完成，共 {len(fields)} 个字段")
    except Exception as e:
        logger.error(f"字段分析失败：{e}")
        # 分析失败时仍创建模板，但字段列表为空（用户可手动配置）
        fields = []

    # 3. 字段标准化
    try:
        from modules.field_normalizer import normalize_fields
        fields = normalize_fields(fields)
    except Exception as e:
        logger.warning(f"字段标准化失败：{e}")

    # 4. 创建模板记录
    from modules.template_store import create_template, save_fields
    name = template_name or Path(file.filename).stem
    page_count = max((f.get("page_number", 1) for f in fields), default=1)
    template_id = create_template(
        name=name,
        institution=institution,
        source_filename=safe_filename,
        page_count=page_count,
    )

    # 5. 保存字段
    if fields:
        save_fields(template_id, fields)

    return {
        "template_id": template_id,
        "template_name": name,
        "institution": institution,
        "page_count": page_count,
        "field_count": len(fields),
        "fields": fields,
    }


# ── 模板列表 ──────────────────────────────────────────────────

@app.get("/templates", tags=["Templates"])
async def get_templates():
    """返回所有模板列表"""
    from modules.template_store import list_templates
    return list_templates()


@app.get("/templates/{template_id}", tags=["Templates"])
async def get_template(template_id: int):
    """返回单个模板及其所有字段"""
    from modules.template_store import get_template as _get_template, get_fields
    template = _get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    fields = get_fields(template_id)
    return {**template, "fields": fields}


@app.put("/templates/{template_id}/fields", tags=["Templates"])
async def update_template_fields(template_id: int, req: FieldsUpdateRequest):
    """批量更新字段映射与排版参数"""
    from modules.template_store import update_field
    for upd in req.fields:
        data = upd.dict(exclude_none=True)
        fid = data.pop("id")
        if data:
            update_field(fid, data)
    return {"success": True, "updated_count": len(req.fields)}


# ── 客户数据 ──────────────────────────────────────────────────

@app.get("/customers", tags=["Customers"])
async def get_customers():
    """从 customer_master.xlsx 读取客户列表"""
    from modules.excel_reader import list_customers
    customers = list_customers()
    return customers


@app.get("/customers/{customer_id}", tags=["Customers"])
async def get_customer(customer_id: str):
    """读取单个客户的完整数据"""
    from modules.excel_reader import get_customer as _get_customer
    data = _get_customer(customer_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"客户 {customer_id} 不存在")
    return data


# ── 填表执行 ──────────────────────────────────────────────────

@app.post("/fill-form", tags=["Fill"])
async def fill_form(req: FillFormRequest):
    """
    执行填表：
      1. 读取模板与客户数据
      2. 调用 filler.fill_pdf()
      3. 返回输出文件的下载链接

    返回：
      {
          "download_url": "/download/{filename}",
          "filled_count": int,
          "manual_count": int,
          "manual_fields": [...],
          ...
      }
    """
    # 获取客户数据
    from modules.excel_reader import get_customer as _get_customer
    customer_data = _get_customer(req.customer_id)
    if customer_data is None:
        raise HTTPException(status_code=404, detail=f"客户 {req.customer_id} 不存在")

    # 确认模板存在
    from modules.template_store import get_template as _get_template
    template = _get_template(req.template_id)
    if not template:
        raise HTTPException(status_code=404, detail=f"模板 {req.template_id} 不存在")

    # 推断源 PDF 路径
    source_pdf_path = str(UPLOADS_DIR / template["source_filename"])

    # 生成输出文件名
    output_filename = f"filled_{req.template_id}_{req.customer_id}_{uuid.uuid4().hex[:8]}.pdf"
    output_path = str(OUTPUTS_DIR / output_filename)

    # 执行填表
    try:
        from modules.filler import fill_pdf
        result = fill_pdf(
            template_id=req.template_id,
            customer_data=customer_data,
            output_path=output_path,
            source_pdf_path=source_pdf_path,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"源 PDF 文件不存在：{e}")
    except Exception as e:
        logger.error(f"填表失败：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"填表失败：{e}")

    return {
        **result,
        "download_url": f"/download/{output_filename}",
        "output_filename": output_filename,
    }


@app.get("/download/{filename}", tags=["Fill"])
async def download_file(filename: str):
    """下载已生成的填好 PDF"""
    file_path = OUTPUTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在或已过期")
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=filename,
    )


# ── 辅助接口 ──────────────────────────────────────────────────

@app.get("/standard-keys", tags=["Meta"])
async def get_standard_keys():
    """返回所有支持的标准字段键列表（供前端下拉选项）"""
    from modules.field_normalizer import get_all_standard_keys
    return {"keys": get_all_standard_keys()}


@app.post("/synonyms", tags=["Meta"])
async def add_synonym(req: SynonymRequest):
    """添加用户自定义同义词并使匹配器缓存失效"""
    from modules.template_store import add_synonym as _add_synonym
    from modules.field_normalizer import invalidate_cache
    _add_synonym(req.standard_key, req.synonym, source="user")
    invalidate_cache()
    return {"success": True}


# ──────────────────────────────────────────────────────────────
#  直接运行（开发用）
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
