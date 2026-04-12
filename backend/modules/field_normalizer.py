"""
field_normalizer.py
-------------------
将 analyzer 输出的 raw_label 映射到标准字段键（standard_key）。

策略（按优先级）：
1. 精确匹配（大小写不敏感）
2. 标准化后精确匹配（去除空格、标点）
3. RapidFuzz 模糊匹配，score_cutoff=75
4. 无法匹配时返回空字符串（前端让用户手动选择）

同义词来源：
- 内置字典（BUILTIN_SYNONYMS）
- SQLite field_synonyms 表（template_store.get_all_synonyms()）
"""

import re
import unicodedata
from typing import Optional

from rapidfuzz import process as fuzz_process, fuzz
from modules.template_store import get_all_synonyms


# ──────────────────────────────────────────────────────────────
#  内置静态字典（补充 SQLite 种子数据之外的常见变体）
# ──────────────────────────────────────────────────────────────

BUILTIN_SYNONYMS: dict[str, list[str]] = {
    "customer.full_name": [
        "full name", "name", "applicant name", "nama", "nama penuh",
        "nama pemohon", "applicant's name", "nama penuh pemohon",
        "姓名", "申请人姓名", "申请人名称",
    ],
    "customer.ic_no": [
        "ic no", "nric no", "mykad no", "no kp", "no ic",
        "identity card no", "identity card number",
        "no. kad pengenalan", "no. kp", "no. mykad",
        "身份证号码", "身份证号", "ic号码",
    ],
    "customer.date_of_birth": [
        "date of birth", "dob", "birth date", "tarikh lahir",
        "出生日期", "生日",
    ],
    "customer.nationality": [
        "nationality", "warganegara", "kewarganegaraan",
        "国籍",
    ],
    "customer.gender": [
        "gender", "sex", "jantina", "jenis kelamin",
        "性别",
    ],
    "customer.marital_status": [
        "marital status", "status perkahwinan", "status kahwin",
        "婚姻状况", "婚姻状态",
    ],
    "customer.race": [
        "race", "bangsa", "ethnicity",
        "种族", "民族",
    ],
    "customer.religion": [
        "religion", "agama",
        "宗教", "宗教信仰",
    ],
    "customer.mobile_no": [
        "mobile no", "mobile number", "phone", "tel no", "telephone",
        "no. tel bimbit", "no. telefon", "contact no",
        "手机号码", "手机号", "电话号码",
    ],
    "customer.home_tel": [
        "home tel", "home telephone", "no. tel rumah",
        "家庭电话",
    ],
    "customer.email": [
        "email", "e-mail", "email address",
        "电子邮件", "电邮",
    ],
    "customer.address_line1": [
        "address", "home address", "residential address",
        "alamat", "alamat rumah", "alamat kediaman",
        "地址", "住址", "居住地址",
    ],
    "customer.address_line2": [
        "address line 2", "address 2", "alamat 2",
        "地址第二行",
    ],
    "customer.address_line3": [
        "address line 3", "address 3",
        "地址第三行",
    ],
    "customer.postcode": [
        "postcode", "postal code", "zip code", "poskod",
        "邮政编码", "邮编",
    ],
    "customer.city": [
        "city", "town", "bandar",
        "城市", "市",
    ],
    "customer.state": [
        "state", "negeri", "province",
        "州属", "州", "省",
    ],
    "customer.country": [
        "country", "negara",
        "国家",
    ],
    "customer.employer_name": [
        "employer name", "company name", "employer",
        "nama majikan", "nama syarikat",
        "雇主名称", "公司名称", "雇主",
    ],
    "customer.employer_address": [
        "employer address", "company address", "office address",
        "alamat majikan", "alamat syarikat",
        "工作地址", "公司地址",
    ],
    "customer.monthly_income": [
        "monthly income", "gross monthly salary", "monthly salary",
        "pendapatan bulanan", "gaji bulanan",
        "月收入", "月薪", "每月收入",
    ],
    "customer.annual_income": [
        "annual income", "yearly income",
        "年收入", "年薪",
    ],
    "customer.occupation": [
        "occupation", "job title", "position", "profession",
        "pekerjaan", "jawatan",
        "职业", "职位", "工作",
    ],
    "customer.employment_type": [
        "employment type", "employment status",
        "jenis pekerjaan",
        "雇佣类型", "就业类型",
    ],
    "customer.years_with_employer": [
        "years with employer", "length of service",
        "tempoh berkhidmat",
        "工龄", "工作年限",
    ],
    "customer.bank_name": [
        "bank name", "nama bank",
        "银行名称",
    ],
    "customer.bank_account_no": [
        "bank account no", "account number", "no. akaun bank",
        "银行账号", "账号",
    ],
    "customer.loan_amount": [
        "loan amount", "financing amount", "amount applied",
        "jumlah pinjaman", "jumlah pembiayaan",
        "贷款金额", "申请金额",
    ],
    "customer.loan_tenure": [
        "loan tenure", "repayment period", "tenure",
        "tempoh pinjaman",
        "贷款期限", "还款期",
    ],
}


