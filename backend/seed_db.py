"""
seed_db.py — 数据库种子脚本（幂等）
--------------------------------------
幂等：可重复执行，不会重复插入已存在的数据。

功能：
  1. 初始化 DB 表结构（如不存在）
  2. 从 data/forms/1/ 重新注册模板（若不存在）
  3. 确保 C001-C005 demo 客户数据存在（含完整字段）
  4. 确保所有字段的 padding_left_px >= 4.0（使用 settings 默认值）

运行方式：
  cd backend && python3 seed_db.py
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_db")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from modules.template_store import (
    init_database, get_connection, get_settings,
    create_template, save_fields, get_template,
    update_template_status,
)
from modules.analyzer import analyze_pdf
from modules.field_normalizer import normalize_fields


# ──────────────────────────────────────────────────────────────
# 1. 初始化数据库
# ──────────────────────────────────────────────────────────────

logger.info("Step 1: 初始化数据库...")
init_database()

# ──────────────────────────────────────────────────────────────
# 2. 种子模板（从 data/forms/ 重新注册，幂等：按名称去重）
# ──────────────────────────────────────────────────────────────

logger.info("Step 2: 检查并注册模板...")

settings = get_settings()
default_padding = float(settings.get("default_left_padding_px", 4.0))

FORM_DEFINITIONS = [
    {
        "folder_id": 1,
        "name": "Sample Bank Personal Loan Form",
        "institution": "Sample Bank Berhad",
    },
    {
        "folder_id": 2,
        "name": "Standard Loan Application Form",
        "institution": "Standard Finance",
    },
]

conn = get_connection()
try:
    existing_names = {
        r[0] for r in conn.execute("SELECT name FROM form_templates").fetchall()
    }
finally:
    conn.close()

for defn in FORM_DEFINITIONS:
    fid = defn["folder_id"]
    pdf_path = os.path.join(BASE_DIR, "data", "forms", str(fid), "original.pdf")

    if not os.path.exists(pdf_path):
        logger.warning(f"  ⚠ data/forms/{fid}/original.pdf 不存在，跳过")
        continue

    if defn["name"] in existing_names:
        logger.info(f"  ✓ 模板 '{defn['name']}' 已存在，跳过")
        continue

    logger.info(f"  → 分析 data/forms/{fid}/original.pdf ...")
    try:
        fields = analyze_pdf(pdf_path)
        fields = normalize_fields(fields)

        # 应用默认 padding
        for f in fields:
            if not f.get("padding_left_px") or float(f.get("padding_left_px", 0)) <= 0:
                f["padding_left_px"] = default_padding

        # 确定页数
        page_count = max((f.get("page_number", 1) for f in fields), default=1)

        # 创建模板（直接存 original.pdf 的绝对路径）
        tid = create_template(
            name=defn["name"],
            institution=defn["institution"],
            source_filename=f"original.pdf",
            page_count=page_count,
            original_pdf_path=os.path.abspath(pdf_path),
        )

        if fields:
            save_fields(tid, fields)

        logger.info(
            f"  ✓ 创建模板 id={tid} '{defn['name']}' — "
            f"{len(fields)} 字段，默认 padding={default_padding}"
        )

    except Exception as e:
        logger.error(f"  ✗ 注册模板失败 (folder {fid}): {e}")


# ──────────────────────────────────────────────────────────────
# 3. 修复所有字段的 padding_left_px（如果为 0）
# ──────────────────────────────────────────────────────────────

logger.info("Step 3: 修复 padding_left_px = 0 的字段...")
conn = get_connection()
try:
    result = conn.execute(
        "UPDATE form_fields SET padding_left_px = ? "
        "WHERE padding_left_px IS NULL OR padding_left_px <= 0",
        (default_padding,),
    )
    conn.commit()
    logger.info(f"  ✓ 修复了 {result.rowcount} 个字段的 padding_left_px → {default_padding}")
finally:
    conn.close()


# ──────────────────────────────────────────────────────────────
# 4. 确保 demo 客户存在（幂等 upsert）
# ──────────────────────────────────────────────────────────────

logger.info("Step 4: 确保 C001-C005 demo 客户存在...")

DEMO_CUSTOMERS = [
    {
        "customer_id": "C001",
        "full_name": "CHAN MEI LING",
        "ic_no": "880515-14-5678",
        "date_of_birth": "15/05/1988",
        "nationality": "Malaysian",
        "gender": "Female",
        "marital_status": "Single",
        "race": "Chinese",
        "religion": "Buddhist",
        "mobile_no": "012-3456789",
        "home_tel": "03-87654321",
        "email": "chanmei@email.com",
        "address_line1": "No. 12, Jalan Bunga Raya",
        "address_line2": "Taman Sri Muda",
        "address_line3": "",
        "postcode": "40150",
        "city": "Shah Alam",
        "state": "Selangor",
        "country": "Malaysia",
        "employer_name": "ABC Sdn Bhd",
        "employer_address": "Lot 5, Jalan Industri, Shah Alam",
        "monthly_income": "5500",
        "annual_income": "66000",
        "occupation": "Engineer",
        "employment_type": "Full-time",
        "years_with_employer": "5",
        "bank_name": "Maybank",
        "bank_account_no": "1234567890",
        "loan_amount": "80000",
        "loan_tenure": "10",
    },
    {
        "customer_id": "C002",
        "full_name": "AHMAD BIN RAHMAN",
        "ic_no": "791230-10-2345",
        "date_of_birth": "30/12/1979",
        "nationality": "Malaysian",
        "gender": "Male",
        "marital_status": "Married",
        "race": "Malay",
        "religion": "Islam",
        "mobile_no": "019-8765432",
        "home_tel": "03-76543210",
        "email": "ahmad.rahman@email.com",
        "address_line1": "No. 45, Jalan Kenanga",
        "address_line2": "Taman Desa",
        "address_line3": "",
        "postcode": "58100",
        "city": "Kuala Lumpur",
        "state": "W.P. Kuala Lumpur",
        "country": "Malaysia",
        "employer_name": "XYZ Corporation Bhd",
        "employer_address": "Tower 5, KLCC, KL",
        "monthly_income": "8000",
        "annual_income": "96000",
        "occupation": "Manager",
        "employment_type": "Full-time",
        "years_with_employer": "8",
        "bank_name": "CIMB Bank",
        "bank_account_no": "9876543210",
        "loan_amount": "150000",
        "loan_tenure": "20",
    },
    {
        "customer_id": "C003",
        "full_name": "MUTHU KRISHNAN A/L SUPPIAH",
        "ic_no": "920318-07-8901",
        "date_of_birth": "18/03/1992",
        "nationality": "Malaysian",
        "gender": "Male",
        "marital_status": "Single",
        "race": "Indian",
        "religion": "Hindu",
        "mobile_no": "016-5432109",
        "home_tel": "",
        "email": "muthu.k@email.com",
        "address_line1": "No. 8, Jalan Tamil",
        "address_line2": "Brickfields",
        "address_line3": "",
        "postcode": "50470",
        "city": "Kuala Lumpur",
        "state": "W.P. Kuala Lumpur",
        "country": "Malaysia",
        "employer_name": "Tech Solutions Sdn Bhd",
        "employer_address": "Cyberjaya, Selangor",
        "monthly_income": "6500",
        "annual_income": "78000",
        "occupation": "Software Developer",
        "employment_type": "Full-time",
        "years_with_employer": "3",
        "bank_name": "Public Bank",
        "bank_account_no": "5566778899",
        "loan_amount": "100000",
        "loan_tenure": "15",
    },
    {
        "customer_id": "C004",
        "full_name": "LIM SOO PING",
        "ic_no": "850722-12-3456",
        "date_of_birth": "22/07/1985",
        "nationality": "Malaysian",
        "gender": "Female",
        "marital_status": "Married",
        "race": "Chinese",
        "religion": "Christian",
        "mobile_no": "011-23456789",
        "home_tel": "04-1234567",
        "email": "limsooping@email.com",
        "address_line1": "No. 22, Lorong Perak",
        "address_line2": "Georgetown",
        "address_line3": "",
        "postcode": "10000",
        "city": "George Town",
        "state": "Pulau Pinang",
        "country": "Malaysia",
        "employer_name": "Penang Manufacturing Co.",
        "employer_address": "Bayan Lepas Industrial Estate",
        "monthly_income": "7200",
        "annual_income": "86400",
        "occupation": "Production Supervisor",
        "employment_type": "Full-time",
        "years_with_employer": "7",
        "bank_name": "Hong Leong Bank",
        "bank_account_no": "1122334455",
        "loan_amount": "120000",
        "loan_tenure": "18",
    },
    {
        "customer_id": "C005",
        "full_name": "NUR FARAHANA BINTI ZULKIFLI",
        "ic_no": "950601-08-7890",
        "date_of_birth": "01/06/1995",
        "nationality": "Malaysian",
        "gender": "Female",
        "marital_status": "Single",
        "race": "Malay",
        "religion": "Islam",
        "mobile_no": "013-9876543",
        "home_tel": "",
        "email": "nurf.zulkifli@email.com",
        "address_line1": "Blok B-12-3, Pangsapuri Maju",
        "address_line2": "Jalan Damansara",
        "address_line3": "",
        "postcode": "50490",
        "city": "Kuala Lumpur",
        "state": "W.P. Kuala Lumpur",
        "country": "Malaysia",
        "employer_name": "Government Servant",
        "employer_address": "Putrajaya",
        "monthly_income": "4800",
        "annual_income": "57600",
        "occupation": "Civil Servant",
        "employment_type": "Full-time",
        "years_with_employer": "4",
        "bank_name": "Bank Islam",
        "bank_account_no": "2233445566",
        "loan_amount": "60000",
        "loan_tenure": "8",
    },
]

conn = get_connection()
try:
    for c in DEMO_CUSTOMERS:
        existing = conn.execute(
            "SELECT id FROM customers WHERE customer_id = ?", (c["customer_id"],)
        ).fetchone()

        if existing:
            # Update to ensure all fields are populated
            cols = [k for k in c if k != "customer_id"]
            set_clause = ", ".join(f"{k} = ?" for k in cols)
            set_clause += ", updated_at = datetime('now')"
            vals = [c[k] for k in cols] + [c["customer_id"]]
            conn.execute(
                f"UPDATE customers SET {set_clause} WHERE customer_id = ?", vals
            )
            logger.info(f"  ✓ 更新客户 {c['customer_id']} — {c['full_name']}")
        else:
            cols = list(c.keys())
            placeholders = ", ".join("?" for _ in cols)
            conn.execute(
                f"INSERT INTO customers ({', '.join(cols)}) VALUES ({placeholders})",
                [c[k] for k in cols],
            )
            logger.info(f"  ✓ 新建客户 {c['customer_id']} — {c['full_name']}")

    conn.commit()
finally:
    conn.close()

# ──────────────────────────────────────────────────────────────
# 5. 报告
# ──────────────────────────────────────────────────────────────

conn = get_connection()
try:
    t_count = conn.execute("SELECT COUNT(*) FROM form_templates").fetchone()[0]
    f_count = conn.execute("SELECT COUNT(*) FROM form_fields").fetchone()[0]
    c_count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    pad_ok  = conn.execute(
        "SELECT COUNT(*) FROM form_fields WHERE padding_left_px >= 4.0"
    ).fetchone()[0]
finally:
    conn.close()

logger.info("=" * 50)
logger.info(f"✅ 种子脚本完成")
logger.info(f"   模板: {t_count} 个")
logger.info(f"   字段: {f_count} 个（padding>=4: {pad_ok}）")
logger.info(f"   客户: {c_count} 个")
logger.info("=" * 50)
