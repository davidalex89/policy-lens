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


# ── Comparison PDF ────────────────────────────────────────────────────────────

DELTA_LABELS = {2: "Major Gap", 1: "Gap", 0: "Parity", -1: "Stronger", -2: "Much Stronger"}
DELTA_COLORS = {2: RED, 1: YELLOW, 0: STEEL, -1: GREEN, -2: GREEN}


def generate_comparison_pdf(
    comparison_dict: dict[str, Any],
    output_path: str | Path,
    model: str = "llama3",
) -> Path:
    """Build a PDF comparison report and write it to output_path."""
    from policy_lens.comparison import SCORE_RANK

    output_path = Path(output_path)
    label_a: str = comparison_dict.get("label_a", "Policy A")
    label_b: str = comparison_dict.get("label_b", "Policy B")
    framework: str = comparison_dict.get("framework", "")
    cov_a: int = comparison_dict.get("coverage_a", 0)
    cov_b: int = comparison_dict.get("coverage_b", 0)
    delta: int = comparison_dict.get("coverage_delta", 0)
    family_comparisons: list[dict] = comparison_dict.get("family_comparisons", [])

    pdf = PolicyReport(framework=framework, model=model)
    pdf.set_title(f"Policy Comparison — {label_a} vs {label_b}")
    pdf.set_author("policy-lens")

    # ── Title page ────────────────────────────────────────────────────────
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 14, "Policy Comparison Report", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(*STEEL)
    pdf.cell(0, 9, f"Framework: {framework}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 9, f"Model: {model}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(
        0, 9,
        f"Generated: {datetime.now().strftime('%B %d, %Y')}",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )

    pdf.ln(14)

    # Side-by-side coverage numbers
    col = 90
    _title_score_block(pdf, label_a, cov_a, col, align="R")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*STEEL)
    pdf.cell(10, 20, "vs", align="C")
    _title_score_block(pdf, label_b, cov_b, col, align="L")
    pdf.ln(28)

    # Delta line
    sign = f"+{delta}" if delta > 0 else str(delta)
    delta_color = RED if delta > 0 else (GREEN if delta < 0 else STEEL)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*delta_color)
    if delta > 0:
        msg = f"{sign}pp coverage advantage for {label_a}"
    elif delta < 0:
        msg = f"{sign}pp coverage advantage for {label_b}"
    else:
        msg = "Overall coverage parity"
    pdf.cell(0, 8, _sanitize(msg), align="C", new_x="LMARGIN", new_y="NEXT")

    # ── Coverage summary stats ────────────────────────────────────────────
    pdf.add_page()
    _section_heading(pdf, "Coverage Summary")

    for label, result_key in [(label_a, "result_a"), (label_b, "result_b")]:
        ev = comparison_dict.get(result_key, {}).get("evaluation", {})
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 7, _sanitize(label), new_x="LMARGIN", new_y="NEXT")
        _kv_line(pdf, "Overall Coverage", f"{ev.get('overall_coverage_pct', '?')}%")
        _kv_line(pdf, "Addressed", str(ev.get("families_addressed", "?")), GREEN)
        _kv_line(pdf, "Partial",   str(ev.get("families_partial", "?")),   YELLOW)
        _kv_line(pdf, "Not Covered", str(ev.get("families_none", "?")),    RED)
        pdf.ln(6)

    # ── Side-by-side comparison table ─────────────────────────────────────
    _section_heading(pdf, "Control Family Comparison")
    _comparison_table(pdf, family_comparisons, label_a, label_b)

    # ── Vendor gap detail ──────────────────────────────────────────────────
    gaps = [f for f in family_comparisons if f.get("delta", 0) > 0]
    if gaps:
        pdf.add_page()
        _section_heading(pdf, f"Vendor Gaps — Where {label_b} Falls Short")
        _gap_detail_section(pdf, gaps, label_b, is_gap=True)

    # ── Vendor stronger detail ─────────────────────────────────────────────
    stronger = [f for f in family_comparisons if f.get("delta", 0) < 0]
    if stronger:
        if pdf.get_y() > 180:
            pdf.add_page()
        else:
            pdf.ln(8)
        _section_heading(pdf, f"Vendor Strengths — Where {label_b} Leads")
        _gap_detail_section(pdf, stronger, label_b, is_gap=False)

    pdf.output(str(output_path))
    return output_path


