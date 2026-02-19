"""PDF export engine using HTML templates + WeasyPrint (or fallback to reportlab)."""

import os
from typing import Optional
from datetime import datetime

try:
    from jinja2 import Template
    HAS_JINJA = True
except ImportError:
    HAS_JINJA = False

# We'll use simple HTML string formatting as fallback
REPORT_CSS = """
body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #1e293b; margin: 40px; font-size: 11pt; line-height: 1.5; }
h1 { color: #1e3a5f; font-size: 24pt; margin-bottom: 5px; }
h2 { color: #1e3a5f; font-size: 16pt; border-bottom: 2px solid #cbd5e1; padding-bottom: 5px; margin-top: 30px; }
h3 { color: #334155; font-size: 13pt; margin-top: 20px; }
.header { border-bottom: 3px solid #1e3a5f; padding-bottom: 15px; margin-bottom: 20px; }
.header .firm { color: #64748b; font-size: 10pt; }
.summary-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; margin: 20px 0; }
.summary-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; }
.summary-box .label { color: #64748b; font-size: 9pt; text-transform: uppercase; letter-spacing: 0.5px; }
.summary-box .value { color: #1e293b; font-size: 18pt; font-weight: 600; margin-top: 5px; }
table { width: 100%; border-collapse: collapse; margin: 15px 0; }
th { background: #f1f5f9; color: #475569; text-align: left; padding: 8px 12px; font-size: 9pt; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #cbd5e1; }
td { padding: 8px 12px; border-bottom: 1px solid #e2e8f0; }
tr:nth-child(even) { background: #f8fafc; }
.money { text-align: right; font-family: 'Courier New', monospace; }
.positive { color: #16a34a; }
.negative { color: #dc2626; }
.observation { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 10px 15px; margin: 10px 0; border-radius: 0 4px 4px 0; }
.observation.opportunity { background: #dcfce7; border-color: #22c55e; }
.observation.alert { background: #fee2e2; border-color: #ef4444; }
.observation.warning { background: #fef3c7; border-color: #f59e0b; }
.footer { margin-top: 40px; padding-top: 15px; border-top: 1px solid #cbd5e1; color: #94a3b8; font-size: 8pt; text-align: center; }
@page { margin: 1cm; @bottom-center { content: "For informational purposes only. Not tax advice."; font-size: 8pt; color: #94a3b8; } @bottom-right { content: "Page " counter(page) " of " counter(pages); font-size: 8pt; color: #94a3b8; } }
.bracket-bar { height: 30px; display: flex; margin: 10px 0; border-radius: 4px; overflow: hidden; }
.bracket-segment { display: flex; align-items: center; justify-content: center; color: white; font-size: 8pt; font-weight: 600; }
"""


def _fmt_money(val):
    """Format a number as currency."""
    if val is None:
        return "$0"
    if val < 0:
        return f"-${abs(val):,.0f}"
    return f"${val:,.0f}"


def _fmt_pct(val):
    """Format a number as percentage."""
    if val is None:
        return "0.0%"
    return f"{val:.1f}%"


