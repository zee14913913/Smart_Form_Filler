"""
create_test_pdf.py
------------------
Creates a realistic sample bank form PDF for testing the Smart Form Filler.
Uses reportlab to produce a digital (text-selectable) PDF with actual form fields.

Run: python create_test_pdf.py
Output: test-data/sample_bank_form.pdf
"""

import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm

OUTPUT_DIR = "test-data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "sample_bank_form.pdf")

os.makedirs(OUTPUT_DIR, exist_ok=True)

PAGE_W, PAGE_H = A4  # 595.27 x 841.89 pt


def draw_labeled_field(c, label: str, x: float, y: float, width: float, height: float = 18):
    """Draw a labeled input field (box + label above)."""
    # Label
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.drawString(x, y + height + 3, label)
    # Box
    c.setFillColorRGB(1, 1, 1)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.rect(x, y, width, height, stroke=1, fill=1)


def draw_section_header(c, title: str, y: float):
    """Draw a section header bar."""
    c.setFillColorRGB(0.25, 0.22, 0.42)  # Morandi violet
    c.rect(40, y, PAGE_W - 80, 18, stroke=0, fill=1)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(48, y + 5, title)


def create_sample_form():
    c = canvas.Canvas(OUTPUT_FILE, pagesize=A4)
    c.setTitle("Personal Loan Application Form — Sample Bank")
    c.setAuthor("Smart Form Filler Test")

    # ── Header ────────────────────────────────────────────────────
    c.setFillColorRGB(0.15, 0.12, 0.28)
    c.rect(0, PAGE_H - 70, PAGE_W, 70, stroke=0, fill=1)

    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, PAGE_H - 38, "SAMPLE BANK BERHAD")
    c.setFont("Helvetica", 9)
    c.drawString(40, PAGE_H - 54, "PERSONAL LOAN APPLICATION FORM")

    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.8, 0.8, 0.8)
    c.drawRightString(PAGE_W - 40, PAGE_H - 54, "Form No: SBB-PL-2024")

    # ── Section 1: Personal Information ───────────────────────────
    y = PAGE_H - 105
    draw_section_header(c, "SECTION A — PERSONAL INFORMATION / MAKLUMAT PERIBADI", y)

    y -= 38
    # Row 1
    draw_labeled_field(c, "Full Name (as per IC) / Nama Penuh", 40, y, 340)
    draw_labeled_field(c, "IC No / No. Kad Pengenalan", 400, y, 155)

    y -= 45
    # Row 2
    draw_labeled_field(c, "Date of Birth / Tarikh Lahir", 40, y, 120)
    draw_labeled_field(c, "Nationality / Warganegara", 178, y, 120)
    draw_labeled_field(c, "Gender / Jantina", 316, y, 100)
    draw_labeled_field(c, "Race / Bangsa", 434, y, 121)

    y -= 45
    # Row 3
    draw_labeled_field(c, "Marital Status / Status Perkahwinan", 40, y, 150)
    draw_labeled_field(c, "Religion / Agama", 208, y, 150)
    draw_labeled_field(c, "Mobile No / No. Tel Bimbit", 376, y, 179)

    y -= 45
    # Row 4
    draw_labeled_field(c, "Email Address", 40, y, 260)
    draw_labeled_field(c, "Home Tel / No. Tel Rumah", 318, y, 237)

    # ── Section 2: Address ─────────────────────────────────────────
    y -= 50
    draw_section_header(c, "SECTION B — RESIDENTIAL ADDRESS / ALAMAT KEDIAMAN", y)

    y -= 38
    draw_labeled_field(c, "Address Line 1 / Alamat", 40, y, 515)

    y -= 35
    draw_labeled_field(c, "Address Line 2", 40, y, 515)

    y -= 35
    draw_labeled_field(c, "Postcode / Poskod", 40, y, 100)
    draw_labeled_field(c, "City / Bandar", 160, y, 180)
    draw_labeled_field(c, "State / Negeri", 360, y, 195)

    # ── Section 3: Employment ──────────────────────────────────────
    y -= 55
    draw_section_header(c, "SECTION C — EMPLOYMENT DETAILS / BUTIRAN PEKERJAAN", y)

    y -= 38
    draw_labeled_field(c, "Employer Name / Nama Majikan", 40, y, 300)
    draw_labeled_field(c, "Occupation / Pekerjaan", 360, y, 195)

    y -= 45
    draw_labeled_field(c, "Employer Address / Alamat Majikan", 40, y, 515)

    y -= 35
    draw_labeled_field(c, "Monthly Income / Pendapatan Bulanan (RM)", 40, y, 200)
    draw_labeled_field(c, "Employment Type / Jenis Pekerjaan", 260, y, 175)
    draw_labeled_field(c, "Years with Employer", 455, y, 100)

    # ── Section 4: Loan Details ────────────────────────────────────
    y -= 55
    draw_section_header(c, "SECTION D — LOAN DETAILS / BUTIRAN PINJAMAN", y)

    y -= 38
    draw_labeled_field(c, "Loan Amount Applied (RM) / Jumlah Pinjaman", 40, y, 200)
    draw_labeled_field(c, "Loan Tenure (Months) / Tempoh Pinjaman", 260, y, 175)
    draw_labeled_field(c, "Bank Name / Nama Bank", 455, y, 100)

    y -= 45
    draw_labeled_field(c, "Bank Account No / No. Akaun Bank", 40, y, 250)

    # ── Declaration ────────────────────────────────────────────────
    y -= 55
    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(0.2, 0.2, 0.2)
    c.drawString(40, y, "DECLARATION / PENGAKUAN")
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    decl = (
        "I/We hereby declare that all the information given in this form is true and accurate. "
        "I/We authorise the Bank to verify the information provided."
    )
    c.drawString(40, y - 14, decl[:90])
    c.drawString(40, y - 25, decl[90:])

    y -= 60
    # Signature fields
    draw_labeled_field(c, "Applicant Signature / Tandatangan Pemohon", 40, y, 200, 40)
    draw_labeled_field(c, "Date / Tarikh", 260, y, 140, 40)
    draw_labeled_field(c, "Staff Verified / Kakitangan", 420, y, 135, 40)

    # ── Footer ────────────────────────────────────────────────────
    c.setFont("Helvetica", 6)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawString(40, 28, "Sample Bank Berhad (Reg. No. 123456-X) | Jalan Bukit Bintang, 50200 Kuala Lumpur")
    c.drawRightString(PAGE_W - 40, 28, "Page 1 of 1")

    c.showPage()
    c.save()
    print(f"✓ Sample form PDF created: {OUTPUT_FILE}")
    print(f"  Size: {os.path.getsize(OUTPUT_FILE)} bytes")


if __name__ == "__main__":
    create_sample_form()
