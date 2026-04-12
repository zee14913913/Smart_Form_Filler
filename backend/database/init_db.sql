-- Smart Form Filler — SQLite 初始化脚本
-- 版本 3.0：严格遵守 PRD Master Prompt
-- 结果状态：只允许 pass / fail，无任何灰色中间态

-- ──────────────────────────────────────────────────────────────
-- 模板表
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS form_templates (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    NOT NULL,
    institution         TEXT,
    source_filename     TEXT,
    original_pdf_path   TEXT,                         -- data/forms/{id}/original.pdf
    page_count          INTEGER DEFAULT 1,
    status              TEXT    DEFAULT 'draft',       -- draft | confirmed | active
    created_at          TEXT    DEFAULT (datetime('now')),
    updated_at          TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────────────────────────
-- 字段表（PRD §四 完整字段列表）
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS form_fields (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id         INTEGER NOT NULL REFERENCES form_templates(id) ON DELETE CASCADE,
    page_number         INTEGER NOT NULL DEFAULT 1,
    raw_label           TEXT,                         -- 从原件识别的标签文本
    standard_key        TEXT,                         -- 标准字段名，如 full_name / ic_number
    -- PRD §四：字段类型
    field_type          TEXT    DEFAULT 'text',       -- text | checkbox | date | phone | signature
    -- 格子坐标（pdfplumber top-down 坐标系）
    cell_x0             REAL,
    cell_top            REAL,
    cell_x1             REAL,
    cell_bottom         REAL,
    -- 排版参数（PRD §四）
    font_name           TEXT,                         -- 留空则用 system_settings 默认值
    font_size_max       REAL    DEFAULT 10.0,
    font_size_min       REAL    DEFAULT 6.0,
    font_size_step      REAL    DEFAULT 0.5,
    padding_left_px     REAL    DEFAULT 0.0,          -- 留0则用 system_settings 默认值
    padding_vertical_strategy TEXT DEFAULT '',        -- 留空则用 system_settings 默认值
    text_align          TEXT    DEFAULT 'left',       -- left | center | right
    multiline           INTEGER DEFAULT 0,            -- 0=单行, 1=允许多行
    max_chars           INTEGER DEFAULT 0,            -- 0=不限；>0=超过此数直接 fail
    -- 映射状态
    is_confirmed        INTEGER DEFAULT 0,            -- 0=待确认, 1=已确认
    -- 注意：needs_manual 已从 PRD 中移除，不再使用
    created_at          TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────────────────────────
-- 同义词表
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS field_synonyms (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_key    TEXT    NOT NULL,
    synonym         TEXT    NOT NULL,
    source          TEXT    DEFAULT 'builtin',
    UNIQUE(standard_key, synonym)
);

-- ──────────────────────────────────────────────────────────────
-- 系统设置表（PRD §六 全部字段）
-- 说明：只允许一行（id=1），所有修改都是 UPDATE
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS system_settings (
    id                          INTEGER PRIMARY KEY DEFAULT 1,
    -- 字体（PRD §六）
    default_font_name           TEXT    DEFAULT 'Helvetica',
    default_font_size_max       REAL    DEFAULT 11.0,
    default_font_size_min       REAL    DEFAULT 6.0,
    default_font_size_step      REAL    DEFAULT 0.5,
    -- Padding（PRD §六）
    default_left_padding_px     REAL    DEFAULT 4.0,
    default_vertical_strategy   TEXT    DEFAULT 'center_baseline',
    -- 对齐
    default_text_align          TEXT    DEFAULT 'left',
    -- 溢出/失败策略（PRD §六）
    -- overflow_policy 已废除灰色选项；系统唯一允许的行为：
    --   字号降到 font_size_min 仍放不下 → 字段直接 fail
    -- fail_threshold: 字符数超过此值 → 字段直接 fail（不尝试收缩）
    fail_threshold              INTEGER DEFAULT 200,
    -- 验证阈值
    verify_pixel_diff_threshold REAL    DEFAULT 0.01,  -- 非填写区域最大差异比例，超过即 fail
    -- 渲染策略（硬性固定，禁止修改）
    render_base                 TEXT    DEFAULT 'original_pdf',
    allow_custom_drawn_templates INTEGER DEFAULT 0,
    allow_modify_original_content INTEGER DEFAULT 0,
    updated_at                  TEXT    DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO system_settings (id) VALUES (1);

-- ──────────────────────────────────────────────────────────────
-- Fill Jobs 表（PRD §四 Phase 4）
-- 结果列只允许 pass / fail，无 warning / manual
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fill_jobs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id         INTEGER NOT NULL REFERENCES form_templates(id),
    customer_ref        TEXT    NOT NULL,
    customer_name       TEXT,
    original_pdf_path   TEXT,
    output_path         TEXT,
    output_filename     TEXT,
    status              TEXT    DEFAULT 'running',    -- running | done | failed
    -- 字段统计（PRD §四：只有 pass / fail）
    total_fields        INTEGER DEFAULT 0,
    total_pass          INTEGER DEFAULT 0,
    total_fail          INTEGER DEFAULT 0,
    -- 验证结果（只允许 pass / fail / pending）
    verification_status TEXT    DEFAULT 'pending',
    final_verdict       TEXT,                         -- pass | fail（无其他值）
    -- 时间
    created_at          TEXT    DEFAULT (datetime('now')),
    updated_at          TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────────────────────────
-- Fill Job Fields 表（字段级结果，只有 pass / fail）
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fill_job_fields (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          INTEGER NOT NULL REFERENCES fill_jobs(id) ON DELETE CASCADE,
    field_id        INTEGER NOT NULL REFERENCES form_fields(id),
    value           TEXT,
    -- 填写状态：write（写入）| fail（失败，不写入）
    fill_status     TEXT    DEFAULT 'fail',
    fill_reason     TEXT,                             -- ok | overflow | no_value | invalid_cell | char_limit
    -- 排版记录
    font_size       REAL,
    text_x          REAL,
    text_y          REAL,
    -- 验证状态：pass | fail（无其他值）
    verify_status   TEXT    DEFAULT 'pending',
    verify_reason   TEXT                              -- ok | out_of_bounds | no_padding | vertical_shift | overflow
);

-- ──────────────────────────────────────────────────────────────
-- Customers 表（数据库主数据源，替代 customer_master.xlsx 直读）
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS customers (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    -- 基础信息
    customer_id         TEXT    NOT NULL UNIQUE,  -- 如 C001
    full_name           TEXT    NOT NULL,
    ic_no               TEXT,
    date_of_birth       TEXT,
    nationality         TEXT,
    gender              TEXT,
    marital_status      TEXT,
    race                TEXT,
    religion            TEXT,
    -- 联系方式
    mobile_no           TEXT,
    home_tel            TEXT,
    email               TEXT,
    -- 地址
    address_line1       TEXT,
    address_line2       TEXT,
    address_line3       TEXT,
    postcode            TEXT,
    city                TEXT,
    state               TEXT,
    country             TEXT    DEFAULT 'Malaysia',
    -- 工作/财务
    employer_name       TEXT,
    employer_address    TEXT,
    monthly_income      TEXT,
    annual_income       TEXT,
    occupation          TEXT,
    employment_type     TEXT,
    years_with_employer TEXT,
    -- 银行/贷款
    bank_name           TEXT,
    bank_account_no     TEXT,
    loan_amount         TEXT,
    loan_tenure         TEXT,
    -- 审计
    created_at          TEXT    DEFAULT (datetime('now')),
    updated_at          TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────────────────────────
-- 内置同义词种子数据
-- ──────────────────────────────────────────────────────────────

INSERT OR IGNORE INTO field_synonyms (standard_key, synonym, source) VALUES
  ('customer.full_name', '姓名', 'builtin'),
  ('customer.full_name', 'Full Name', 'builtin'),
  ('customer.full_name', '申请人姓名', 'builtin'),
  ('customer.full_name', 'Name', 'builtin'),
  ('customer.full_name', 'Nama', 'builtin'),
  ('customer.full_name', 'Nama Penuh', 'builtin'),
  ('customer.full_name', 'Applicant Name', 'builtin'),
  ('customer.ic_no', 'IC No', 'builtin'),
  ('customer.ic_no', 'NRIC No', 'builtin'),
  ('customer.ic_no', '身份证号码', 'builtin'),
  ('customer.ic_no', 'MyKad No', 'builtin'),
  ('customer.ic_no', 'No. KP', 'builtin'),
  ('customer.ic_no', 'Identity Card No', 'builtin'),
  ('customer.date_of_birth', 'Date of Birth', 'builtin'),
  ('customer.date_of_birth', 'DOB', 'builtin'),
  ('customer.date_of_birth', '出生日期', 'builtin'),
  ('customer.date_of_birth', 'Tarikh Lahir', 'builtin'),
  ('customer.nationality', 'Nationality', 'builtin'),
  ('customer.nationality', '国籍', 'builtin'),
  ('customer.nationality', 'Warganegara', 'builtin'),
  ('customer.gender', 'Gender', 'builtin'),
  ('customer.gender', '性别', 'builtin'),
  ('customer.gender', 'Jantina', 'builtin'),
  ('customer.marital_status', 'Marital Status', 'builtin'),
  ('customer.marital_status', '婚姻状况', 'builtin'),
  ('customer.marital_status', 'Status Perkahwinan', 'builtin'),
  ('customer.mobile_no', 'Mobile No', 'builtin'),
  ('customer.mobile_no', '手机号码', 'builtin'),
  ('customer.mobile_no', 'Phone', 'builtin'),
  ('customer.mobile_no', 'Tel No', 'builtin'),
  ('customer.mobile_no', 'No. Tel Bimbit', 'builtin'),
  ('customer.email', 'Email', 'builtin'),
  ('customer.email', 'E-mail', 'builtin'),
  ('customer.email', '电子邮件', 'builtin'),
  ('customer.address_line1', 'Address', 'builtin'),
  ('customer.address_line1', 'Address Line 1', 'builtin'),
  ('customer.address_line1', 'Address 1', 'builtin'),
  ('customer.address_line1', '地址', 'builtin'),
  ('customer.address_line1', 'Alamat', 'builtin'),
  ('customer.address_line1', 'Alamat 1', 'builtin'),
  ('customer.address_line1', 'Home Address', 'builtin'),
  ('customer.address_line2', 'Address Line 2', 'builtin'),
  ('customer.address_line2', 'Address 2', 'builtin'),
  ('customer.address_line2', '地址第二行', 'builtin'),
  ('customer.address_line2', 'Alamat 2', 'builtin'),
  ('customer.postcode', 'Postcode', 'builtin'),
  ('customer.postcode', 'Postal Code', 'builtin'),
  ('customer.postcode', '邮政编码', 'builtin'),
  ('customer.postcode', 'Poskod', 'builtin'),
  ('customer.city', 'City', 'builtin'),
  ('customer.city', '城市', 'builtin'),
  ('customer.city', 'Bandar', 'builtin'),
  ('customer.state', 'State', 'builtin'),
  ('customer.state', '州属', 'builtin'),
  ('customer.state', 'Negeri', 'builtin'),
  ('customer.employer_name', 'Employer Name', 'builtin'),
  ('customer.employer_name', 'Company Name', 'builtin'),
  ('customer.employer_name', '雇主名称', 'builtin'),
  ('customer.employer_name', 'Nama Majikan', 'builtin'),
  ('customer.monthly_income', 'Monthly Income', 'builtin'),
  ('customer.monthly_income', '月收入', 'builtin'),
  ('customer.monthly_income', 'Pendapatan Bulanan', 'builtin'),
  ('customer.monthly_income', 'Gross Monthly Salary', 'builtin'),
  ('customer.occupation', 'Occupation', 'builtin'),
  ('customer.occupation', '职业', 'builtin'),
  ('customer.occupation', 'Pekerjaan', 'builtin'),
  ('customer.race', 'Race', 'builtin'),
  ('customer.race', '种族', 'builtin'),
  ('customer.race', 'Bangsa', 'builtin'),
  ('customer.religion', 'Religion', 'builtin'),
  ('customer.religion', '宗教', 'builtin'),
  ('customer.religion', 'Agama', 'builtin');
