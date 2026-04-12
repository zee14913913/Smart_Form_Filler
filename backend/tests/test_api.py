"""
test_api.py — Backend API test suite using FastAPI TestClient

Run from backend/ directory:
  pip install httpx pytest
  pytest tests/test_api.py -v

These tests verify:
  - All API routes respond correctly
  - Upload + analysis workflow works
  - Field normalizer maps common labels correctly
  - Customer data can be read from Excel
  - Fill-form pipeline executes without crash
  - Output PDF is generated as a valid file
"""

import os
import sys
import io
import pytest

# Ensure modules directory is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# ──────────────────────────────────────────────────────────────
#  Helper: create a minimal test PDF in memory
# ──────────────────────────────────────────────────────────────

def make_test_pdf() -> bytes:
    """Generate a minimal digital PDF with labeled form fields using reportlab."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    PAGE_W, PAGE_H = A4

    def draw_field(label, x, y, w=200, h=18):
        c.setFont("Helvetica", 7)
        c.drawString(x, y + h + 3, label)
        c.rect(x, y, w, h, stroke=1, fill=0)

    draw_field("Full Name / Nama Penuh", 40, 700)
    draw_field("IC No", 260, 700, 150)
    draw_field("Date of Birth", 40, 650, 140)
    draw_field("Mobile No", 200, 650, 140)
    draw_field("Email Address", 40, 600, 310)
    draw_field("Address Line 1 / Alamat", 40, 550, 310)
    draw_field("Postcode / Poskod", 40, 500, 100)
    draw_field("City / Bandar", 155, 500, 140)
    draw_field("State / Negeri", 310, 500, 140)
    draw_field("Employer Name / Nama Majikan", 40, 450, 310)
    draw_field("Monthly Income / Pendapatan Bulanan (RM)", 40, 400, 250)
    draw_field("Occupation / Pekerjaan", 310, 400, 140)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()


# ──────────────────────────────────────────────────────────────
#  Health / Root
# ──────────────────────────────────────────────────────────────

class TestHealth:
    def test_root_returns_ok(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Smart Form Filler" in data["message"]

    def test_standard_keys_returns_list(self):
        response = client.get("/standard-keys")
        assert response.status_code == 200
        keys = response.json()["keys"]
        assert isinstance(keys, list)
        assert len(keys) > 10
        assert "customer.full_name" in keys
        assert "customer.ic_no" in keys
        assert "customer.monthly_income" in keys


# ──────────────────────────────────────────────────────────────
#  Customers
# ──────────────────────────────────────────────────────────────

class TestCustomers:
    def test_list_customers_returns_records(self):
        response = client.get("/customers")
        assert response.status_code == 200
        customers = response.json()
        assert isinstance(customers, list)
        assert len(customers) >= 1
        # Verify first record has required fields
        first = customers[0]
        assert "customer_id" in first
        assert "full_name" in first
        assert "ic_no" in first

    def test_get_customer_c001(self):
        response = client.get("/customers/C001")
        assert response.status_code == 200
        data = response.json()
        assert data.get("customer.full_name") == "CHAN MEI LING"
        assert "880515" in data.get("customer.ic_no", "")

    def test_get_nonexistent_customer_returns_404(self):
        response = client.get("/customers/NONEXISTENT")
        assert response.status_code == 404


# ──────────────────────────────────────────────────────────────
#  Templates
# ──────────────────────────────────────────────────────────────

class TestTemplates:
    def test_list_templates_initially_returns_list(self):
        response = client.get("/templates")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_nonexistent_template_returns_404(self):
        response = client.get("/templates/999999")
        assert response.status_code == 404


# ──────────────────────────────────────────────────────────────
#  Upload + Analyze workflow
# ──────────────────────────────────────────────────────────────

class TestUploadAndAnalyze:
    @pytest.fixture(autouse=True)
    def setup_pdf(self):
        """Generate in-memory test PDF once per test class."""
        self.pdf_bytes = make_test_pdf()

    def test_upload_pdf_returns_template(self):
        response = client.post(
            "/upload-form",
            files={"file": ("test_form.pdf", self.pdf_bytes, "application/pdf")},
            data={"template_name": "Test Form", "institution": "Test Bank"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "template_id" in data
        assert data["template_id"] > 0
        assert data["template_name"] == "Test Form"
        assert data["field_count"] > 0
        self.__class__._template_id = data["template_id"]

    def test_fields_are_auto_matched(self):
        """After upload, at least some fields should be auto-matched."""
        response = client.post(
            "/upload-form",
            files={"file": ("test_form.pdf", self.pdf_bytes, "application/pdf")},
            data={"template_name": "Test Match Form", "institution": "QA"},
        )
        assert response.status_code == 200
        data = response.json()
        matched = sum(1 for f in data["fields"] if f.get("standard_key"))
        total = data["field_count"]
        # We expect at least 50% auto-match rate on a well-labeled form
        assert matched >= total * 0.5, f"Match rate too low: {matched}/{total}"

    def test_get_template_detail(self):
        """Upload then retrieve template detail."""
        upload_response = client.post(
            "/upload-form",
            files={"file": ("detail_form.pdf", self.pdf_bytes, "application/pdf")},
            data={"template_name": "Detail Test", "institution": "QA Bank"},
        )
        tid = upload_response.json()["template_id"]

        get_response = client.get(f"/templates/{tid}")
        assert get_response.status_code == 200
        template = get_response.json()
        assert template["id"] == tid
        assert "fields" in template
        assert isinstance(template["fields"], list)

    def test_update_fields(self):
        """Upload form, fetch template detail (which has field IDs), then confirm fields."""
        upload_response = client.post(
            "/upload-form",
            files={"file": ("update_form.pdf", self.pdf_bytes, "application/pdf")},
            data={"template_name": "Update Test"},
        )
        tid = upload_response.json()["template_id"]

        # Fetch full template detail — this includes field IDs from the DB
        detail_response = client.get(f"/templates/{tid}")
        assert detail_response.status_code == 200
        fields = detail_response.json()["fields"]

        updates = [
            {
                "id": f["id"],
                "standard_key": f.get("standard_key", ""),
                "is_confirmed": 1,
            }
            for f in fields
        ]

        put_response = client.put(
            f"/templates/{tid}/fields",
            json={"fields": updates},
        )
        assert put_response.status_code == 200
        assert put_response.json()["success"] is True


# ──────────────────────────────────────────────────────────────
#  Fill Form workflow
# ──────────────────────────────────────────────────────────────

class TestFillForm:
    @pytest.fixture(autouse=True)
    def setup_template(self):
        """Upload a template and confirm fields before testing fill."""
        pdf_bytes = make_test_pdf()
        upload = client.post(
            "/upload-form",
            files={"file": ("fill_test.pdf", pdf_bytes, "application/pdf")},
            data={"template_name": "Fill Test Form", "institution": "Test Bank"},
        )
        data = upload.json()
        self.template_id = data["template_id"]
        # Fetch template detail to get field IDs from DB
        detail = client.get(f"/templates/{self.template_id}")
        fields = detail.json()["fields"]
        updates = [{"id": f["id"], "standard_key": f.get("standard_key", ""), "is_confirmed": 1} for f in fields]
        client.put(f"/templates/{self.template_id}/fields", json={"fields": updates})

    def test_fill_form_generates_pdf(self):
        response = client.post(
            "/fill-form",
            json={"template_id": self.template_id, "customer_id": "C001"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["filled_count"] > 0
        assert "download_url" in data
        assert data["download_url"].startswith("/download/")
        assert data["output_filename"].endswith(".pdf")

    def test_fill_form_output_file_exists(self):
        response = client.post(
            "/fill-form",
            json={"template_id": self.template_id, "customer_id": "C002"},
        )
        assert response.status_code == 200
        data = response.json()
        output_path = data["output_path"]
        assert os.path.exists(output_path), f"Output file not found: {output_path}"
        assert os.path.getsize(output_path) > 1000, "Output PDF is suspiciously small"

    def test_fill_form_download_endpoint(self):
        fill_response = client.post(
            "/fill-form",
            json={"template_id": self.template_id, "customer_id": "C003"},
        )
        filename = fill_response.json()["output_filename"]
        download_response = client.get(f"/download/{filename}")
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/pdf"

    def test_fill_nonexistent_template_returns_404(self):
        response = client.post(
            "/fill-form",
            json={"template_id": 999999, "customer_id": "C001"},
        )
        assert response.status_code == 404

    def test_fill_nonexistent_customer_returns_404(self):
        response = client.post(
            "/fill-form",
            json={"template_id": self.template_id, "customer_id": "NOEXIST"},
        )
        assert response.status_code == 404


# ──────────────────────────────────────────────────────────────
#  Field Normalizer unit tests
# ──────────────────────────────────────────────────────────────

class TestFieldNormalizer:
    def test_exact_match_english(self):
        from modules.field_normalizer import normalize_label
        assert normalize_label("Full Name") == "customer.full_name"
        assert normalize_label("IC No") == "customer.ic_no"
        assert normalize_label("Email") == "customer.email"

    def test_malay_exact_match(self):
        from modules.field_normalizer import normalize_label
        assert normalize_label("Nama Penuh") == "customer.full_name"
        assert normalize_label("Poskod") == "customer.postcode"
        assert normalize_label("Warganegara") == "customer.nationality"

    def test_compound_bilingual_label(self):
        from modules.field_normalizer import normalize_label
        assert normalize_label("Full Name (as per IC) / Nama Penuh") == "customer.full_name"
        assert normalize_label("Date of Birth / Tarikh Lahir") == "customer.date_of_birth"
        assert normalize_label("Monthly Income / Pendapatan Bulanan (RM)") == "customer.monthly_income"
        assert normalize_label("Postcode / Poskod") == "customer.postcode"

    def test_fuzzy_match(self):
        from modules.field_normalizer import normalize_label
        assert normalize_label("Mobile Number") == "customer.mobile_no"
        assert normalize_label("Employer") == "customer.employer_name"

    def test_empty_returns_empty(self):
        from modules.field_normalizer import normalize_label
        assert normalize_label("") == ""
        assert normalize_label("   ") == ""

    def test_get_all_standard_keys_nonempty(self):
        from modules.field_normalizer import get_all_standard_keys
        keys = get_all_standard_keys()
        assert len(keys) > 20
        assert "customer.full_name" in keys


# ──────────────────────────────────────────────────────────────
#  Synonyms
# ──────────────────────────────────────────────────────────────

class TestSynonyms:
    def test_add_synonym(self):
        response = client.post(
            "/synonyms",
            json={"standard_key": "customer.full_name", "synonym": "Test Custom Synonym"},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_added_synonym_is_matchable(self):
        # Add unique synonym
        unique = "XYZ Test Label 99999"
        client.post("/synonyms", json={"standard_key": "customer.ic_no", "synonym": unique})
        # Invalidate cache and retest
        from modules.field_normalizer import normalize_label, invalidate_cache
        invalidate_cache()
        result = normalize_label(unique)
        assert result == "customer.ic_no"