def _normalize_text(text: str) -> str:
    """标准化文本：转小写、去除多余空白、去除标点"""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", text)  # 保留汉字
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_matcher() -> dict[str, str]:
    """
    构建 {normalized_synonym: standard_key} 查找表，
    合并内置字典和 SQLite 中的同义词。
    """
    matcher: dict[str, str] = {}

    # 1. 内置字典
    for std_key, synonyms in BUILTIN_SYNONYMS.items():
        for syn in synonyms:
            matcher[_normalize_text(syn)] = std_key
        # 标准键本身也作为同义词
        matcher[_normalize_text(std_key.split(".")[-1].replace("_", " "))] = std_key

    # 2. 数据库同义词（可能在运行中动态添加）
    try:
        db_synonyms = get_all_synonyms()
        for std_key, synonyms in db_synonyms.items():
            for syn in synonyms:
                matcher[_normalize_text(syn)] = std_key
    except Exception:
        # 数据库尚未初始化时不报错
        pass

    return matcher


# 模块级缓存（进程内有效，重启后重新构建）
_matcher_cache: Optional[dict[str, str]] = None


def get_matcher() -> dict[str, str]:
    """获取缓存的匹配器，如不存在则构建"""
    global _matcher_cache
    if _matcher_cache is None:
        _matcher_cache = build_matcher()
    return _matcher_cache


def invalidate_cache():
    """当同义词表更新时，调用此函数使缓存失效"""
    global _matcher_cache
    _matcher_cache = None


def normalize_label(raw_label: str) -> str:
    """
    将 raw_label 映射到标准字段键。
    返回空字符串表示无法自动匹配，需要用户手动选择。

    匹配流程：
    1. 精确匹配（normalized）
    2. RapidFuzz 模糊匹配（score_cutoff=75）
    3. 返回空字符串
    """
    if not raw_label or not raw_label.strip():
        return ""

    matcher = get_matcher()
    normalized = _normalize_text(raw_label)

    # 步骤 1：精确匹配
    if normalized in matcher:
        return matcher[normalized]

    # 步骤 2：RapidFuzz 模糊匹配
    choices = list(matcher.keys())
    result = fuzz_process.extractOne(
        normalized,
        choices,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=75,
    )
    if result:
        matched_key, score, _ = result
        return matcher[matched_key]

    return ""


def normalize_fields(fields: list[dict]) -> list[dict]:
    """
    批量处理字段列表，为每个字段添加 standard_key。
    输入/输出格式与 analyzer.py 一致。
    """
    for field in fields:
        raw = field.get("raw_label", "")
        field["standard_key"] = normalize_label(raw)
        field["match_confidence"] = _compute_confidence(raw)
    return fields


def _compute_confidence(raw_label: str) -> float:
    """
    返回 0.0~1.0 的置信度：
    - 1.0  精确匹配
    - 0.75~0.99  模糊匹配
    - 0.0  未匹配
    """
    if not raw_label:
        return 0.0
    matcher = get_matcher()
    normalized = _normalize_text(raw_label)
    if normalized in matcher:
        return 1.0
    choices = list(matcher.keys())
    result = fuzz_process.extractOne(
        normalized,
        choices,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=75,
    )
    if result:
        return round(result[1] / 100, 2)
    return 0.0


def get_all_standard_keys() -> list[str]:
    """返回所有已知标准字段键列表（供前端下拉选项）"""
    keys = set(BUILTIN_SYNONYMS.keys())
    try:
        db_synonyms = get_all_synonyms()
        keys.update(db_synonyms.keys())
    except Exception:
        pass
    return sorted(keys)
