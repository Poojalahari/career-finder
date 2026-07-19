from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_report(scan):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50
    pdf.setTitle("ATS Resume Scan Report")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "ATS Resume Scan Report")
    y -= 35
    pdf.setFont("Helvetica", 11)
    lines = [
        f"Resume: {scan.original_filename}",
        f"Job title: {scan.job_title or 'General resume review'}",
        f"Overall score: {scan.overall_score}/100",
        "This advisory score is not a guarantee of acceptance.",
        "",
        "Section scores:",
    ]
    for name, value in scan.section_scores.items():
        lines.append(f"- {name}: {value}/100")
    lines.append("")
    lines.append("Recommendations:")
    lines.extend(f"- {item}" for item in scan.recommendations)
    for line in lines:
        if y < 60:
            pdf.showPage()
            y = height - 50
            pdf.setFont("Helvetica", 11)
        pdf.drawString(50, y, line[:95])
        y -= 18
    pdf.save()
    buffer.seek(0)
    return buffer
