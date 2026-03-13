"""Generate PDF report for SiteGrade scan results."""
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT


GREEN = HexColor("#059669")
DARK = HexColor("#111827")
GRAY = HexColor("#6B7280")
LIGHT_GREEN = HexColor("#D1FAE5")
LIGHT_RED = HexColor("#FEE2E2")
LIGHT_YELLOW = HexColor("#FEF3C7")
WHITE = HexColor("#FFFFFF")


def grade_color(score):
    if score >= 80:
        return HexColor("#059669")
    elif score >= 60:
        return HexColor("#D97706")
    else:
        return HexColor("#DC2626")


def grade_bg(score):
    if score >= 80:
        return LIGHT_GREEN
    elif score >= 60:
        return LIGHT_YELLOW
    else:
        return LIGHT_RED


def generate_pdf(report_data):
    """Generate a PDF report and return bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm,
                            leftMargin=20 * mm, rightMargin=20 * mm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Title2", parent=styles["Title"], fontSize=24, textColor=DARK))
    styles.add(ParagraphStyle("Section", parent=styles["Heading2"], fontSize=16,
                              textColor=DARK, spaceAfter=8))
    styles.add(ParagraphStyle("Body2", parent=styles["Normal"], fontSize=10, textColor=GRAY))
    styles.add(ParagraphStyle("Grade", parent=styles["Title"], fontSize=48,
                              alignment=TA_CENTER))
    styles.add(ParagraphStyle("Issue", parent=styles["Normal"], fontSize=9,
                              textColor=HexColor("#DC2626"), leftIndent=10))
    styles.add(ParagraphStyle("Good", parent=styles["Normal"], fontSize=9,
                              textColor=HexColor("#059669"), leftIndent=10))

    elements = []

    domain = report_data["domain"]
    grade = report_data["overall_grade"]
    score = report_data["overall_score"]
    scores = report_data["scores"]

    # Header
    elements.append(Paragraph("SiteGrade Report", styles["Title2"]))
    elements.append(Paragraph(f"Website: {domain}", styles["Body2"]))
    elements.append(Spacer(1, 10 * mm))

    # Overall Grade
    elements.append(Paragraph(f'<font color="{grade_color(score).hexval()}">{grade}</font>',
                              styles["Grade"]))
    elements.append(Paragraph(f"Overall Score: {score}/100", styles["Body2"]))
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", color=HexColor("#E5E7EB")))
    elements.append(Spacer(1, 5 * mm))

    # Score summary table
    score_data = [["Category", "Score", "Grade"]]
    categories = [
        ("SSL Certificate", "ssl"),
        ("Security Headers", "headers"),
        ("Performance", "performance"),
        ("Tech Stack", "techstack"),
        ("DNS Health", "dns"),
        ("Mobile Ready", "mobile"),
    ]
    for label, key in categories:
        s = scores[key]
        g = "A+" if s >= 90 else "A" if s >= 80 else "B" if s >= 70 else "C" if s >= 60 else "D" if s >= 50 else "F"
        score_data.append([label, f"{s}/100", g])

    tbl = Table(score_data, colWidths=[90 * mm, 35 * mm, 35 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#F9FAFB")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(tbl)
    elements.append(Spacer(1, 8 * mm))

    # SSL section
    ssl = report_data["ssl"]
    elements.append(Paragraph("1. SSL Certificate", styles["Section"]))
    if ssl.get("valid"):
        elements.append(Paragraph(f"✓ Valid certificate from {ssl.get('issuer', 'Unknown')}", styles["Good"]))
        elements.append(Paragraph(f"  Expires: {ssl.get('expires', 'N/A')} ({ssl.get('days_remaining', 0)} days)", styles["Body2"]))
        elements.append(Paragraph(f"  Protocol: {ssl.get('protocol', 'N/A')} | Cipher: {ssl.get('cipher', 'N/A')}", styles["Body2"]))
    else:
        elements.append(Paragraph("✗ SSL certificate is invalid or not present", styles["Issue"]))
    for issue in ssl.get("issues", []):
        elements.append(Paragraph(f"⚠ {issue}", styles["Issue"]))
    elements.append(Spacer(1, 5 * mm))

    # Headers section
    headers = report_data["headers"]
    elements.append(Paragraph("2. Security Headers", styles["Section"]))
    for h, val in headers.get("headers_present", {}).items():
        elements.append(Paragraph(f"✓ {h}: {val[:80]}", styles["Good"]))
    for h in headers.get("headers_missing", []):
        elements.append(Paragraph(f"✗ Missing: {h}", styles["Issue"]))
    elements.append(Spacer(1, 5 * mm))

    # Performance section
    perf = report_data["performance"]
    elements.append(Paragraph("3. Performance", styles["Section"]))
    if "error" not in perf:
        elements.append(Paragraph(f"  TTFB: {perf.get('ttfb_ms', 0)}ms", styles["Body2"]))
        elements.append(Paragraph(f"  Page Size: {perf.get('page_size_kb', 0)} KB", styles["Body2"]))
        elements.append(Paragraph(f"  Redirects: {perf.get('redirects', 0)}", styles["Body2"]))
        elements.append(Paragraph(f"  Compression: {perf.get('compression', 'none')}", styles["Body2"]))
    for issue in perf.get("issues", []):
        elements.append(Paragraph(f"⚠ {issue}", styles["Issue"]))
    elements.append(Spacer(1, 5 * mm))

    # Tech Stack section
    tech = report_data["techstack"]
    elements.append(Paragraph("4. Tech Stack Detected", styles["Section"]))
    detected = tech.get("detected", [])
    if detected:
        elements.append(Paragraph(", ".join(detected), styles["Body2"]))
    else:
        elements.append(Paragraph("No technologies detected (site may use custom stack)", styles["Body2"]))
    elements.append(Spacer(1, 5 * mm))

    # DNS section
    dns_data = report_data["dns"]
    elements.append(Paragraph("5. DNS Health", styles["Section"]))
    if dns_data.get("a_records"):
        elements.append(Paragraph(f"✓ A Records: {', '.join(dns_data['a_records'][:3])}", styles["Good"]))
    if dns_data.get("aaaa_records"):
        elements.append(Paragraph(f"✓ IPv6 (AAAA): {', '.join(dns_data['aaaa_records'][:2])}", styles["Good"]))
    if dns_data.get("mx_records"):
        elements.append(Paragraph(f"✓ MX: {', '.join(dns_data['mx_records'][:3])}", styles["Good"]))
    if dns_data.get("has_spf"):
        elements.append(Paragraph("✓ SPF record present", styles["Good"]))
    if dns_data.get("has_dmarc"):
        elements.append(Paragraph("✓ DMARC record present", styles["Good"]))
    for issue in dns_data.get("issues", []):
        elements.append(Paragraph(f"⚠ {issue}", styles["Issue"]))
    elements.append(Spacer(1, 5 * mm))

    # Mobile section
    mobile = report_data["mobile"]
    elements.append(Paragraph("6. Mobile Readiness", styles["Section"]))
    if mobile.get("has_viewport"):
        elements.append(Paragraph("✓ Viewport meta tag present", styles["Good"]))
    if mobile.get("has_responsive_meta"):
        elements.append(Paragraph("✓ Responsive viewport (width=device-width)", styles["Good"]))
    if mobile.get("has_touch_icon"):
        elements.append(Paragraph("✓ Apple touch icon found", styles["Good"]))
    if mobile.get("has_media_queries"):
        elements.append(Paragraph("✓ Media queries detected", styles["Good"]))
    for issue in mobile.get("issues", []):
        elements.append(Paragraph(f"⚠ {issue}", styles["Issue"]))

    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", color=HexColor("#E5E7EB")))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph("Generated by SiteGrade — sitegrade.tinyship.ai", styles["Body2"]))

    doc.build(elements)
    buf.seek(0)
    return buf.read()
