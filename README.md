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

## 目录结构

```
Smart_Form_Filler/
├── backend/
│   ├── main.py                  # FastAPI 应用入口，所有 API 路由
│   ├── requirements.txt
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── analyzer.py          # PDF/图片字段分析（pdfplumber + OpenCV + OCR）
│   │   ├── field_normalizer.py  # 字段标准化（rapidfuzz 模糊匹配，4 阶段匹配）
│   │   ├── template_store.py    # SQLite 模板库 CRUD
│   │   ├── excel_reader.py      # customer_master.xlsx 读取
│   │   └── filler.py            # PDF 精准回填（ReportLab + pypdf）
│   ├── database/
│   │   ├── init_db.sql          # 数据库建表 + 同义词种子脚本
│   │   └── templates.db         # 运行时自动生成（首次启动时创建）
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_api.py          # 24 个端到端 API 测试（FastAPI TestClient）
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
│   ├── .env.local.example       # 前端环境变量示例
│   ├── package.json
│   └── next.config.mjs
├── test-data/
│   └── sample_bank_form.pdf     # 测试用 A4 银行表格（33 个字段）
├── customer_master.xlsx         # 客户主资料（含 5 条示例记录 + FieldDictionary）
├── generate_excel.py            # 生成 customer_master.xlsx 的脚本
├── create_test_pdf.py           # 生成测试用 PDF 的脚本
├── DRY_RUN_REPORT.md            # 端到端干跑测试报告（已通过）
└── README.md
```

---

## 前提条件

### 必装软件

| 软件 | 版本 | 安装方式 |
|------|------|---------|
| Python | 3.10 或以上 | https://www.python.org/downloads/ |
| Node.js | 18 或以上 | https://nodejs.org/ |
| Git | 任意 | 自带 / Xcode Command Line Tools |

### 可选依赖（扫描版 PDF / OCR）

> 数字 PDF 无需以下依赖，仅扫描版 PDF（照片/影印件）才需要。

| 软件 | 用途 |
|------|------|
| Tesseract OCR | 扫描图像文字识别 |
| Poppler | PDF → 图像转换 |

---

## macOS 完整安装步骤

### 第 0 步：安装系统依赖（可选，仅扫描 PDF 需要）

```bash
# 安装 Homebrew（如已安装可跳过）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Tesseract 和 Poppler
brew install tesseract poppler

# 如需支持繁体/简体中文 OCR
brew install tesseract-lang
```

---

### 第 1 步：克隆仓库

```bash
git clone https://github.com/zee14913913/Smart_Form_Filler.git
cd Smart_Form_Filler
```

---

### 第 2 步：生成客户主资料 Excel

> 如果仓库中已有 `customer_master.xlsx`，可跳过此步。

```bash
# 在项目根目录（Smart_Form_Filler/）运行
python3 generate_excel.py
```

这会生成含 5 条示例客户的 `customer_master.xlsx`。可直接编辑此文件，替换为真实客户数据。

---

### 第 3 步：启动后端

```bash
# 进入 backend 目录
cd backend

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 确认 pip 已激活
which pip      # 应输出 .../backend/venv/bin/pip
which python3  # 应输出 .../backend/venv/bin/python3

# 安装后端依赖（约 2-5 分钟，依网速而定）
pip install -r requirements.txt

# 启动后端服务
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

后端启动成功标志：

```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

后端访问地址：
- Swagger API 文档：http://localhost:8000/docs
- ReDoc 文档：http://localhost:8000/redoc

> **注意**：后端窗口需保持打开。启动前端时请另开一个终端标签页。

---

### 第 4 步：启动前端

> 在新的终端标签页中操作（不要关闭后端终端）。

```bash
# 回到项目根目录，再进入 frontend
cd Smart_Form_Filler/frontend

# 安装前端依赖（约 1-3 分钟）
npm install

# 配置 API 地址（如不存在 .env.local 则创建）
cp .env.local.example .env.local
# 默认内容：NEXT_PUBLIC_API_URL=http://localhost:8000
# 如后端运行在不同端口，请修改此文件

# 启动前端开发服务器
npm run dev
```

前端启动成功标志：

```
▲ Next.js 14.x.x
- Local: http://localhost:3000
✓ Ready in x.xs
```

前端访问地址：http://localhost:3000

---

## 完整使用流程（图形界面）

### 步骤 1：上传表格