def generate_tax_report_pdf(report_data: dict) -> bytes:
    """Generate a Tax Report PDF from report data."""
    summary = report_data.get("summary", {})
    household = report_data.get("household", {})
    scenario = report_data.get("scenario", {})
    income_breakdown = report_data.get("income_breakdown", [])
    deductions = report_data.get("deductions", {})
    capital_gains = report_data.get("capital_gains", {})
    observations = report_data.get("observations", [])
    magi_thresholds = report_data.get("magi_thresholds", [])
    bracket_details = report_data.get("bracket_details", [])

    # Build HTML
    html = f"""<!DOCTYPE html>
<html>
<head><style>{REPORT_CSS}</style></head>
<body>
<div class="header">
    <h1>{household.get('name', 'Tax Report')}</h1>
    <div class="firm">{report_data.get('firm_name', '')} | {report_data.get('advisor_name', '')}</div>
    <div>Tax Year {scenario.get('tax_year', '')} | Filing Status: {summary.get('filing_status', '').upper()}</div>
</div>

<h2>Tax Summary</h2>
<div class="summary-grid">
    <div class="summary-box">
        <div class="label">Total Income</div>
        <div class="value">{_fmt_money(summary.get('total_income'))}</div>
    </div>
    <div class="summary-box">
        <div class="label">AGI</div>
        <div class="value">{_fmt_money(summary.get('agi'))}</div>
    </div>
    <div class="summary-box">
        <div class="label">Taxable Income</div>
        <div class="value">{_fmt_money(summary.get('taxable_income'))}</div>
    </div>
    <div class="summary-box">
        <div class="label">Total Federal Tax</div>
        <div class="value">{_fmt_money(summary.get('total_tax'))}</div>
    </div>
    <div class="summary-box">
        <div class="label">Effective Rate</div>
        <div class="value">{_fmt_pct(summary.get('effective_rate'))}</div>
    </div>
    <div class="summary-box">
        <div class="label">Marginal Bracket</div>
        <div class="value">{_fmt_pct(summary.get('marginal_bracket_pct'))}</div>
    </div>
</div>

<h2>Income Breakdown</h2>
<table>
<tr><th>Income Source</th><th class="money">Amount</th></tr>
"""
    for item in income_breakdown:
        html += f'<tr><td>{item["label"]}</td><td class="money">{_fmt_money(item["value"])}</td></tr>\n'

    html += f"""</table>

<h2>Tax Bracket Visualization</h2>
<div class="bracket-bar">
"""
    colors = ['#22c55e', '#84cc16', '#eab308', '#f97316', '#ef4444', '#dc2626', '#991b1b']
    for i, bracket in enumerate(bracket_details):
        if bracket.get("ordinary_income_in_bracket", 0) > 0:
            width = max(bracket.get("fill_pct", 0) * 0.14, 3)  # Scale width
            color = colors[min(i, len(colors)-1)]
            html += f'<div class="bracket-segment" style="width:{width}%;background:{color}">{bracket["rate_pct"]}%</div>\n'

    html += f"""</div>

<h2>MAGI Planning Thresholds</h2>
<table>
<tr><th>Threshold</th><th class="money">Start</th><th class="money">End</th><th class="money">Client MAGI</th><th>Status</th></tr>
"""
    for t in magi_thresholds:
        status = t.get("status", "")
        html += f'<tr><td>{t["name"]}</td><td class="money">{_fmt_money(t.get("start"))}</td><td class="money">{_fmt_money(t.get("end")) if t.get("end") else "—"}</td><td class="money">{_fmt_money(t.get("client_magi"))}</td><td>{status}</td></tr>\n'

    html += f"""</table>

<h2>Deductions Summary</h2>
<table>
<tr><td>Standard Deduction</td><td class="money">{_fmt_money(deductions.get('standard_deduction'))}</td></tr>
<tr><td>Total Itemized</td><td class="money">{_fmt_money(deductions.get('total_itemized'))}</td></tr>
<tr><td><strong>Deduction Used ({deductions.get('deduction_type', 'standard').title()})</strong></td><td class="money"><strong>{_fmt_money(deductions.get('deduction_used'))}</strong></td></tr>
<tr><td>QBI Deduction</td><td class="money">{_fmt_money(deductions.get('qbi_deduction'))}</td></tr>
</table>
"""

    # Itemized breakdown if applicable
    ib = deductions.get("itemized_breakdown", {})
    if ib and deductions.get("deduction_type") == "itemized":
        html += """<h3>Itemized Deduction Breakdown</h3><table>"""
        html += f'<tr><td>Medical (above 7.5% AGI)</td><td class="money">{_fmt_money(ib.get("medical_deductible"))}</td></tr>'
        html += f'<tr><td>SALT (capped)</td><td class="money">{_fmt_money(ib.get("salt_capped"))}</td></tr>'
        html += f'<tr><td>Mortgage Interest</td><td class="money">{_fmt_money(ib.get("mortgage_interest"))}</td></tr>'
        html += f'<tr><td>Charitable</td><td class="money">{_fmt_money(ib.get("charitable"))}</td></tr>'
        html += "</table>"

    html += f"""
<h2>Capital Gains Summary</h2>
<table>
<tr><td>Short-Term Gains/Losses</td><td class="money">{_fmt_money(capital_gains.get('st_gains_losses'))}</td></tr>
<tr><td>Long-Term Gains/Losses</td><td class="money">{_fmt_money(capital_gains.get('lt_gains_losses'))}</td></tr>
<tr><td>Net Capital Gain/Loss</td><td class="money">{_fmt_money(capital_gains.get('net_capital'))}</td></tr>
<tr><td>Loss Carryforward</td><td class="money">{_fmt_money(capital_gains.get('carryforward'))}</td></tr>
<tr><td>Room in 0% LTCG Bracket</td><td class="money">{_fmt_money(capital_gains.get('ltcg_0pct_room'))}</td></tr>
</table>

<h2>Observations</h2>
"""
    for obs in observations:
        severity = obs.get("severity", "info")
        html += f'<div class="observation {severity}">{obs["text"]}</div>\n'

    html += f"""
<div class="footer">
    Generated {datetime.now().strftime('%B %d, %Y')} | For informational purposes only. Not tax advice.
</div>
</body></html>"""

    return _html_to_pdf(html)


