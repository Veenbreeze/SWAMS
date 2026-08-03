"""ReportLab-based PDF export — pure Python, no system dependencies
(chosen over WeasyPrint specifically to avoid the Pango/GTK system
libraries it needs, which are painful to install on Windows dev machines).

One generic table renderer, not a function per report type: every report
in apps/reports/services/table_builder.py already reduces to a
(title, headers, rows) shape, so the export format only needs to know how
to render that shape once.
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def render_table_pdf(*, title, headers, rows):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title=title)
    styles = getSampleStyleSheet()

    table_data = [headers] + [[str(cell) for cell in row] for row in rows]
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ]
        )
    )

    doc.build([Paragraph(title, styles["Title"]), Spacer(1, 16), table])
    return buffer.getvalue()