1. 打开 http://localhost:3000/upload
2. 拖拽或点击选择需要填写的 PDF 表格
3. 填写 **Template Name**（模板名称）和 **Institution**（机构名称）
4. 点击 **Start Analysis**
5. 等待系统分析完成（约 1-5 秒，取决于 PDF 复杂度）

系统会自动：
- 识别 PDF 中所有可填写字段的位置
- 提取字段标签文字
- 与标准字段库进行模糊匹配

---

### 步骤 2：确认字段映射

1. 分析完成后，系统会跳转至模板详情页（或手动访问 http://localhost:3000/templates）
2. 点击对应模板，进入 **字段映射编辑** 页面
3. 检查每个字段的 `Standard Key` 是否正确映射
   - 正确示例：`Full Name (as per IC)` → `full_name`
   - 如有错误，在下拉菜单中选择正确的标准键
4. 可调整每个字段的字体大小（`font_size`）、对齐方式（`align`）
5. 点击 **Save & Confirm All Fields** 保存

---

### 步骤 3：准备客户数据

编辑项目根目录的 `customer_master.xlsx`：

| 列名 | 说明 |
|------|------|
| `customer_id` | 唯一客户编号（如 C001）|
| `full_name` | 客户全名 |
| `ic_number` | 身份证号 |
| `date_of_birth` | 出生日期 |
| `email` | 电子邮件 |
| `phone` | 联系电话 |
| `address_line1` | 地址第一行 |
| `address_line2` | 地址第二行 |
| `city` | 城市 |
| `postcode` | 邮编 |
| `state` | 州/省 |
| `country` | 国家 |
| ... | 更多字段见 FieldDictionary 工作表 |

---

### 步骤 4：执行填表

1. 访问 http://localhost:3000/fill
2. 在 **Select Template** 下拉菜单中选择已确认的模板
3. 在 **Select Customer** 下拉菜单中选择客户记录
4. 点击 **Fill & Generate PDF**
5. 等待系统生成（约 1-3 秒）
6. 点击 **Download Filled PDF** 下载结果

---

## 命令行用法（无图形界面）

所有操作也可直接通过 REST API 完成：

```bash
# 1. 上传表格并分析
curl -X POST http://localhost:8000/upload-form \
  -F "file=@test-data/sample_bank_form.pdf" \
  -F "template_name=Bank Account Opening Form" \
  -F "institution=Test Bank"

# 返回示例：{"template_id": 1, "field_count": 33, "matched": 26}

# 2. 查看字段详情
curl http://localhost:8000/templates/1

# 3. 查看客户列表
curl http://localhost:8000/customers

# 4. 执行填表
curl -X POST http://localhost:8000/fill-form \
  -H "Content-Type: application/json" \
  -d '{"template_id": 1, "customer_id": "C001"}'

# 返回示例：{"download_url": "/download/filled_1_C001_xxxxxxxx.pdf", "filled": 26}

# 5. 下载填写完成的 PDF
curl http://localhost:8000/download/filled_1_C001_xxxxxxxx.pdf -o output.pdf
```

---

## 运行测试套件

```bash
cd backend
source venv/bin/activate    # 如果尚未激活虚拟环境

# 运行全部 24 个 API 测试
python3 -m pytest tests/test_api.py -v

# 预期输出：24 passed
```

测试覆盖范围：
- `POST /upload-form` — 上传与分析
- `GET /templates` / `GET /templates/{id}` — 模板读取
- `PUT /templates/{id}/fields` — 字段映射更新
- `GET /customers` / `GET /customers/{id}` — 客户数据读取
- `POST /fill-form` — 填表执行与 PDF 生成
- `GET /download/{filename}` — 文件下载
- `GET /standard-keys` — 标准键列表
- `POST /synonyms` — 自定义同义词

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

> 完整请求/响应 Schema 见 http://localhost:8000/docs（Swagger UI）。

---

## 环境变量

在 `frontend/` 目录创建 `.env.local` 文件：

```env
# 后端 API 地址（默认 http://localhost:8000）
NEXT_PUBLIC_API_URL=http://localhost:8000
```

参考模板：`frontend/.env.local.example`

---

## 故障排除（macOS）

### ❌ `zsh: command not found: python`

macOS 默认不含 `python`，请统一使用 `python3`：

```bash
python3 --version    # 应输出 Python 3.10+
pip3 --version       # 或用 pip（如已激活 venv）
```

如仍无 Python 3，从官网安装：https://www.python.org/downloads/mac-osx/

---

