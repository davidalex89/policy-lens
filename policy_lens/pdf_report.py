"""Generate a styled PDF report from analysis results."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF

# Brand colours
NAVY = (23, 37, 63)
STEEL = (70, 90, 120)
WHITE = (255, 255, 255)
LIGHT_GRAY = (240, 242, 245)
GREEN = (34, 139, 34)
YELLOW = (200, 150, 0)
RED = (180, 40, 40)

SCORE_COLORS = {
    "addressed": GREEN,
    "partial": YELLOW,
    "none": RED,
}

SCORE_LABELS = {
    "addressed": "Addressed",
    "partial": "Partial",
    "none": "Not Covered",
}


class PolicyReport(FPDF):
    """Custom FPDF subclass with header/footer branding."""

    def __init__(self, framework: str, model: str) -> None:
        super().__init__()
        self.framework = framework
        self.model = model
        self.set_auto_page_break(auto=True, margin=25)

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*STEEL)
        self.cell(0, 8, "policy-lens  |  Security Policy Assessment", align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*STEEL)
        self.cell(
            0, 10,
            f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
            f"Model: {self.model}  |  Framework: {self.framework}",
            align="C",
        )


def generate_pdf(
    result: dict[str, Any],
    output_path: str | Path,
    framework: str = "NIST SP 800-53 Rev. 5",
    model: str = "llama3",
) -> Path:
    """Build a PDF report and write it to output_path."""
    output_path = Path(output_path)
    evaluation = result.get("evaluation", {})
    mappings = result.get("mappings", {})
    statements = result.get("statements", {})

    pdf = PolicyReport(framework=framework, model=model)
    pdf.set_title("Security Policy Assessment — policy-lens")
    pdf.set_author("policy-lens")

    # ── Title page ───────────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(50)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 14, "Security Policy Assessment", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*STEEL)
    pdf.cell(0, 10, f"Framework: {framework}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, f"Model: {model}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 10,
        f"Generated: {datetime.now().strftime('%B %d, %Y')}",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )

    pdf.ln(20)
    pct = evaluation.get("overall_coverage_pct", "?")
    pdf.set_font("Helvetica", "B", 48)
    pdf.set_text_color(*_pct_color(pct))
    pdf.cell(0, 20, f"{pct}%", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(*STEEL)
    pdf.cell(0, 10, "Overall Coverage", align="C", new_x="LMARGIN", new_y="NEXT")

    # ── Executive summary page ───────────────────────────────────────────
    pdf.add_page()
    _section_heading(pdf, "Executive Summary")

    summary = evaluation.get("executive_summary", "No summary available.")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(0, 6, _sanitize(summary))
    pdf.ln(6)

    addressed = evaluation.get("families_addressed", 0)
    partial = evaluation.get("families_partial", 0)
    none_count = evaluation.get("families_none", 0)
    total = evaluation.get("total_families", 20)

    _kv_line(pdf, "Total Control Families", str(total))
    _kv_line(pdf, "Addressed", str(addressed), GREEN)
    _kv_line(pdf, "Partial", str(partial), YELLOW)
    _kv_line(pdf, "Not Covered", str(none_count), RED)
    pdf.ln(8)

    # ── Coverage table ───────────────────────────────────────────────────
    _section_heading(pdf, "Coverage by Control Family")
    _coverage_table(pdf, evaluation.get("family_scores", []))

    # ── Detailed findings ────────────────────────────────────────────────
    pdf.add_page()
    _section_heading(pdf, "Detailed Findings")

    mapping_list = mappings.get("mappings", [])
    mapping_by_family: dict[str, list[dict]] = {}
    for m in mapping_list:
        for fam in m.get("mapped_families", []):
            fid = fam["family_id"]
            mapping_by_family.setdefault(fid, []).append({
                "statement_id": m["statement_id"],
                "statement_text": m["statement_text"],
                "rationale": fam.get("rationale", ""),
            })

    for fs in evaluation.get("family_scores", []):
        fid = fs["family_id"]
        fname = fs["family_name"]
        score = fs["score"]
        rec = fs.get("recommendation")

        if pdf.get_y() > 240:
            pdf.add_page()

        # Family header bar
        color = SCORE_COLORS.get(score, STEEL)
        pdf.set_fill_color(*color)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 11)
        label = SCORE_LABELS.get(score, score)
        pdf.cell(0, 8, _sanitize(f"  {fid} -- {fname}    [{label}]"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_text_color(*NAVY)
        mapped = mapping_by_family.get(fid, [])

        if mapped:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(0, 5, "Mapped Policy Statements:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            for entry in mapped:
                pdf.set_x(10)
                bullet = f"  *  [{entry['statement_id']}] {entry['statement_text']}"
                pdf.multi_cell(w=0, h=5, text=_sanitize(bullet))
                if entry["rationale"]:
                    pdf.set_text_color(*STEEL)
                    pdf.set_font("Helvetica", "I", 8)
                    pdf.set_x(10)
                    pdf.multi_cell(w=0, h=4, text=_sanitize(f"    {entry['rationale']}"))
                    pdf.set_text_color(*NAVY)
                    pdf.set_font("Helvetica", "", 9)
            pdf.ln(1)

        if rec:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*RED)
            pdf.cell(0, 5, "Recommendation:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*NAVY)
            pdf.multi_cell(0, 5, _sanitize(f"  {rec}"))

        pdf.ln(4)

    # ── Appendix: all extracted statements ───────────────────────────────
    pdf.add_page()
    _section_heading(pdf, "Appendix: Extracted Policy Statements")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*NAVY)

    for stmt in statements.get("statements", []):
        if pdf.get_y() > 260:
            pdf.add_page()
        section = stmt.get("section") or "General"
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 5, _sanitize(f"[{stmt['id']}]  ({section})"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, _sanitize(f"  {stmt['text']}"))
        pdf.ln(2)

    pdf.output(str(output_path))
    return output_path


# ── Helpers ──────────────────────────────────────────────────────────────────

def _section_heading(pdf: FPDF, text: str) -> None:
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*NAVY)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(6)


def _kv_line(
    pdf: FPDF,
    label: str,
    value: str,
    value_color: tuple[int, int, int] = NAVY,
) -> None:
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*STEEL)
    pdf.cell(60, 7, label + ":")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*value_color)
    pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")


def _coverage_table(pdf: FPDF, family_scores: list[dict]) -> None:
    col_widths = [15, 75, 30, 70]
    headers = ["ID", "Control Family", "Score", "Recommendation"]

    # Header row
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 7, f" {h}", fill=True)
    pdf.ln()

    # Data rows
    pdf.set_font("Helvetica", "", 9)
    for i, fs in enumerate(family_scores):
        bg = LIGHT_GRAY if i % 2 == 0 else WHITE
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*NAVY)

        row_height = 6
        score = fs["score"]
        label = SCORE_LABELS.get(score, score)
        rec = fs.get("recommendation") or "-"
        rec_short = (rec[:60] + "...") if len(rec) > 63 else rec

        pdf.cell(col_widths[0], row_height, _sanitize(f" {fs['family_id']}"), fill=True)
        pdf.cell(col_widths[1], row_height, _sanitize(f" {fs['family_name']}"), fill=True)

        pdf.set_text_color(*SCORE_COLORS.get(score, NAVY))
        pdf.cell(col_widths[2], row_height, _sanitize(f" {label}"), fill=True)

        pdf.set_text_color(*NAVY)
        pdf.cell(col_widths[3], row_height, _sanitize(f" {rec_short}"), fill=True)
        pdf.ln()

    pdf.ln(4)


def _sanitize(text: str) -> str:
    """Replace Unicode characters unsupported by built-in PDF fonts."""
    replacements = {
        "\u2014": "--",   # em dash
        "\u2013": "-",    # en dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "*",    # bullet
        "\u00a0": " ",    # non-breaking space
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _pct_color(pct: Any) -> tuple[int, int, int]:
    try:
        p = int(pct)
    except (TypeError, ValueError):
        return STEEL
    if p >= 70:
        return GREEN
    if p >= 40:
        return YELLOW
    return RED
