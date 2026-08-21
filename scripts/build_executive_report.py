# ruff: noqa: E501
"""Build the English executive PDF report from deterministic analytical outputs."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "report" / "Aurelia_Bank_SME_Relationship_Sales_Executive_Report.pdf"
FIGURES = ROOT / "artifacts" / "figures"

NAVY = colors.HexColor("#081F33")
NAVY_2 = colors.HexColor("#123B56")
TEAL = colors.HexColor("#0B7285")
CYAN = colors.HexColor("#30B8C5")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#5B677A")
PALE = colors.HexColor("#F4F7FA")
SOFT = colors.HexColor("#E7EEF3")
GREEN = colors.HexColor("#15803D")
GREEN_SOFT = colors.HexColor("#E8F5EC")
RED = colors.HexColor("#C2413B")
RED_SOFT = colors.HexColor("#FDECEC")
AMBER = colors.HexColor("#D97706")
RULE = colors.HexColor("#CBD5E1")
WHITE = colors.white
PAGE_W, PAGE_H = A4


def draw_wrapped(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font: str = "Helvetica",
    size: float = 10,
    color: colors.Color = INK,
    leading: float | None = None,
    max_lines: int | None = None,
) -> float:
    """Draw width-aware wrapped text and return the next y coordinate."""
    leading = leading or size * 1.35
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if not current or pdfmetrics.stringWidth(candidate, font, size) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if max_lines:
        lines = lines[:max_lines]
    pdf.setFont(font, size)
    pdf.setFillColor(color)
    for line in lines:
        pdf.drawString(x, y, line)
        y -= leading
    return y


def header(pdf: canvas.Canvas, page_number: int, title: str, source: str) -> None:
    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(42, PAGE_H - 31, "AURELIA BANK | SME RELATIONSHIP & SALES")
    pdf.drawRightString(PAGE_W - 42, PAGE_H - 31, f"{page_number:02d}")
    pdf.setStrokeColor(RULE)
    pdf.line(42, PAGE_H - 40, PAGE_W - 42, PAGE_H - 40)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(42, PAGE_H - 76, title)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 7)
    pdf.drawString(42, 24, source[:105])
    pdf.drawRightString(PAGE_W - 42, 24, "20 AUG 2026")


def section_title(pdf: canvas.Canvas, title: str, y: float) -> float:
    pdf.setFillColor(NAVY_2)
    pdf.roundRect(42, y - 22, PAGE_W - 84, 24, 2, fill=1, stroke=0)
    pdf.setFillColor(WHITE)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(52, y - 15, title.upper())
    return y - 34


def stat_card(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    value: str,
    label: str,
    detail: str,
    tone: str = "neutral",
) -> None:
    fill = {"red": RED_SOFT, "green": GREEN_SOFT}.get(tone, PALE)
    value_color = {"red": RED, "green": GREEN}.get(tone, NAVY)
    pdf.setFillColor(fill)
    pdf.roundRect(x, y, width, 88, 3, fill=1, stroke=0)
    pdf.setFillColor(value_color)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(x + 12, y + 57, value)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(x + 12, y + 39, label)
    draw_wrapped(pdf, detail, x + 12, y + 24, width - 24, size=6.8, color=MUTED, leading=8)


def draw_bullets(
    pdf: canvas.Canvas,
    items: list[str],
    x: float,
    y: float,
    width: float,
    size: float = 9,
    gap: float = 7,
) -> float:
    for item in items:
        pdf.setFillColor(TEAL)
        pdf.circle(x + 3, y + 2, 2.2, fill=1, stroke=0)
        y = draw_wrapped(pdf, item, x + 13, y + 5, width - 13, size=size, leading=size * 1.35)
        y -= gap
    return y


def draw_image(
    pdf: canvas.Canvas, path: Path, x: float, y: float, width: float, height: float
) -> None:
    image = ImageReader(path)
    source_w, source_h = image.getSize()
    scale = min(width / source_w, height / source_h)
    draw_w, draw_h = source_w * scale, source_h * scale
    pdf.drawImage(
        image, x + (width - draw_w) / 2, y + (height - draw_h) / 2, draw_w, draw_h, mask="auto"
    )


def draw_table(
    pdf: canvas.Canvas,
    rows: list[list[str]],
    x: float,
    y: float,
    widths: list[float],
    row_height: float = 24,
    header_fill: colors.Color = TEAL,
) -> float:
    for row_index, row in enumerate(rows):
        fill = header_fill if row_index == 0 else (PALE if row_index % 2 else WHITE)
        text_color = WHITE if row_index == 0 else INK
        font = "Helvetica-Bold" if row_index == 0 else "Helvetica"
        cursor = x
        pdf.setFillColor(fill)
        pdf.rect(x, y - row_height, sum(widths), row_height, fill=1, stroke=0)
        for col_index, cell in enumerate(row):
            pdf.setStrokeColor(RULE)
            pdf.rect(cursor, y - row_height, widths[col_index], row_height, fill=0, stroke=1)
            draw_wrapped(
                pdf,
                str(cell),
                cursor + 5,
                y - 10,
                widths[col_index] - 10,
                font=font,
                size=6.7,
                color=text_color,
                leading=8,
                max_lines=2,
            )
            cursor += widths[col_index]
        y -= row_height
    return y


def new_page(pdf: canvas.Canvas) -> None:
    pdf.showPage()


def build_report() -> Path:
    summary = json.loads((ROOT / "artifacts" / "results" / "executive_summary.json").read_text())
    funnel = pd.read_csv(ROOT / "artifacts" / "results" / "sales_funnel.csv")
    controls = pd.read_csv(ROOT / "artifacts" / "results" / "management_controls.csv")
    uplift = pd.read_csv(ROOT / "artifacts" / "results" / "uplift_deciles.csv")
    model = pd.read_csv(ROOT / "artifacts" / "results" / "model_performance.csv")
    queue = pd.read_csv(ROOT / "artifacts" / "results" / "next_best_conversations.csv")
    rms = pd.read_csv(ROOT / "artifacts" / "results" / "rm_performance.csv")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(OUTPUT), pagesize=A4, pageCompression=1)
    pdf.setTitle("Aurelia Bank SME Relationship & Sales Intelligence Control Tower")
    pdf.setAuthor("Murat Miraç Gedik")
    pdf.setSubject("Governed SME relationship-sales decision-support platform")
    pdf.setKeywords("SME banking, relationship management, uplift, profitability, customer 360")

    # 1 — cover.
    pdf.setFillColor(NAVY)
    pdf.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    pdf.setFillColor(CYAN)
    pdf.rect(42, PAGE_H - 164, 9, 84, fill=1, stroke=0)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(68, PAGE_H - 92, "EXECUTIVE DECISION REPORT")
    pdf.setFillColor(WHITE)
    pdf.setFont("Helvetica-Bold", 34)
    pdf.drawString(42, PAGE_H - 232, "SME Relationship & Sales")
    pdf.drawString(42, PAGE_H - 274, "Intelligence Control Tower")
    draw_wrapped(
        pdf,
        "Customer 360, activation propensity, incremental contact uplift, risk-adjusted economics and human-led next-best conversations.",
        42,
        PAGE_H - 326,
        470,
        size=15,
        color=colors.HexColor("#D9E7EF"),
        leading=20,
    )
    stat_card(
        pdf,
        42,
        228,
        154,
        f"{summary['synthetic_customers']:,}",
        "Synthetic SMEs",
        "Controlled demonstration population",
        "green",
    )
    stat_card(
        pdf,
        221,
        228,
        154,
        f"{summary['prioritised_conversations']:,}",
        "Conversations",
        "Policy and capacity qualified",
        "green",
    )
    stat_card(
        pdf,
        400,
        228,
        154,
        f"TRY {summary['expected_incremental_profit_try'] / 1e6:.1f}m",
        "Expected value",
        "Incremental, first-year and risk adjusted",
        "green",
    )
    pdf.setFillColor(WHITE)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(42, 126, "Murat Miraç Gedik | Portfolio demonstration")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        42,
        104,
        "Synthetic cutoff: 20 August 2026 | Report generated from canonical repository outputs",
    )
    pdf.setFillColor(CYAN)
    pdf.roundRect(42, 54, 332, 30, 3, fill=1, stroke=0)
    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawCentredString(208, 64, "HUMAN-LED DECISION SUPPORT — NO AUTOMATED SALE")
    new_page(pdf)

    # 2 — executive decision.
    header(
        pdf,
        2,
        "Executive decision",
        "Source: verified deterministic analytical snapshot and internal demonstration parameters",
    )
    y = PAGE_H - 108
    y = draw_wrapped(
        pdf,
        "Launch the governed conversation queue and KYC remediation as one programme.",
        42,
        y,
        511,
        font="Helvetica-Bold",
        size=17,
        color=NAVY,
        leading=22,
    )
    y -= 16
    stat_card(
        pdf,
        42,
        y - 100,
        154,
        "661",
        "Prioritised conversations",
        "Every item passed permission, product, risk, profitability and capacity gates",
        "green",
    )
    stat_card(
        pdf,
        221,
        y - 100,
        154,
        "42.2%",
        "Mean activation probability",
        "Transparent logistic-regression champion",
        "green",
    )
    stat_card(
        pdf,
        400,
        y - 100,
        154,
        "38.1%",
        "KYC overdue rate",
        "Above the 30% internal management ceiling",
        "red",
    )
    y -= 130
    y = section_title(pdf, "Decision required", y)
    pdf.setFillColor(NAVY)
    pdf.roundRect(42, y - 104, 511, 104, 4, fill=1, stroke=0)
    draw_wrapped(
        pdf,
        "Approve a controlled RM launch; clear overdue KYC by risk, service urgency and customer permission before affected needs become proposals.",
        58,
        y - 28,
        479,
        font="Helvetica-Bold",
        size=13,
        color=WHITE,
        leading=18,
    )
    y -= 130
    y = section_title(pdf, "Management interpretation", y)
    draw_bullets(
        pdf,
        [
            "Commercial value is material: TRY 16.7m expected incremental first-year profit across the selected queue.",
            "The transparent model clears discrimination, calibration and lift floors; the challenger remains available for monitoring.",
            "RM capacity is not binding: average utilisation is 24.3%, maximum utilisation is 60.7%, and the waitlist is zero.",
            "The sole breach is KYC freshness. It changes execution and requires an accountable remediation path.",
        ],
        50,
        y - 2,
        495,
        size=9.4,
    )
    new_page(pdf)

    # 3 — operating model.
    header(
        pdf,
        3,
        "Governed operating model",
        "Source: docs/architecture.md, docs/methodology.md and API/SQL contracts",
    )
    y = PAGE_H - 112
    y = draw_wrapped(
        pdf,
        "Six lenses converge on one accountable human conversation.",
        42,
        y,
        511,
        font="Helvetica-Bold",
        size=16,
        color=NAVY,
        leading=21,
    )
    y -= 18
    stages = [
        ("01", "Customer 360", "Relationship depth, holdings, interactions and observable flows"),
        ("02", "Need", "Product-specific behavioural evidence"),
        ("03", "Propensity", "Probability of activation"),
        ("04", "Uplift", "Incremental response to RM contact"),
        ("05", "Economics", "FTP, expected loss, capital and servicing"),
        ("06", "Policy", "Permission, KYC, AML, credit and capacity"),
    ]
    card_w, card_h = 160, 105
    for index, (number, label, body) in enumerate(stages):
        col, row = index % 3, index // 3
        x = 42 + col * (card_w + 15)
        cy = y - row * (card_h + 16) - card_h
        pdf.setFillColor(PALE if label != "Policy" else colors.HexColor("#E7F4F6"))
        pdf.roundRect(x, cy, card_w, card_h, 4, fill=1, stroke=0)
        pdf.setFillColor(TEAL)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawString(x + 10, cy + 84, number)
        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(x + 10, cy + 63, label)
        draw_wrapped(pdf, body, x + 10, cy + 45, card_w - 20, size=8, color=INK, leading=10)
    y -= 262
    y = section_title(pdf, "Technical decision flow", y)
    flow = [
        "Source layer",
        "Customer 360",
        "Models + economics",
        "Policy + capacity",
        "API / SQL / BI",
    ]
    for index, label in enumerate(flow):
        x = 42 + index * 102
        pdf.setFillColor(NAVY_2 if index in {2, 3} else SOFT)
        pdf.roundRect(x, y - 56, 88, 56, 3, fill=1, stroke=0)
        draw_wrapped(
            pdf,
            label,
            x + 7,
            y - 18,
            74,
            font="Helvetica-Bold",
            size=7.8,
            color=WHITE if index in {2, 3} else NAVY,
            leading=10,
            max_lines=3,
        )
        if index < len(flow) - 1:
            pdf.setFillColor(TEAL)
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(x + 91, y - 35, "›")
    y -= 86
    pdf.setFillColor(NAVY)
    pdf.roundRect(42, y - 70, 511, 70, 4, fill=1, stroke=0)
    draw_wrapped(
        pdf,
        "Cross-cutting controls: lineage | temporal validation | conduct monitoring | human ownership | reproducible result digest",
        58,
        y - 25,
        479,
        font="Helvetica-Bold",
        size=9,
        color=WHITE,
        leading=13,
    )
    new_page(pdf)

    # 4 — snapshot.
    header(
        pdf,
        4,
        "Portfolio and opportunity snapshot",
        "Source: controlled synthetic customer register and canonical opportunity queue",
    )
    draw_image(pdf, FIGURES / "executive-overview.png", 42, 420, 511, 305)
    y = 390
    y = section_title(pdf, "Portfolio structure", y)
    draw_bullets(
        pdf,
        [
            "3,200 synthetic SMEs are distributed across Micro, Small and Medium size bands and six operational regions.",
            "The book contains 7,044 product holdings—2.20 products per customer on average—plus 18 months of flows and interactions.",
            "Customer 360 retains KYC, AML, credit, permission and freshness indicators alongside behavioural features.",
            "The platform evaluates 18,556 product gaps, qualifies 1,254 through policy thresholds and allocates 661 conversations.",
        ],
        50,
        y,
        495,
        size=9,
    )
    y -= 8
    pdf.setFillColor(GREEN_SOFT)
    pdf.roundRect(42, 68, 511, 58, 4, fill=1, stroke=0)
    draw_wrapped(
        pdf,
        "Evidence boundary | Relationship depth and wallet share are transparent proxies. They support inquiry and do not establish customer need or suitability.",
        56,
        104,
        483,
        font="Helvetica-Bold",
        size=8.6,
        color=GREEN,
        leading=12,
    )
    new_page(pdf)

    # 5 — model validation.
    header(
        pdf,
        5,
        "Model validation and explainability",
        "Source: out-of-time validation window, 2 May–5 August 2026; controlled synthetic labels",
    )
    draw_image(pdf, FIGURES / "model-validation.png", 42, 412, 511, 310)
    y = 382
    y = section_title(pdf, "Champion / challenger evidence", y)
    champion = model.loc[model["selected_champion"]].iloc[0]
    challenger = model.loc[~model["selected_champion"]].iloc[0]
    rows = [
        ["Model", "ROC AUC", "PR AUC", "Brier", "Top-decile lift"],
        [
            "Logistic champion",
            f"{champion.roc_auc:.3f}",
            f"{champion.pr_auc:.3f}",
            f"{champion.brier_score:.3f}",
            f"{champion.top_decile_lift:.2f}x",
        ],
        [
            "Histogram GB challenger",
            f"{challenger.roc_auc:.3f}",
            f"{challenger.pr_auc:.3f}",
            f"{challenger.brier_score:.3f}",
            f"{challenger.top_decile_lift:.2f}x",
        ],
    ]
    y = draw_table(pdf, rows, 42, y, [155, 78, 78, 78, 122], row_height=27)
    y -= 18
    draw_bullets(
        pdf,
        [
            "The transparent champion narrowly wins on discrimination, precision-recall and calibration.",
            "Thirty-seven encoded coefficients and three customer-level reason codes remain available for challenge.",
            "Synthetic labels validate implementation and ranking logic—not production effectiveness, suitability or fairness.",
        ],
        50,
        y,
        495,
        size=8.8,
    )
    new_page(pdf)

    # 6 — uplift and economics.
    header(
        pdf,
        6,
        "Incrementality and risk-adjusted economics",
        "Source: uplift deciles and first-year illustrative product economics",
    )
    draw_image(pdf, FIGURES / "risk-adjusted-profitability.png", 42, 418, 511, 302)
    y = 389
    y = section_title(pdf, "Why propensity alone is insufficient", y)
    draw_bullets(
        pdf,
        [
            f"Mean selected activation probability is {summary['weighted_activation_probability']:.1%}; mean estimated contact uplift is {queue.predicted_contact_uplift.mean():.1%}.",
            f"Top-decile predicted uplift is {uplift.iloc[0].mean_predicted_uplift:.1%}; lower-ranked deciles create an explicit holdout challenge.",
            "Each activated product bridge deducts FTP-style funding, PD×LGD×EAD expected loss, capital charge and servicing cost.",
            f"The selected queue retains TRY {queue.risk_adjusted_profit_if_activated_try.sum() / 1e6:.1f}m if activated and TRY {summary['expected_incremental_profit_try'] / 1e6:.1f}m after probability and incrementality weighting.",
        ],
        50,
        y,
        495,
        size=8.8,
    )
    pdf.setFillColor(NAVY)
    pdf.roundRect(42, 63, 511, 58, 4, fill=1, stroke=0)
    draw_wrapped(
        pdf,
        "Finance boundary | Expected incremental profit is a prioritisation metric—not booked P&L. Realised contribution must be reconciled against governed assumptions.",
        56,
        99,
        483,
        font="Helvetica-Bold",
        size=8.3,
        color=WHITE,
        leading=11,
    )
    new_page(pdf)

    # 7 — execution.
    header(
        pdf,
        7,
        "Product mix, RM capacity and expected funnel",
        "Source: governed worklist, product economics and capacity allocation",
    )
    draw_image(pdf, FIGURES / "product-opportunities.png", 42, 514, 511, 215)
    draw_image(pdf, FIGURES / "rm-capacity.png", 42, 303, 511, 190)
    draw_image(pdf, FIGURES / "sales-funnel.png", 42, 80, 260, 205)
    y = 270
    pdf.setFillColor(PALE)
    pdf.roundRect(320, 80, 233, 205, 4, fill=1, stroke=0)
    pdf.setFillColor(TEAL)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(336, 261, "EXECUTION INTERPRETATION")
    draw_bullets(
        pdf,
        [
            "Cash Management produces 65.9% of expected profit and 343 conversations.",
            f"Average RM capacity utilisation is {rms.capacity_utilisation.mean():.1%}; maximum is {rms.capacity_utilisation.max():.1%}.",
            f"The expected funnel moves from {int(funnel.iloc[0].expected_count)} conversations to {int(funnel.iloc[-1].expected_count)} activations.",
            "Capacity is a hard control—not a pressure target.",
        ],
        336,
        238,
        201,
        size=7.6,
        gap=4,
    )
    new_page(pdf)

    # 8 — controls.
    header(
        pdf,
        8,
        "Controls, conduct and human oversight",
        "Source: 14 data-quality controls, 10 management controls and segment monitoring",
    )
    draw_image(pdf, FIGURES / "conduct-controls.png", 42, 430, 511, 292)
    y = 400
    y = section_title(pdf, "Control conclusions", y)
    rows = [["Control", "Actual", "Threshold", "Status", "Owner"]]
    for control_id in ["CTL01", "CTL02", "CTL04", "CTL05", "CTL07", "CTL10"]:
        row = controls.loc[controls.control_id == control_id].iloc[0]
        if control_id == "CTL02":
            actual, threshold = f"{row.actual_value:.2f}x", f"{row.threshold:.2f}x"
        elif control_id in {"CTL01", "CTL04", "CTL05"}:
            actual, threshold = f"{row.actual_value:.1%}", f"{row.threshold:.1%}"
        else:
            actual, threshold = f"{row.actual_value:.0f}", f"{row.threshold:.0f}"
        rows.append([row.control_name, actual, threshold, row.status, row.owner])
    y = draw_table(pdf, rows, 42, y, [218, 68, 68, 63, 94], row_height=29)
    y -= 15
    pdf.setFillColor(RED_SOFT)
    pdf.roundRect(42, y - 72, 511, 72, 4, fill=1, stroke=0)
    draw_wrapped(
        pdf,
        "Required action | KYC Operations owns the 38.1% overdue-rate breach. Sales cannot treat this dashboard as authority to bypass KYC, AML, privacy, credit or suitability controls.",
        56,
        y - 24,
        483,
        font="Helvetica-Bold",
        size=8.5,
        color=RED,
        leading=12,
    )
    new_page(pdf)

    # 9 — roadmap.
    header(
        pdf,
        9,
        "Ninety-day controlled pilot",
        "Decision requested: approve sequence, owners, holdout and monthly governance review",
    )
    y = PAGE_H - 122
    y = draw_wrapped(
        pdf,
        "Prove incremental customer value before scaling.",
        42,
        y,
        511,
        font="Helvetica-Bold",
        size=17,
        color=NAVY,
        leading=22,
    )
    y -= 38
    periods = [
        (
            "0–30 days",
            "Prepare and remediate",
            [
                "Risk-rank KYC backlog",
                "Brief authorised RMs",
                "Freeze assumptions and queue",
                "Confirm owners and evidence",
            ],
        ),
        (
            "31–60 days",
            "Run holdout pilot",
            [
                "Launch the 661-conversation queue",
                "Preserve treatment/control logic",
                "Capture need, non-sale and outcome",
                "Monitor SLA and conduct gaps",
            ],
        ),
        (
            "61–90 days",
            "Validate and scale",
            [
                "Reconcile realised economics",
                "Challenge uplift and drift",
                "Approve model or policy changes",
                "Decide controlled next wave",
            ],
        ),
    ]
    for index, (period, heading, items) in enumerate(periods):
        x = 42 + index * 175
        pdf.setFillColor(TEAL if index else RED)
        pdf.circle(x + 76, y, 7, fill=1, stroke=0)
        pdf.setStrokeColor(RULE)
        if index < 2:
            pdf.line(x + 83, y, x + 168, y)
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica-Bold", 8)
        pdf.drawCentredString(x + 76, y + 34, period.upper())
        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(x + 76, y - 35, heading)
        draw_bullets(pdf, items, x + 7, y - 72, 145, size=7.8, gap=3)
    pdf.setFillColor(NAVY)
    pdf.roundRect(42, 128, 511, 86, 4, fill=1, stroke=0)
    draw_wrapped(
        pdf,
        "Decision | Approve the pilot, name Sales–KYC–Risk–Finance owners, and review uplift, conduct, KYC freshness and realised profit monthly.",
        58,
        182,
        479,
        font="Helvetica-Bold",
        size=11.5,
        color=WHITE,
        leading=16,
    )
    pdf.setFillColor(PALE)
    pdf.roundRect(42, 63, 511, 45, 4, fill=1, stroke=0)
    draw_wrapped(
        pdf,
        "Scale condition | No unresolved KYC/control breach attributable to the pilot; holdout and Finance evidence remains decision-useful.",
        56,
        91,
        483,
        font="Helvetica-Bold",
        size=8.3,
        color=INK,
        leading=11,
    )
    new_page(pdf)

    # 10 — appendix.
    header(
        pdf,
        10,
        "Technical appendix, sources and boundary",
        "Source: repository README, data provenance, model card and artifact manifest",
    )
    y = PAGE_H - 112
    y = section_title(pdf, "Deliverable map", y)
    rows = [
        ["Layer", "Primary deliverables", "Purpose"],
        [
            "Decision engine",
            "src/aurelia_sme_sales",
            "Features, propensity, uplift, economics, policy and controls",
        ],
        [
            "Consumption",
            "FastAPI | SQL | Power BI",
            "Read-only endpoints, governed analytical views and executive measures",
        ],
        [
            "Executive",
            "Excel | PPTX | PDF",
            "Formula workbench, decision deck and management report",
        ],
        [
            "Assurance",
            "Pytest | Ruff | CI | manifest",
            "Branch coverage, linting, artifact verification and SHA-256 evidence",
        ],
    ]
    y = draw_table(pdf, rows, 42, y, [106, 170, 235], row_height=34)
    y -= 18
    y = section_title(pdf, "Read-only API contract", y)
    endpoints = [
        "GET /health",
        "GET /api/v1/portfolio/summary",
        "GET /api/v1/customers/{id}/next-conversation",
        "GET /api/v1/rms/{id}/worklist",
        "GET /api/v1/products/{code}/opportunities",
        "GET /api/v1/controls",
    ]
    for index, endpoint in enumerate(endpoints):
        col, row = index % 2, index // 2
        x = 42 + col * 257
        py = y - row * 38
        pdf.setFillColor(PALE)
        pdf.roundRect(x, py - 26, 239, 28, 3, fill=1, stroke=0)
        pdf.setFillColor(NAVY)
        pdf.setFont("Courier-Bold", 6.8)
        pdf.drawString(x + 8, py - 16, endpoint)
    y -= 132
    y = section_title(pdf, "Official context and reproducibility", y)
    draw_bullets(
        pdf,
        [
            "BDDK monthly sector data: https://www.bddk.org.tr/BultenAylik/",
            "TCMB EVDS documentation: https://evds2.tcmb.gov.tr/index.php?/evds/userDocs=",
            "EBA product-governance guidance: https://www.eba.europa.eu/activities/single-rulebook/regulatory-activities/consumer-protection/",
            "Basel credit-risk principles: https://www.bis.org/bcbs/publ/d595.pdf",
            f"Canonical analytical result SHA-256: {summary['canonical_result_sha256']}",
        ],
        50,
        y,
        495,
        size=7.7,
        gap=4,
    )
    pdf.setFillColor(RED_SOFT)
    pdf.roundRect(42, 55, 511, 64, 4, fill=1, stroke=0)
    draw_wrapped(
        pdf,
        "Boundary | Aurelia Bank is fictional. All bank records are synthetic. The report is not legal, regulatory, suitability, credit or production advice and cannot authorise a customer action.",
        56,
        94,
        483,
        font="Helvetica-Bold",
        size=8.3,
        color=RED,
        leading=11,
    )

    pdf.save()
    return OUTPUT


if __name__ == "__main__":
    result = build_report()
    print(f"SAVED {result}")