### ❌ `pip: command not found` / `ModuleNotFoundError: No module named 'fastapi'`

原因：未激活虚拟环境，或依赖未安装。

```bash
# 确保在 backend/ 目录
cd backend

# 创建并激活虚拟环境
python3 -m venv venv
source venv/bin/activate

# 确认 pip 指向虚拟环境内
which pip    # 应包含 venv/bin/pip

# 安装依赖
pip install -r requirements.txt
```

---

### ❌ 后端启动报错：`uvicorn: command not found`

请使用 `python3 -m uvicorn`，而非直接调用 `uvicorn`：

```bash
# 正确启动方式
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

### ❌ 后端启动报错：`Address already in use` / port 8000 occupied

```bash
# 查找占用 8000 端口的进程
lsof -i :8000

# 强制终止（替换 <PID> 为实际进程号）
kill -9 <PID>

# 重新启动后端
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

### ❌ 前端报错：`Error: NEXT_PUBLIC_API_URL is not defined` / 请求 undefined

```bash
cd frontend
cp .env.local.example .env.local
# 确认文件内容
cat .env.local    # 应显示：NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev       # 重启前端
```

---

### ❌ 前端启动报错：`Cannot find module '...'` / `npm ERR!`

```bash
cd frontend
rm -rf node_modules .next
npm install
npm run dev
```

---

### ❌ 上传 PDF 后字段数为 0

可能原因：
1. **PDF 为扫描件** — 需要 Tesseract OCR：`brew install tesseract poppler`
2. **PDF 无嵌入文字层** — 同上
3. **PDF 表格用图像绘制** — 系统会尝试 OpenCV 轮廓检测，效果因 PDF 质量而异

如使用本仓库测试数据，可先用 `test-data/sample_bank_form.pdf`（已知可识别 33 字段）验证系统是否正常运行。

---

### ❌ 填表输出 PDF 中文字显示为方块 / 乱码

当前版本使用 ReportLab 内置字体（仅 ASCII），中文字符需要额外配置。

解决方案：

1. 下载 Noto Sans SC 字体：https://fonts.google.com/noto/specimen/Noto+Sans+SC
2. 将 `NotoSansSC-Regular.ttf` 放入 `backend/fonts/` 目录
3. 在 `backend/modules/filler.py` 中取消注释中文字体注册代码：
   ```python
   FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")
   FONT_PATH = os.path.join(FONT_DIR, "NotoSansSC-Regular.ttf")
   if os.path.exists(FONT_PATH):
       pdfmetrics.registerFont(TTFont("NotoSansSC", FONT_PATH))
       FONT_NAME = "NotoSansSC"
   ```

---

### ❌ `templates.db` 丢失 / 模板列表为空

SQLite 数据库在后端首次启动时自动创建。如数据库损坏或需要重置：

```bash
cd backend/database
rm -f templates.db   # 删除旧数据库
# 重启后端，数据库会自动重建
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

---

### ❌ `customer_master.xlsx` 不存在

```bash
# 在项目根目录生成
cd Smart_Form_Filler
python3 generate_excel.py
# 生成后验证
ls -lh customer_master.xlsx
```

---

## 已验证的端到端测试结果

详见 [`DRY_RUN_REPORT.md`](./DRY_RUN_REPORT.md)。

核心结论：

| 检查项 | 结果 |
|--------|------|
| 后端启动 | ✅ 正常 |
| 前端启动（5 页面） | ✅ 全部 HTTP 200 |
| PDF 上传 + 字段识别 | ✅ 33 字段检测，26 自动匹配 |
| 模板确认 | ✅ 成功写入 SQLite |
| 客户数据读取 | ✅ 5 条记录正常加载 |
| 填表执行 | ✅ C001: 26 字段填写，C002: 26 字段填写 |
| 输出 PDF 下载 | ✅ 文件存在，可下载 |
| 全套 API 测试 | ✅ 24/24 通过 |

---

## OCR 支持（扫描版 PDF）

### macOS

```bash
brew install tesseract poppler
# 中文语言包（繁体 + 简体）
brew install tesseract-lang
```

### Ubuntu / Debian

```bash
sudo apt-get install tesseract-ocr poppler-utils
sudo apt-get install tesseract-ocr-chi-sim tesseract-ocr-chi-tra
```

### Windows

1. 下载安装包：https://github.com/UB-Mannheim/tesseract/wiki
2. 在 `backend/modules/analyzer.py` 中配置路径：
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

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

## License

MIT License · Built for internal business operations