def generate_scenario_comparison_pdf(comparison_data: dict, household_name: str) -> bytes:
    """Generate a Scenario Comparison PDF."""
    scenarios = comparison_data.get("scenarios", [])
    fields = comparison_data.get("comparison_fields", [])

    html = f"""<!DOCTYPE html>
<html>
<head><style>{REPORT_CSS}</style></head>
<body>
<div class="header">
    <h1>Scenario Comparison — {household_name}</h1>
</div>
<table>
<tr><th>Line Item</th>"""

    for s in scenarios:
        html += f'<th class="money">{s["scenario_name"]}</th>'
    if len(scenarios) > 1:
        html += '<th class="money">Change ($)</th><th class="money">Change (%)</th>'

    html += "</tr>"

    field_labels = {
        "agi": "AGI", "taxable_income": "Taxable Income", "total_tax": "Federal Tax",
        "effective_rate": "Effective Rate", "marginal_bracket_pct": "Marginal Bracket",
        "niit": "NIIT", "se_tax": "SE Tax", "total_credits": "Total Credits",
        "ordinary_tax": "Ordinary Tax", "ltcg_tax": "LTCG Tax",
        "qbi_deduction": "QBI Deduction", "total_income": "Total Income",
        "deduction_used": "Deduction Used", "refund_or_owed": "Refund/Owed",
        "effective_tax_on_next_1000": "Tax on Next $1,000",
        "social_security_taxable": "SS Taxable",
        "additional_medicare_tax": "Addt'l Medicare",
        "total_other_taxes": "Other Taxes",
    }

    for field in fields:
        label = field_labels.get(field, field.replace("_", " ").title())
        html += f"<tr><td>{label}</td>"
        for s in scenarios:
            val = s["values"].get(field)
            if field in ("effective_rate", "marginal_bracket_pct"):
                html += f'<td class="money">{_fmt_pct(val)}</td>'
            else:
                html += f'<td class="money">{_fmt_money(val)}</td>'

        if len(scenarios) > 1 and "changes" in scenarios[-1]:
            change = scenarios[-1]["changes"].get(field, {})
            dollar = change.get("dollar", 0)
            pct = change.get("percent", 0)
            cls = "positive" if dollar < 0 else "negative" if dollar > 0 else ""
            if field in ("effective_rate", "marginal_bracket_pct"):
                html += f'<td class="money {cls}">{_fmt_pct(dollar)}</td>'
            else:
                html += f'<td class="money {cls}">{_fmt_money(dollar)}</td>'
            html += f'<td class="money">{pct:+.1f}%</td>'

        html += "</tr>"

    html += """</table>
<div class="footer">For informational purposes only. Not tax advice.</div>
</body></html>"""

    return _html_to_pdf(html)


def generate_letter_pdf(letter_data: dict, household_name: str, advisor_name: str, firm_name: str) -> bytes:
    """Generate a Tax Letter PDF."""
    sections = letter_data.get("sections", [])
    tax_year = letter_data.get("tax_year", "")

    html = f"""<!DOCTYPE html>
<html>
<head><style>{REPORT_CSS}
.letter-section {{ margin: 20px 0; padding: 15px 0; border-bottom: 1px solid #e2e8f0; }}
.letter-section:last-child {{ border-bottom: none; }}
</style></head>
<body>
<div class="header">
    <h1>Tax Planning Letter — {household_name}</h1>
    <div class="firm">{firm_name}</div>
    <div>Tax Year {tax_year} | Prepared by {advisor_name}</div>
</div>
"""
    for section in sections:
        html += f"""<div class="letter-section">
    <h2>{section.get('title', '')}</h2>
    <p>{section.get('content', '').replace(chr(10), '<br>')}</p>
</div>
"""

    html += f"""
<div class="footer">
    Prepared {datetime.now().strftime('%B %d, %Y')} | For informational purposes only. Not tax advice.
</div>
</body></html>"""

    return _html_to_pdf(html)


def generate_explainer_pdf(explainer_data: dict) -> bytes:
    """Generate an Explainer PDF."""
    title = explainer_data.get("title", "Tax Explainer")
    household = explainer_data.get("household_name", "")
    tax_year = explainer_data.get("tax_year", "")

    html = f"""<!DOCTYPE html>
<html>
<head><style>{REPORT_CSS}</style></head>
<body>
<div class="header">
    <h1>{title}</h1>
    <div>{household} | Tax Year {tax_year}</div>
</div>
"""

    # Handle both line-by-line explainer and section-based explainer
    if "lines" in explainer_data:
        for line in explainer_data["lines"]:
            html += f"""<div style="margin: 15px 0; padding: 10px; background: #f8fafc; border-radius: 4px;">
    <strong>{line.get('line', '')} — {line.get('label', '')}</strong>: {_fmt_money(line.get('amount', 0))}
    <p style="margin: 5px 0 0 0; color: #475569;">{line.get('explanation', '')}</p>
</div>
"""
    elif "sections" in explainer_data:
        for section in explainer_data["sections"]:
            html += f"""<h2>{section.get('heading', '')}</h2>
<p>{section.get('content', '').replace(chr(10), '<br>')}</p>
"""

    html += """<div class="footer">For informational purposes only. Not tax advice.</div>
</body></html>"""

    return _html_to_pdf(html)


def _html_to_pdf(html: str) -> bytes:
    """Convert HTML to PDF bytes. Try WeasyPrint, fall back to returning HTML."""
    try:
        from weasyprint import HTML
        return HTML(string=html).write_pdf()
    except ImportError:
        pass

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from io import BytesIO

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(72, 750, "Tax Report — PDF generation requires WeasyPrint")
        c.drawString(72, 730, "Install with: pip install weasyprint")
        c.drawString(72, 710, "HTML content is available via the API.")
        c.save()
        buffer.seek(0)
        return buffer.read()
    except ImportError:
        pass

    # Last resort: return HTML as bytes (can be saved as .html)
    return html.encode("utf-8")
