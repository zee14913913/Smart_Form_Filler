-- Smart Form Filler — SQLite 初始化脚本
-- 按蓝图 §3.3 SQLite 模板库结构创建

CREATE TABLE IF NOT EXISTS form_templates (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,             -- 模板名称，例如 "CIMB 信用卡申请表"
    institution     TEXT,                         -- 所属机构/银行
    source_filename TEXT,                         -- 上传时的原始文件名
    page_count      INTEGER DEFAULT 1,
    status          TEXT    DEFAULT 'draft',       -- draft | confirmed | active
    created_at      TEXT    DEFAULT (datetime('now')),
    updated_at      TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS form_fields (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id     INTEGER NOT NULL REFERENCES form_templates(id) ON DELETE CASCADE,
    page_number     INTEGER NOT NULL DEFAULT 1,
    raw_label       TEXT,                         -- OCR/PDF 读取到的原始标签文字
    standard_key    TEXT,                         -- 映射后的标准字段键，例如 customer.full_name
    cell_x0         REAL,                         -- 格子左边 x 坐标（PDF 点单位）
    cell_top        REAL,                         -- 格子顶部 y 坐标
    cell_x1         REAL,                         -- 格子右边 x 坐标
    cell_bottom     REAL,                         -- 格子底部 y 坐标
    font_size_max   REAL    DEFAULT 10.0,
    font_size_min   REAL    DEFAULT 6.0,
    font_size_step  REAL    DEFAULT 0.5,
    align           TEXT    DEFAULT 'left',       -- left | center | right
    padding_left    REAL    DEFAULT 0.0,          -- 由 filler 根据字号自动计算，此列作覆盖留存
    padding_vertical REAL   DEFAULT 0.0,
    is_confirmed    INTEGER DEFAULT 0,            -- 0=未确认, 1=已确认
    needs_manual    INTEGER DEFAULT 0,            -- 1=需要人工补填
    created_at      TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS field_synonyms (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_key    TEXT    NOT NULL,             -- 标准字段键
    synonym         TEXT    NOT NULL,             -- 同义词或别名
    source          TEXT    DEFAULT 'builtin',    -- builtin | user
    UNIQUE(standard_key, synonym)
);

-- 内置同义词种子数据
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
  ('customer.address_line1', '地址', 'builtin'),
  ('customer.address_line1', 'Alamat', 'builtin'),
  ('customer.address_line1', 'Home Address', 'builtin'),
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
