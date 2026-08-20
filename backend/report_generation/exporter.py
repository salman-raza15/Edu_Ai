"""
EduAI professional report exporter.

Features:
- PDF / Excel / CSV exports
- Optional custom letterhead
- Custom letterhead supports PDF, PNG, JPG and JPEG
- PDF letterhead uses only the top/header portion of page 1
- Removes large white margins around the letterhead
- Never adds the EduAI header underneath a custom letterhead
- Keeps analytics, tables and graphs
- Does not add duplicate chart titles outside the chart images
"""

import base64
import html
import io
import json
import os
from datetime import datetime

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)

from .graphs import generate_graphs


# ---------------------------------------------------------------------------
# Visual system
# ---------------------------------------------------------------------------

NAVY = HexColor("#172554")
BLUE = HexColor("#2563EB")
TEAL = HexColor("#0F766E")
LIGHT_BLUE = HexColor("#EFF6FF")
LIGHT_TEAL = HexColor("#ECFDF5")
LIGHT_PURPLE = HexColor("#F5F3FF")
LIGHT_GRAY = HexColor("#F8FAFC")
MID_GRAY = HexColor("#64748B")
BORDER = HexColor("#CBD5E1")
DARK = HexColor("#0F172A")
WHITE = colors.white


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

def _safe(value, default="—"):
    return default if value is None or value == "" else str(value)


