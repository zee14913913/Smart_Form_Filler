-- Smart Form Filler — SQLite 初始化脚本
-- 版本 2.0：增加 Settings、fill_jobs、fill_job_fields 表

-- ──────────────────────────────────────────────────────────────
-- 核心模板表
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS form_templates (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT    NOT NULL,
    institution         TEXT,
    source_filename     TEXT,                         -- uploads/ 目录下的文件名（兼容旧版）
    original_pdf_path   TEXT,                         -- 规范路径：data/forms/{id}/original.pdf
    page_count          INTEGER DEFAULT 1,
    status              TEXT    DEFAULT 'draft',       -- draft | confirmed | active
    created_at          TEXT    DEFAULT (datetime('now')),
    updated_at          TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS form_fields (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id         INTEGER NOT NULL REFERENCES form_templates(id) ON DELETE CASCADE,
    page_number         INTEGER NOT NULL DEFAULT 1,
    raw_label           TEXT,
    standard_key        TEXT,
    cell_x0             REAL,
    cell_top            REAL,
    cell_x1             REAL,
    cell_bottom         REAL,
    font_size_max       REAL    DEFAULT 10.0,
    font_size_min       REAL    DEFAULT 6.0,
    font_size_step      REAL    DEFAULT 0.5,
    align               TEXT    DEFAULT 'left',
    padding_left        REAL    DEFAULT 0.0,
    padding_vertical    REAL    DEFAULT 0.0,
    is_confirmed        INTEGER DEFAULT 0,
    needs_manual        INTEGER DEFAULT 0,
    created_at          TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS field_synonyms (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_key    TEXT    NOT NULL,
    synonym         TEXT    NOT NULL,
    source          TEXT    DEFAULT 'builtin',
    UNIQUE(standard_key, synonym)
);

-- ──────────────────────────────────────────────────────────────
-- Settings 全局配置表（单行，id=1）
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS system_settings (
    id                          INTEGER PRIMARY KEY DEFAULT 1,  -- 永远只有一行
    -- 字体
    default_font_name           TEXT    DEFAULT 'Helvetica',
    default_font_size_max       REAL    DEFAULT 11.0,
    default_font_size_min       REAL    DEFAULT 6.0,
    default_font_size_step      REAL    DEFAULT 0.5,
    -- Padding
    default_left_padding_px     REAL    DEFAULT 4.0,            -- pt 单位
    default_vertical_strategy   TEXT    DEFAULT 'center_baseline', -- center_baseline | top | custom_offset
    default_custom_offset       REAL    DEFAULT 0.0,
    -- 对齐与多行
    default_text_align          TEXT    DEFAULT 'left',
    default_multiline_behavior  TEXT    DEFAULT 'single_line_truncate',
    -- 溢出策略
    overflow_policy             TEXT    DEFAULT 'mark_manual_without_writing',
    manual_threshold            INTEGER DEFAULT 80,              -- 超过此字符数直接标记 manual
    -- 渲染策略（固定值，只读）
    render_base                 TEXT    DEFAULT 'original_pdf',  -- 不可修改
    allow_custom_drawn_templates INTEGER DEFAULT 0,              -- 强制 false
    allow_modify_original_content INTEGER DEFAULT 0,            -- 强制 false
    -- 验证阈值
    verify_pixel_diff_threshold REAL    DEFAULT 0.02,           -- 非填写区域最大允许差异比例
    updated_at                  TEXT    DEFAULT (datetime('now'))
);

-- 插入默认配置（只在初次创建时插入）
INSERT OR IGNORE INTO system_settings (id) VALUES (1);

-- ──────────────────────────────────────────────────────────────
-- Fill Jobs 表（每次填表任务的记录）
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fill_jobs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id         INTEGER NOT NULL REFERENCES form_templates(id),
    customer_ref        TEXT    NOT NULL,              -- customer_id，如 C001
    customer_name       TEXT,
    output_path         TEXT,                          -- 输出 PDF 完整路径
    output_filename     TEXT,                          -- 仅文件名
    status              TEXT    DEFAULT 'pending',     -- pending | running | done | failed
    filled_count        INTEGER DEFAULT 0,
    skipped_count       INTEGER DEFAULT 0,
    manual_count        INTEGER DEFAULT 0,
    total_fields        INTEGER DEFAULT 0,
    -- 验证结果
    verification_status TEXT    DEFAULT 'pending',     -- pending | pass | warning | fail
    verification_verdict TEXT,                        -- pass | warning | fail
    pass_count          INTEGER DEFAULT 0,
    warning_count       INTEGER DEFAULT 0,
    fail_count          INTEGER DEFAULT 0,
    created_at          TEXT    DEFAULT (datetime('now')),
    updated_at          TEXT    DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────────────────────────
-- Fill Job Fields 表（每个字段的填写结果）
-- ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fill_job_fields (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      INTEGER NOT NULL REFERENCES fill_jobs(id) ON DELETE CASCADE,
    field_id    INTEGER NOT NULL REFERENCES form_fields(id),
    value       TEXT,                                  -- 实际填入的值
    status      TEXT    DEFAULT 'skip',               -- write | skip | manual | fail
    reason      TEXT,                                  -- 如 "overflow" / "no_value" / "ok"
    font_size   REAL,
    text_x      REAL,
    text_y      REAL,
    -- 验证结果
    verify_status TEXT  DEFAULT 'pending',             -- pass | warning | fail | manual
    verify_reason TEXT
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
