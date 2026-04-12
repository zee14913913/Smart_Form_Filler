# Smart Form Filler — 智能表格自动填写系统

> 上传任意银行/机构 PDF 表格，系统自动分析填写字段位置，从客户主资料 Excel 中精准回填，生成填写完整的 PDF 供下载。

---

## 系统架构

```
frontend (Next.js)          backend (FastAPI)          数据层
──────────────            ─────────────────────     ──────────────
上传表格 PDF    ────────▶  POST /upload-form        SQLite templates.db
确认字段映射   ◀────────  GET  /templates/:id       customer_master.xlsx
选择客户       ────────▶  GET  /customers            uploads/ (原始 PDF)
执行填表       ────────▶  POST /fill-form            outputs/ (填好 PDF)
下载 PDF       ◀────────  GET  /download/:filename
```

---

## 快速启动

### 前提条件

| 软件 | 版本要求 |
|------|---------|
| Python | 3.10 或以上 |
| Node.js | 18 或以上 |
| Tesseract OCR | 可选（扫描 PDF 需要）|
| Poppler | 可选（扫描 PDF 需要）|

---

### 1. 后端启动

```bash
# 进入 backend 目录
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate      # macOS/Linux
# venv\Scripts\activate       # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务（开发模式，支持热重载）
uvicorn main:app --reload --port 8000
```

后端启动后访问：
- API 文档（Swagger）：http://localhost:8000/docs
- API 文档（ReDoc）：http://localhost:8000/redoc

---

### 2. 生成客户主资料 Excel

首次运行前，需在项目根目录生成 `customer_master.xlsx`：

```bash
# 在项目根目录（Smart_Form_Filler/）运行
python generate_excel.py
```

这会生成包含 5 条示例客户记录的 Excel 文件。直接编辑此文件添加真实客户数据。

---

### 3. 前端启动

```bash
# 进入 frontend 目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端启动后访问：http://localhost:3000

---

## 使用流程

### 步骤 1：上传表格
1. 访问 http://localhost:3000/upload
2. 拖拽或选择 PDF/图片表格文件
3. 填写模板名称与机构名称
4. 点击 **Start Analysis** → 系统自动识别填写字段

### 步骤 2：确认字段映射
1. 分析完成后，前往模板详情页（`/templates/:id`）
2. 检查每个字段的 `standard_key` 映射是否正确
3. 可调整字体大小、对齐方式等排版参数
4. 点击 **Save & Confirm All Fields**

### 步骤 3：填表
1. 访问 http://localhost:3000/fill
2. 选择已确认的模板 + 客户记录
3. 点击 **Fill & Generate PDF**
4. 点击 **Download Filled PDF** 下载结果

---

## 目录结构

```
Smart_Form_Filler/
├── backend/
│   ├── main.py                  # FastAPI 应用入口，所有 API 路由
│   ├── requirements.txt
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── analyzer.py          # PDF/图片字段分析（pdfplumber + OpenCV + OCR）
│   │   ├── field_normalizer.py  # 字段标准化（rapidfuzz 模糊匹配）
│   │   ├── template_store.py    # SQLite 模板库 CRUD
│   │   ├── excel_reader.py      # customer_master.xlsx 读取
│   │   └── filler.py            # PDF 精准回填（ReportLab + pypdf）
│   ├── database/
│   │   ├── init_db.sql          # 数据库建表 + 同义词种子脚本
│   │   └── templates.db         # 运行时自动生成
│   ├── uploads/                 # 上传的原始 PDF 文件
│   └── outputs/                 # 生成的填写完成 PDF
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css      # Morandi Violet Design System 全局样式
│   │   │   ├── layout.tsx       # 全局布局（带侧栏）
│   │   │   ├── page.tsx         # Dashboard
│   │   │   ├── upload/          # 上传表格页
│   │   │   ├── templates/       # 模板列表页 + 详情/编辑页
│   │   │   ├── customers/       # 客户列表页
│   │   │   ├── fill/            # 填表执行页
│   │   │   └── settings/        # 系统设置页
│   │   ├── components/
│   │   │   └── Sidebar.tsx      # 侧栏导航
│   │   └── lib/
│   │       └── api.ts           # 后端 API 调用封装（axios）
│   ├── package.json
│   └── next.config.mjs
├── customer_master.xlsx         # 客户主资料（需先运行 generate_excel.py）
├── generate_excel.py            # 生成 customer_master.xlsx 的脚本
├── smart_form_filler_blueprint_with_ui.md  # 完整系统设计蓝图
└── README.md
```

---

## API 参考

| Method | Endpoint | 说明 |
|--------|----------|------|
| POST | `/upload-form` | 上传 PDF，分析字段，创建模板 |
| GET | `/templates` | 列出所有模板 |
| GET | `/templates/{id}` | 读取模板详情（含字段列表）|
| PUT | `/templates/{id}/fields` | 批量更新字段映射与排版参数 |
| GET | `/customers` | 从 Excel 读取客户列表 |
| GET | `/customers/{id}` | 读取单个客户完整数据 |
| POST | `/fill-form` | 执行填表，返回下载链接 |
| GET | `/download/{filename}` | 下载生成的 PDF |
| GET | `/standard-keys` | 获取所有标准字段键 |
| POST | `/synonyms` | 添加自定义同义词 |

---

## 扫描 PDF / OCR 支持

对于扫描版 PDF，系统使用 Tesseract OCR 识别字段标签。生产部署时需要：

### macOS
```bash
brew install tesseract poppler
# 如需中文支持：
brew install tesseract-lang
```

### Ubuntu/Debian
```bash
sudo apt-get install tesseract-ocr poppler-utils
# 中文语言包：
sudo apt-get install tesseract-ocr-chi-sim tesseract-ocr-chi-tra
```

### Windows
1. 下载 Tesseract 安装包：https://github.com/UB-Mannheim/tesseract/wiki
2. 在 `backend/modules/analyzer.py` 中取消注释并配置路径：
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

---

## 中文字体支持

PDF 回填目前使用 ReportLab 内置的 Helvetica 字体（仅支持 ASCII）。

如需支持中文回填，需在 `backend/fonts/` 目录放置支持中文的 TTF 字体，并在 `filler.py` 中取消注释字体注册代码：

```python
# 取消注释以下代码（filler.py 第 ~35 行）
FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
FONT_PATH = os.path.join(FONT_DIR, "NotoSansSC-Regular.ttf")
if os.path.exists(FONT_PATH):
    pdfmetrics.registerFont(TTFont("NotoSansSC", FONT_PATH))
    FONT_NAME = "NotoSansSC"
```

推荐字体：[Noto Sans SC](https://fonts.google.com/noto/specimen/Noto+Sans+SC)

---

## 设计系统

前端使用 **Morandi Violet Design System（莫兰迪紫系）**：

| 变量 | 色值 | 用途 |
|------|------|------|
| `--vd` | `#4A3F6B` | 深紫，侧栏主色 |
| `--vm` | `#7B6FA0` | 中紫，active/accent |
| `--vl` | `#C5BCE0` | 浅紫，边框/分割线 |
| `--vp` | `#F0EEF8` | 极浅紫，hover 背景 |
| `--ow` | `#F8F6F2` | 主内容区背景 |
| `--ink` | `#1E1A2E` | 主文字颜色 |

字体：IBM Plex Sans（UI）/ Playfair Display（标题）/ DM Sans（正文）/ Cormorant Garamond（KPI）

---

## 环境变量

在 `frontend/` 目录创建 `.env.local` 文件可自定义 API 地址：

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## License

MIT License · Built for internal business operations