def _title_score_block(
    pdf: FPDF, label: str, pct: int, width: int, align: str
) -> None:
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(*_pct_color(pct))
    pdf.cell(width, 20, f"{pct}%", align=align)
    if align == "L":
        pdf.ln()
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*STEEL)
        pdf.cell(0, 6, _sanitize(label), new_x="LMARGIN", new_y="NEXT")


def _comparison_table(
    pdf: FPDF,
    family_comparisons: list[dict],
    label_a: str,
    label_b: str,
) -> None:
    col_widths = [14, 62, 32, 32, 20]
    la_short = label_a[:14] if len(label_a) > 14 else label_a
    lb_short = label_b[:14] if len(label_b) > 14 else label_b
    headers = ["ID", "Control Family", la_short, lb_short, "Gap"]

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 7, _sanitize(f" {h}"), fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for i, fc in enumerate(family_comparisons):
        bg = LIGHT_GRAY if i % 2 == 0 else WHITE
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*NAVY)

        score_a = fc.get("score_a", "none")
        score_b = fc.get("score_b", "none")
        delta = fc.get("delta", 0)
        clamped = max(-2, min(2, delta))
        gap_label = DELTA_LABELS.get(clamped, str(delta))
        gap_color = DELTA_COLORS.get(clamped, STEEL)

        pdf.cell(col_widths[0], 6, _sanitize(f" {fc['family_id']}"), fill=True)
        pdf.cell(col_widths[1], 6, _sanitize(f" {fc['family_name']}"), fill=True)

        pdf.set_text_color(*SCORE_COLORS.get(score_a, NAVY))
        pdf.cell(col_widths[2], 6, _sanitize(f" {SCORE_LABELS.get(score_a, score_a)}"), fill=True)

        pdf.set_text_color(*SCORE_COLORS.get(score_b, NAVY))
        pdf.cell(col_widths[3], 6, _sanitize(f" {SCORE_LABELS.get(score_b, score_b)}"), fill=True)

        pdf.set_text_color(*gap_color)
        pdf.cell(col_widths[4], 6, _sanitize(f" {gap_label}"), fill=True)
        pdf.ln()

    pdf.ln(4)


def _gap_detail_section(
    pdf: FPDF,
    families: list[dict],
    subject_label: str,
    is_gap: bool,
) -> None:
    rec_key = "recommendation_b" if is_gap else "recommendation_a"
    score_key = "score_b" if is_gap else "score_a"
    other_score_key = "score_a" if is_gap else "score_b"
    header_color = RED if is_gap else GREEN

    for fc in families:
        if pdf.get_y() > 245:
            pdf.add_page()

        score = fc.get(score_key, "none")
        other_score = fc.get(other_score_key, "none")
        color = SCORE_COLORS.get(score, STEEL)

        pdf.set_fill_color(*color)
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "B", 10)
        label = SCORE_LABELS.get(score, score)
        other_label = SCORE_LABELS.get(other_score, other_score)
        pdf.cell(
            0, 7,
            _sanitize(
                f"  {fc['family_id']} -- {fc['family_name']}"
                f"    [{subject_label}: {label} / Other: {other_label}]"
            ),
            fill=True,
            new_x="LMARGIN",
            new_y="NEXT",
        )
        pdf.ln(2)

        rec = fc.get(rec_key)
        if rec:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*header_color)
            pdf.cell(0, 5, "Recommendation:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*NAVY)
            pdf.multi_cell(0, 5, _sanitize(f"  {rec}"))

        pdf.ln(4)
