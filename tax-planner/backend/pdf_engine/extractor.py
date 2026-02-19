"""Form 1040 PDF extraction engine.

Uses pdfplumber for text-based PDFs, falls back to pytesseract for scanned PDFs.
"""

import re
from typing import Tuple, Dict, List

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import pytesseract
    from pdf2image import convert_from_path
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


def extract_1040_data(pdf_path: str) -> Tuple[Dict, List[str]]:
    """
    Extract Form 1040 data from a PDF file.

    Returns:
        (extracted_data, needs_review_fields)
    """
    text = ""

    # Try pdfplumber first
    if HAS_PDFPLUMBER:
        try:
            text = _extract_with_pdfplumber(pdf_path)
        except Exception:
            pass

    # Fall back to OCR if pdfplumber didn't work
    if not text.strip() and HAS_OCR:
        try:
            text = _extract_with_ocr(pdf_path)
        except Exception:
            pass

    if not text.strip():
        return {}, ["extraction_failed"]

    # Parse the extracted text
    data, needs_review = _parse_1040_text(text)
    return data, needs_review


def _extract_with_pdfplumber(pdf_path: str) -> str:
    """Extract text using pdfplumber."""
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
    return full_text


def _extract_with_ocr(pdf_path: str) -> str:
    """Extract text using OCR (pytesseract + pdf2image)."""
    images = convert_from_path(pdf_path)
    full_text = ""
    for image in images:
        text = pytesseract.image_to_string(image)
        full_text += text + "\n"
    return full_text


def _parse_amount(text: str) -> float:
    """Parse a dollar amount from text."""
    # Remove $, commas, spaces
    cleaned = re.sub(r'[$,\s]', '', text)
    # Handle parentheses for negative
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _find_line_value(text: str, patterns: list) -> Tuple[float, bool]:
    """
    Try to find a value matching patterns in the text.
    Returns (value, confident) where confident indicates extraction certainty.
    """
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            for match in matches:
                val = _parse_amount(match if isinstance(match, str) else match[-1])
                if val != 0:
                    return val, True
    return 0.0, False


def _parse_1040_text(text: str) -> Tuple[Dict, List[str]]:
    """Parse extracted text and map to 1040 schema."""
    data = {}
    needs_review = []

    # Filing status detection
    filing_status = "single"
    if re.search(r'married\s*filing\s*joint', text, re.IGNORECASE):
        filing_status = "mfj"
    elif re.search(r'married\s*filing\s*separate', text, re.IGNORECASE):
        filing_status = "mfs"
    elif re.search(r'head\s*of\s*household', text, re.IGNORECASE):
        filing_status = "hoh"
    elif re.search(r'qualifying\s*(surviving\s*spouse|widow)', text, re.IGNORECASE):
        filing_status = "qw"
    data["filing_status"] = filing_status

    # Field extraction patterns: (field_name, [regex_patterns])
    field_patterns = [
        ("wages_salaries", [
            r'(?:line\s*1a?|wages.*salaries.*tips)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
            r'1a\s+[\w\s]*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("interest_income_taxable", [
            r'(?:line\s*2b|taxable\s*interest)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
            r'2b\s+\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("interest_income_exempt", [
            r'(?:line\s*2a|tax.exempt\s*interest)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
            r'2a\s+\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("qualified_dividends", [
            r'(?:line\s*3a|qualified\s*dividends)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
            r'3a\s+\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("ordinary_dividends", [
            r'(?:line\s*3b|ordinary\s*dividends)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
            r'3b\s+\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("ira_distributions_total", [
            r'(?:line\s*4a|IRA\s*distributions)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("ira_distributions_taxable", [
            r'(?:line\s*4b|taxable\s*amount.*4b)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("pension_annuity_total", [
            r'(?:line\s*5a|pensions?\s*(?:and|&)\s*annuit)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("pension_annuity_taxable", [
            r'(?:line\s*5b)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("social_security_total", [
            r'(?:line\s*6a|social\s*security\s*benefits)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("social_security_taxable", [
            r'(?:line\s*6b)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("capital_gain_loss", [
            r'(?:line\s*7|capital\s*gain\s*or\s*loss)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("other_income", [
            r'(?:line\s*8|other\s*income)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("total_income", [
            r'(?:line\s*9|total\s*income)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("agi", [
            r'(?:line\s*11|adjusted\s*gross\s*income)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("standard_or_itemized_deduction", [
            r'(?:line\s*12[a-c]?|standard\s*deduction|itemized\s*deductions?)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("qbi_deduction", [
            r'(?:line\s*13|qualified\s*business\s*income)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("taxable_income", [
            r'(?:line\s*15|taxable\s*income)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("tax", [
            r'(?:line\s*16|^tax\b)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("total_tax", [
            r'(?:line\s*24|total\s*tax)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("federal_withholding", [
            r'(?:line\s*25[a-d]?|federal.*withh?olding|tax\s*withh?eld)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("estimated_tax_payments", [
            r'(?:line\s*26|estimated\s*tax\s*payments)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
    ]

    # Schedule A patterns
    schedule_a_patterns = [
        ("medical_expenses", [
            r'medical.*dental.*expenses?\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("state_local_taxes", [
            r'(?:state\s*(?:and|&)\s*local\s*(?:income\s*)?taxes?|SALT)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("mortgage_interest", [
            r'(?:home\s*)?mortgage\s*interest\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("charitable_contributions", [
            r'(?:gifts?\s*(?:to|by)\s*cash|charitable\s*contributions?)\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
        ("total_itemized", [
            r'total\s*itemized\s*deductions?\s*[:.]*\s*\$?([\d,]+(?:\.\d{2})?)',
        ]),
    ]

    for field_name, patterns in field_patterns + schedule_a_patterns:
        value, confident = _find_line_value(text, patterns)
        if value != 0:
            data[field_name] = value
            if not confident:
                needs_review.append(field_name)
        elif field_name in ("wages_salaries", "agi", "total_income", "taxable_income"):
            needs_review.append(field_name)

    return data, needs_review