def _footer(canvas, doc):
    canvas.saveState()
    width, _ = A4

    y = 12 * mm

    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(
        18 * mm,
        y + 5 * mm,
        width - 18 * mm,
        y + 5 * mm,
    )

    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MID_GRAY)

    canvas.drawString(
        18 * mm,
        y,
        "EduAI • Intelligent Assessment Platform",
    )

    canvas.drawRightString(
        width - 18 * mm,
        y,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Letterhead handling
# ---------------------------------------------------------------------------

def _decode_base64(value):
    """Decode a base64 string, including data URLs."""
    if not value:
        return None

    if isinstance(value, bytes):
        return value

    if not isinstance(value, str):
        return None

    if "," in value and value.lower().startswith("data:"):
        value = value.split(",", 1)[1]

    try:
        return base64.b64decode(value)
    except Exception:
        return None


def _extract_letterhead_value(report_result):
    """
    Accept several possible keys so this exporter works with the different
    report-generation UI/router versions.

    Supported values:
      letterhead_data
      custom_letterhead
      letterhead_base64
      letterhead_path
    """
    candidates = [
        report_result.get("letterhead_data"),
        report_result.get("custom_letterhead"),
        report_result.get("letterhead_base64"),
        report_result.get("letterhead_path"),
    ]

    for value in candidates:
        if value:
            return value

    return None


def _crop_white_margins(image, top_fraction=None):
    """
    Crop mostly-white margins from an image.

    If top_fraction is supplied, only that percentage from the top of the
    source page is considered. This is important for PDF letterheads:
    a letterhead PDF is often a complete A4 page with the actual header only
    occupying the top portion.
    """
    try:
        from PIL import Image as PILImage
        from PIL import ImageChops
    except ImportError:
        return image

    img = image.convert("RGB")

    if top_fraction is not None:
        crop_h = max(1, int(img.height * top_fraction))
        img = img.crop((0, 0, img.width, crop_h))

    # Treat near-white pixels as background.
    bg = PILImage.new("RGB", img.size, (255, 255, 255))
    diff = ImageChops.difference(img, bg)

    # Increase the difference slightly so very light gray borders are ignored.
    bbox = diff.point(lambda p: 255 if p > 10 else 0).getbbox()

    if not bbox:
        return img

    # Small safety padding around detected content.
    pad_x = max(4, int(img.width * 0.01))
    pad_y = max(4, int(img.height * 0.01))

    left = max(0, bbox[0] - pad_x)
    top = max(0, bbox[1] - pad_y)
    right = min(img.width, bbox[2] + pad_x)
    bottom = min(img.height, bbox[3] + pad_y)

    return img.crop((left, top, right, bottom))


def _pdf_letterhead_to_png(pdf_bytes, output_dir, filename_prefix):
    """
    Convert the first page of an uploaded PDF letterhead into a real
    letterhead HEADER.

    IMPORTANT:
    A letterhead PDF is often a complete A4 page. We must NOT scale that
    complete page into the report. We take only the upper header area,
    remove white margins, and save that header as a transparent-looking
    PNG with its real aspect ratio.

    The source report/letterhead can contain footer text or other content
    lower on the page; that content is intentionally ignored.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError(
            "PyMuPDF is required for PDF letterheads. "
            "Install it with: pip install pymupdf"
        ) from exc

    try:
        from PIL import Image as PILImage
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for PDF letterheads. "
            "Install it with: pip install pillow"
        ) from exc

    document = fitz.open(stream=pdf_bytes, filetype="pdf")

    if document.page_count == 0:
        document.close()
        raise ValueError("The uploaded letterhead PDF has no pages.")

    page = document.load_page(0)

    # Render at high resolution.
    pix = page.get_pixmap(
        matrix=fitz.Matrix(3.0, 3.0),
        alpha=False,
        colorspace=fitz.csRGB,
    )

    rendered = PILImage.open(
        io.BytesIO(pix.tobytes("png"))
    ).convert("RGB")

    # ---------------------------------------------------------------
    # FINAL PDF LETTERHEAD RULE:
    #
    # A user-uploaded "letterhead PDF" is a complete A4 page in many cases.
    # We must NEVER use that complete page as the report header.
    #
    # The supplied letterhead used in this project has its actual branding
    # header in the top part of the page. Keep only that region. Do not run
    # horizontal white-space detection here because the source can contain
    # full-width background bands/borders that make the whole A4 page look
    # non-white and defeat the crop.
    # ---------------------------------------------------------------
    header_h = max(1, int(rendered.height * 0.20))
    cropped = rendered.crop(
        (0, 0, rendered.width, header_h)
    )

    # Remove only a tiny amount of accidental blank space at the bottom of
    # the selected header region. Never crop the width.
    cropped = cropped.crop(
        (0, 0, cropped.width, max(1, int(cropped.height * 0.97)))
    )

    output_path = os.path.join(
        output_dir,
        f"{filename_prefix}_letterhead.png",
    )

    cropped.save(
        output_path,
        "PNG",
        optimize=True,
    )

    document.close()

    return output_path

def _image_letterhead_to_png(image_bytes, output_dir, filename_prefix):
    """Normalize and crop PNG/JPG/JPEG letterheads."""
    try:
        from PIL import Image as PILImage
    except ImportError as exc:
        raise RuntimeError(
            "Pillow is required for image letterheads. "
            "Install it with: pip install pillow"
        ) from exc

    image = PILImage.open(
        io.BytesIO(image_bytes)
    ).convert("RGB")

    cropped = _crop_white_margins(image)

    output_path = os.path.join(
        output_dir,
        f"{filename_prefix}_letterhead.png",
    )

    cropped.save(
        output_path,
        "PNG",
        optimize=True,
    )

    return output_path


def _prepare_custom_letterhead(
    report_result,
    output_dir,
    filename_prefix,
):
    """
    Resolve the optional custom letterhead.

    Returns:
        PNG path, or None if default EduAI letterhead should be used.
    """
    mode = str(
        report_result.get(
            "letterhead_mode",
            report_result.get("letterhead_type", ""),
        )
    ).strip().lower()

    if mode in {
        "default",
        "default eduai",
        "eduai",
    }:
        return None

    value = _extract_letterhead_value(report_result)

    if not value:
        return None

    # A dict is supported for routers that send:
    # {"filename": "...", "data": "..."}
    if isinstance(value, dict):
        filename = str(
            value.get("filename")
            or value.get("name")
            or "letterhead"
        )
        raw = (
            value.get("data")
            or value.get("content")
            or value.get("base64")
        )

        if isinstance(raw, str):
            raw = _decode_base64(raw)

        if not raw:
            return None

        value = (filename, raw)

    # Tuple/list: (filename, bytes)
    if isinstance(value, (tuple, list)) and len(value) >= 2:
        filename = str(value[0] or "letterhead")
        raw = value[1]

        if isinstance(raw, str):
            raw = _decode_base64(raw)

        if not raw:
            return None

        ext = os.path.splitext(filename)[1].lower()

        if ext == ".pdf":
            return _pdf_letterhead_to_png(
                raw,
                output_dir,
                filename_prefix,
            )

        if ext in {".png", ".jpg", ".jpeg"}:
            return _image_letterhead_to_png(
                raw,
                output_dir,
                filename_prefix,
            )

        raise ValueError(
            "Unsupported letterhead format. "
            "Use PDF, PNG, JPG or JPEG."
        )

    # Raw bytes: inspect magic bytes.
    if isinstance(value, bytes):
        raw = value

        if raw.startswith(b"%PDF"):
            return _pdf_letterhead_to_png(
                raw,
                output_dir,
                filename_prefix,
            )

        return _image_letterhead_to_png(
            raw,
            output_dir,
            filename_prefix,
        )

    # File path.
    if isinstance(value, str):
        # A real filesystem path is handled before any data-url logic.
        if os.path.isfile(value):
            ext = os.path.splitext(value)[1].lower()

            with open(value, "rb") as f:
                raw = f.read()

            if ext == ".pdf" or raw.startswith(b"%PDF"):
                return _pdf_letterhead_to_png(
                    raw,
                    output_dir,
                    filename_prefix,
                )

            if ext in {".png", ".jpg", ".jpeg"}:
                return _image_letterhead_to_png(
                    raw,
                    output_dir,
                    filename_prefix,
                )

            raise ValueError(
                "Unsupported letterhead format. "
                "Use PDF, PNG, JPG or JPEG."
            )

        if value.startswith("data:"):
            raw = _decode_base64(value)

            if raw and raw.startswith(b"%PDF"):
                return _pdf_letterhead_to_png(
                    raw,
                    output_dir,
                    filename_prefix,
                )

            if raw:
                return _image_letterhead_to_png(
                    raw,
                    output_dir,
                    filename_prefix,
                )

    return None


# ---------------------------------------------------------------------------
# Default EduAI header
# ---------------------------------------------------------------------------

def _default_header(report_result):
    scope = str(
        report_result.get("scope", "report")
    ).capitalize()

    scope_id = _safe(
        report_result.get("scope_id")
    )

    report_type = (
        str(report_result.get("report_type", "custom"))
        .replace("_", " ")
        .title()
    )

    brand_style = ParagraphStyle(
        "DefaultBrand",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=19,
        textColor=WHITE,
    )

    meta_style = ParagraphStyle(
        "DefaultHeaderMeta",
        fontName="Helvetica",
        fontSize=9.5,
        leading=12,
        textColor=WHITE,
    )

    title = Paragraph(
        "<b>EduAI</b><br/>"
        "<font size='7.5' color='#CBD5E1'>"
        "INTELLIGENT ASSESSMENT PLATFORM"
        "</font>",
        brand_style,
    )

    meta = Paragraph(
        f"<b>{html.escape(scope)} Performance Report</b><br/>"
        f"{html.escape(scope_id)} &nbsp; • &nbsp; "
        f"{html.escape(report_type)}",
        meta_style,
    )

    table = Table(
        [[title, meta]],
        colWidths=[88 * mm, 82 * mm],
        rowHeights=[24 * mm],
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 8 * mm),
        ("LEFTPADDING", (1, 0), (1, 0), 2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("BOX", (0, 0), (-1, -1), 0, NAVY),
    ]))

    return table


def _custom_header(letterhead_path):
    """
    Place the already-cropped custom letterhead at the full report width.

    IMPORTANT:
    Do not impose a maximum height. The PDF-letterhead converter has already
    cropped the source to the header region. The height is therefore derived
    only from the real image aspect ratio.
    """
    from PIL import Image as PILImage

    available_width = 174 * mm

    with PILImage.open(letterhead_path) as src:
        src_width, src_height = src.size

    if src_width <= 0 or src_height <= 0:
        raise ValueError("The custom letterhead image has invalid dimensions.")

    height = available_width * (src_height / src_width)

    return Image(
        letterhead_path,
        width=available_width,
        height=height,
        kind="proportional",
    )


# ---------------------------------------------------------------------------
# Report components
# ---------------------------------------------------------------------------

def _section_title(text, styles):
    return Paragraph(
        html.escape(text).upper(),
        styles["SectionTitle"],
    )


def _metric_rows(analytics):
    return [
        ["Metric", "Value"],
        ["Total Students", analytics.get("total_students", "—")],
        ["Total Submissions", analytics.get("total_submissions", "—")],
        ["Average %", f"{analytics.get('average_percentage', '—')}%"],
        ["Highest %", f"{analytics.get('highest_percentage', '—')}%"],
        ["Lowest %", f"{analytics.get('lowest_percentage', '—')}%"],
        ["Pass Rate", f"{analytics.get('pass_rate', '—')}%"],
    ]


def _metric_cards(analytics, styles):
    metrics = [
        (
            "AVERAGE",
            f"{analytics.get('average_percentage', '—')}%",
            BLUE,
            LIGHT_BLUE,
        ),
        (
            "HIGHEST",
            f"{analytics.get('highest_percentage', '—')}%",
            TEAL,
            LIGHT_TEAL,
        ),
        (
            "LOWEST",
            f"{analytics.get('lowest_percentage', '—')}%",
            NAVY,
            LIGHT_PURPLE,
        ),
        (
            "PASS RATE",
            f"{analytics.get('pass_rate', '—')}%",
            TEAL,
            LIGHT_TEAL,
        ),
    ]

    cells = []

    for label, value, accent, bg in metrics:
        value_style = ParagraphStyle(
            f"CardValue_{label}",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=20,
            textColor=accent,
        )

        cell = Table(
            [
                [Paragraph(label, styles["CardLabel"])],
                [Paragraph(value, value_style)],
            ],
            colWidths=[39 * mm],
            rowHeights=[7 * mm, 11 * mm],
        )

        cell.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), bg),
            ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ]))

        cells.append(cell)

    outer = Table(
        [cells],
        colWidths=[43 * mm] * 4,
    )

    outer.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    return outer


def _styled_table(
    data,
    widths,
    header_bg=NAVY,
    font_size=8.5,
    align_right_cols=None,
):
    table = Table(
        data,
        colWidths=widths,
        repeatRows=1,
        hAlign="LEFT",
    )

    align_right_cols = align_right_cols or []

    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("TEXTCOLOR", (0, 1), (-1, -1), DARK),
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
    ]

    for col in align_right_cols:
        commands.append(
            ("ALIGN", (col, 1), (col, -1), "RIGHT")
        )

    table.setStyle(TableStyle(commands))

    return table


def _chart_image(path, width=165 * mm, height=72 * mm):
    """
    The graph image already contains its own title.

    Therefore we intentionally DO NOT add another Paragraph title here.
    This removes the duplicated titles seen in previous PDFs.
    """
    return [
        Image(
            path,
            width=width,
            height=height,
            kind="proportional",
        ),
        Spacer(1, 4 * mm),
    ]


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def export_pdf(
    report_result: dict,
    output_dir: str,
    filename_prefix: str,
    letterhead_path: str = None,
    letterhead_data=None,
    **kwargs,
) -> str:
    """
    Generate the professional EduAI PDF.

    Custom letterhead is optional and can be supplied through report_result.
    The existing router signature remains unchanged.
    """
    os.makedirs(output_dir, exist_ok=True)

    analytics = report_result["analytics"]

    # Generate graphs.
    graph_paths = generate_graphs(
        analytics,
        output_dir,
        prefix=filename_prefix,
    )

    # Resolve optional custom letterhead.
    #
    # IMPORTANT:
    # If the router explicitly provides letterhead_path, use that FIRST.
    # This prevents an older/stale letterhead_data value from overriding the
    # actual uploaded file and bypassing PDF header extraction.
    if letterhead_path:
        letterhead_report = dict(report_result)
        letterhead_report.pop("letterhead_data", None)
        letterhead_report.pop("custom_letterhead", None)
        letterhead_report.pop("letterhead_base64", None)
        letterhead_report["letterhead_path"] = letterhead_path

        custom_letterhead = _prepare_custom_letterhead(
            letterhead_report,
            output_dir,
            filename_prefix,
        )
    else:
        letterhead_report = dict(report_result)

        if letterhead_data:
            letterhead_report["letterhead_data"] = letterhead_data

        custom_letterhead = _prepare_custom_letterhead(
            letterhead_report,
            output_dir,
            filename_prefix,
        )

    pdf_path = os.path.join(
        output_dir,
        f"{filename_prefix}.pdf",
    )

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=12 * mm,
        bottomMargin=20 * mm,
        title=(
            f"EduAI Performance Report - "
            f"{report_result.get('scope_id', '')}"
        ),
        author="EduAI",
        subject="Academic performance analytics report",
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="SectionTitle",
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=14,
        textColor=NAVY,
        spaceBefore=3,
        spaceAfter=6,
    ))

    styles.add(ParagraphStyle(
        name="BodyProfessional",
        fontName="Helvetica",
        fontSize=9.2,
        leading=13.5,
        textColor=HexColor("#334155"),
    ))

    styles.add(ParagraphStyle(
        name="CardLabel",
        fontName="Helvetica-Bold",
        fontSize=7.2,
        leading=8.5,
        textColor=MID_GRAY,
    ))

    styles.add(ParagraphStyle(
        name="SmallMuted",
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=MID_GRAY,
    ))

    story = []

    # -----------------------------------------------------------------------
    # Header
    # -----------------------------------------------------------------------

    if custom_letterhead:
        story.append(_custom_header(custom_letterhead))
        story.append(Spacer(1, 4 * mm))
    else:
        story.append(_default_header(report_result))
        story.append(Spacer(1, 5 * mm))

    # -----------------------------------------------------------------------
    # Metadata
    # -----------------------------------------------------------------------

    date_from = report_result.get("date_from")
    date_to = report_result.get("date_to")

    generated = datetime.now().strftime(
        "%d %b %Y, %I:%M %p"
    )

    metadata = [
        [
            "REPORT TYPE",
            str(
                report_result.get(
                    "report_type",
                    "custom",
                )
            ).replace("_", " ").title(),
            "GENERATED",
            generated,
        ]
    ]

    if date_from or date_to:
        metadata.append([
            "DATE RANGE",
            f"{date_from or 'Start'} → {date_to or 'End'}",
            "SCOPE",
            _safe(report_result.get("scope_id")),
        ])
    else:
        metadata.append([
            "SCOPE",
            _safe(report_result.get("scope_id")),
            "STATUS",
            "Finalized",
        ])

    meta_table = Table(
        metadata,
        colWidths=[
            26 * mm,
            59 * mm,
            24 * mm,
            61 * mm,
        ],
    )

    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.7),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), MID_GRAY),
        ("TEXTCOLOR", (2, 0), (2, -1), MID_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
    ]))

    story.append(meta_table)
    story.append(Spacer(1, 5 * mm))

    # -----------------------------------------------------------------------
    # Executive Summary
    # -----------------------------------------------------------------------

    summary = str(
        report_result.get("narrative_text", "")
    ).strip()

    if summary:
        story.append(
            _section_title(
                "Executive Summary",
                styles,
            )
        )

        summary_box = Table(
            [[
                Paragraph(
                    html.escape(summary).replace(
                        "\n",
                        "<br/>",
                    ),
                    styles["BodyProfessional"],
                )
            ]],
            colWidths=[174 * mm],
        )

        summary_box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE),
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.6,
                HexColor("#BFDBFE"),
            ),
            ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
        ]))

        story.append(summary_box)
        story.append(Spacer(1, 5 * mm))

    # -----------------------------------------------------------------------
    # KPI cards
    # -----------------------------------------------------------------------

    story.append(
        _section_title(
            "Performance Snapshot",
            styles,
        )
    )

    story.append(
        _metric_cards(
            analytics,
            styles,
        )
    )

    story.append(Spacer(1, 5 * mm))

    # -----------------------------------------------------------------------
    # Key analytics
    # -----------------------------------------------------------------------

    story.append(
        _section_title(
            "Key Analytics",
            styles,
        )
    )

    story.append(
        _styled_table(
            _metric_rows(analytics),
            [95 * mm, 55 * mm],
            align_right_cols=[1],
        )
    )

    # -----------------------------------------------------------------------
    # Rubric
    # -----------------------------------------------------------------------

    rubric = analytics.get(
        "rubric_analysis",
        {},
    ) or {}

    if rubric:
        story.append(Spacer(1, 5 * mm))

        story.append(
            _section_title(
                "Rubric Analysis",
                styles,
            )
        )

        rubric_rows = [["Criteria", "Average %"]]

        rubric_rows.extend(
            [
                [str(k), f"{v}%"]
                for k, v in rubric.items()
            ]
        )

        story.append(
            _styled_table(
                rubric_rows,
                [115 * mm, 35 * mm],
                header_bg=TEAL,
                align_right_cols=[1],
            )
        )

    # -----------------------------------------------------------------------
    # Evaluation history
    # -----------------------------------------------------------------------

    history = analytics.get(
        "evaluation_history",
        [],
    ) or []

    if history:
        story.append(PageBreak())

        story.append(
            _section_title(
                "Evaluation History & Trend",
                styles,
            )
        )

        history_rows = [[
            "Date",
            "Submissions",
            "Average %",
            "Highest %",
            "Lowest %",
            "Pass Rate %",
        ]]

        for item in history:
            history_rows.append([
                _safe(item.get("evaluation_date")),
                _safe(item.get("submissions")),
                _safe(item.get("average_percentage")),
                _safe(item.get("highest_percentage")),
                _safe(item.get("lowest_percentage")),
                _safe(item.get("pass_rate")),
            ])

        story.append(
            _styled_table(
                history_rows,
                [
                    31 * mm,
                    26 * mm,
                    29 * mm,
                    29 * mm,
                    29 * mm,
                    30 * mm,
                ],
                font_size=7.4,
                align_right_cols=[
                    1,
                    2,
                    3,
                    4,
                    5,
                ],
            )
        )

    # -----------------------------------------------------------------------
    # Visual analytics
    # -----------------------------------------------------------------------

    chart_order = [
        "student_bar",
        "pass_fail_pie",
        "rubric_bar",
        "trend_line",
    ]

    available = [
        (key, graph_paths.get(key))
        for key in chart_order
        if graph_paths.get(key)
        and os.path.exists(graph_paths.get(key))
    ]

    if available:
        story.append(PageBreak())

        story.append(
            _section_title(
                "Visual Analytics",
                styles,
            )
        )

        for index, (key, path) in enumerate(available):
            # No external chart title here. The graph itself already has one.
            height = (
                68 * mm
                if key == "pass_fail_pie"
                else 70 * mm
            )

            story.extend(
                _chart_image(
                    path,
                    width=165 * mm,
                    height=height,
                )
            )

            if index == 1 and index < len(available) - 1:
                story.append(PageBreak())
                story.append(
                    _section_title(
                        "Visual Analytics",
                        styles,
                    )
                )

    # -----------------------------------------------------------------------
    # Final note
    # -----------------------------------------------------------------------

    story.append(Spacer(1, 3 * mm))

    story.append(
        Paragraph(
            "This report was generated by EduAI from the selected "
            "assessment and evaluation data. Percentages are presented "
            "to support academic performance review and instructional "
            "decision-making.",
            styles["SmallMuted"],
        )
    )

    doc.build(
        story,
        onFirstPage=_footer,
        onLaterPages=_footer,
    )

    return pdf_path


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

def export_excel(
    report_result: dict,
    output_dir: str,
    filename_prefix: str,
) -> str:
    os.makedirs(output_dir, exist_ok=True)

    analytics = report_result["analytics"]

    path = os.path.join(
        output_dir,
        f"{filename_prefix}.xlsx",
    )

    with pd.ExcelWriter(
        path,
        engine="openpyxl",
    ) as writer:

        pd.DataFrame([{
            "Scope": report_result.get("scope"),
            "Scope ID": report_result.get("scope_id"),
            "Report Type": report_result.get("report_type"),
            "Date From": report_result.get("date_from"),
            "Date To": report_result.get("date_to"),
            "Total Students": analytics.get("total_students"),
            "Total Submissions": analytics.get("total_submissions"),
            "Average %": analytics.get("average_percentage"),
            "Highest %": analytics.get("highest_percentage"),
            "Lowest %": analytics.get("lowest_percentage"),
            "Pass Rate %": analytics.get("pass_rate"),
        }]).to_excel(
            writer,
            sheet_name="Summary",
            index=False,
        )

        pd.DataFrame(
            analytics.get(
                "student_breakdown",
                [],
            )
        ).to_excel(
            writer,
            sheet_name="Student Breakdown",
            index=False,
        )

        pd.DataFrame([
            {
                "Criteria": key,
                "Average %": value,
            }
            for key, value in analytics.get(
                "rubric_analysis",
                {},
            ).items()
        ]).to_excel(
            writer,
            sheet_name="Rubric Analysis",
            index=False,
        )

        pd.DataFrame(
            analytics.get(
                "evaluation_history",
                [],
            )
        ).to_excel(
            writer,
            sheet_name="Evaluation History",
            index=False,
        )

        pd.DataFrame([
            {
                "Date": key,
                "Average %": value,
            }
            for key, value in analytics.get(
                "trend",
                {},
            ).items()
        ]).to_excel(
            writer,
            sheet_name="Trend",
            index=False,
        )

    return path


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------

def json_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            default=str,
        )

    return value


def export_csv(
    report_result: dict,
    output_dir: str,
    filename_prefix: str,
) -> str:
    os.makedirs(output_dir, exist_ok=True)

    analytics = report_result["analytics"]

    path = os.path.join(
        output_dir,
        f"{filename_prefix}.csv",
    )

    rows = []

    for key in (
        "scope",
        "scope_id",
        "report_type",
        "date_from",
        "date_to",
    ):
        rows.append({
            "section": "metadata",
            "field": key,
            "value": report_result.get(key),
        })

    for key in (
        "total_students",
        "total_submissions",
        "average_percentage",
        "highest_percentage",
        "lowest_percentage",
        "pass_rate",
    ):
        rows.append({
            "section": "analytics",
            "field": key,
            "value": analytics.get(key),
        })

    for criteria, value in analytics.get(
        "rubric_analysis",
        {},
    ).items():
        rows.append({
            "section": "rubric",
            "field": criteria,
            "value": value,
        })

    for item in analytics.get(
        "evaluation_history",
        [],
    ):
        rows.append({
            "section": "evaluation_history",
            "field": item.get("evaluation_date"),
            "value": json_value(item),
        })

    for item in analytics.get(
        "student_breakdown",
        [],
    ):
        rows.append({
            "section": "student_breakdown",
            "field": item.get("student_id"),
            "value": json_value(item),
        })

    pd.DataFrame(rows).to_csv(
        path,
        index=False,
    )

    return path