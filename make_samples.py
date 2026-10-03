from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

out = Path(__file__).parent / "data" / "inbox"
out.mkdir(parents=True, exist_ok=True)
samples = [
    ("Northstar_Components_2026-09.pdf", "Northstar Components", "NSC-2026-0918", "INR ", "48,250.00", "2026-10-25", "Industrial fasteners and assembly supplies"),
    ("Meridian_Cloud_2026-09.pdf", "Meridian Cloud Services", "MCS-2026-0441", "INR ", "126,500.00", "2026-10-18", "Annual cloud infrastructure renewal"),
    ("Pioneer_Office_2026-09.pdf", "Pioneer Office Supply", "POS-2026-0872", "INR ", "8,940.00", "2026-10-12", "Office stationery and printer supplies"),
]
for filename, vendor, number, symbol, amount, due, description in samples:
    path = out / filename
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"Invoice {number}")
    c.setFillColorRGB(.055, .11, .16); c.rect(0, 735, 595, 107, fill=1, stroke=0)
    c.setFillColorRGB(.45, .88, .74); c.setFont("Helvetica-Bold", 11); c.drawString(48, 795, "CENTRALIGN · SAMPLE VENDOR")
    c.setFillColorRGB(.93, .96, .98); c.setFont("Helvetica-Bold", 27); c.drawString(48, 758, "INVOICE")
    c.setFillColorRGB(.12, .18, .23); c.setFont("Helvetica-Bold", 15); c.drawString(48, 690, vendor)
    c.setFont("Helvetica", 10); c.drawString(48, 670, "Accounts Receivable · Synthetic demo document")
    c.setFillColorRGB(.39, .45, .51); c.setFont("Helvetica", 10)
    c.drawString(48, 615, f"Vendor: {vendor}"); c.drawString(48, 592, f"Invoice No: {number}")
    c.drawString(48, 569, f"Invoice Date: 2026-09-18"); c.drawString(48, 546, f"Due Date: {due}")
    c.setFillColorRGB(.055, .11, .16); c.rect(48, 485, 499, 1, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 10); c.drawString(48, 458, "DESCRIPTION"); c.drawString(452, 458, "AMOUNT")
    c.setFont("Helvetica", 10); c.drawString(48, 428, description); c.drawRightString(545, 428, f"{symbol}{amount}")
    c.setFillColorRGB(.055, .11, .16); c.rect(48, 396, 499, 1, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 14); c.drawString(385, 365, "Total:"); c.drawRightString(545, 365, f"{symbol}{amount}")
    c.setFillColorRGB(.39, .45, .51); c.setFont("Helvetica", 9); c.drawString(48, 78, "Synthetic invoice for the CentrAlign AI autonomous operator demo. No real vendor or payment data.")
    c.save()
