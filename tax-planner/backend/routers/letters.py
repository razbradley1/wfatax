"""Tax Letter API routes."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import TaxLetter, Household

router = APIRouter(prefix="/api/letters", tags=["letters"])


# Pre-built section templates
SECTION_TEMPLATES = {
    "roth_conversion": {
        "title": "Roth Conversion",
        "content": "We executed a Roth conversion of $[AMOUNT] during tax year [YEAR]. This conversion moved pre-tax IRA funds into your Roth IRA, where future growth and qualified withdrawals will be tax-free. The conversion amount is included in your taxable income for [YEAR], increasing your federal tax liability by approximately $[TAX_IMPACT]. This strategy is designed to reduce future Required Minimum Distributions and take advantage of your current tax bracket.",
        "pinned": False,
    },
    "charitable_giving": {
        "title": "Charitable Giving Strategy",
        "content": "Your charitable contributions for [YEAR] totaled $[AMOUNT]. [If applicable: We utilized a Qualified Charitable Distribution (QCD) of $[QCD_AMOUNT] from your IRA, which satisfies your Required Minimum Distribution while excluding the distribution from taxable income.] [If applicable: A contribution of $[DAF_AMOUNT] was made to your Donor Advised Fund, allowing you to take the full deduction this year while distributing grants to charities over multiple years.]",
        "pinned": False,
    },
    "capital_gains": {
        "title": "Capital Gains Management",
        "content": "During [YEAR], your investment portfolio generated $[ST_GAINS] in short-term gains and $[LT_GAINS] in long-term gains. [If applicable: We harvested $[LOSSES] in losses to offset gains, reducing your taxable capital gains by $[OFFSET].] Your net capital gain of $[NET] is taxed at preferential long-term rates. [If applicable: You have $[CARRYFORWARD] in capital loss carryforward available for future years.]",
        "pinned": False,
    },
    "retirement_contributions": {
        "title": "Retirement Contributions",
        "content": "For [YEAR], your retirement contributions included:\n- 401(k)/403(b): $[401K_AMOUNT]\n- Traditional IRA: $[IRA_AMOUNT]\n- Roth IRA: $[ROTH_AMOUNT]\n- HSA: $[HSA_AMOUNT]\n\nThese contributions reduce your current taxable income and build tax-advantaged savings for retirement.",
        "pinned": False,
    },
    "estimated_payments": {
        "title": "Estimated Tax Payments",
        "content": "For tax year [YEAR], your estimated tax payments were:\n- Q1 (April): $[Q1]\n- Q2 (June): $[Q2]\n- Q3 (September): $[Q3]\n- Q4 (January): $[Q4]\n- Total: $[TOTAL]\n\n[Your estimated payments covered approximately [COVERAGE]% of your total tax liability.]",
        "pinned": False,
    },
    "business_income": {
        "title": "Business Income Summary",
        "content": "Your business income for [YEAR]:\n- Gross revenue: $[REVENUE]\n- Business expenses: $[EXPENSES]\n- Net profit: $[NET]\n- Self-employment tax: $[SE_TAX]\n- QBI deduction: $[QBI]\n\n[Include any notable business deductions or planning notes.]",
        "pinned": False,
    },
    "other_notes": {
        "title": "Additional Notes",
        "content": "",
        "pinned": False,
    },
}


class LetterSection(BaseModel):
    title: str
    content: str
    pinned: bool = False


class LetterCreate(BaseModel):
    household_id: int
    tax_year: int
    sections: List[LetterSection] = []


class LetterUpdate(BaseModel):
    sections: Optional[List[LetterSection]] = None
    status: Optional[str] = None


class LetterResponse(BaseModel):
    id: int
    household_id: int
    tax_year: int
    sections: list
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/household/{household_id}")
def list_letters(household_id: int, db: Session = Depends(get_db)):
    """List tax letters for a household."""
    letters = (
        db.query(TaxLetter)
        .filter(TaxLetter.household_id == household_id)
        .order_by(TaxLetter.tax_year.desc())
        .all()
    )
    return [
        {
            "id": l.id,
            "household_id": l.household_id,
            "tax_year": l.tax_year,
            "status": l.status,
            "section_count": len(l.sections) if l.sections else 0,
            "updated_at": l.updated_at.isoformat(),
        }
        for l in letters
    ]


@router.get("/templates")
def get_templates():
    """Get available section templates."""
    return SECTION_TEMPLATES


@router.get("/{letter_id}", response_model=LetterResponse)
def get_letter(letter_id: int, db: Session = Depends(get_db)):
    """Get a tax letter."""
    letter = db.query(TaxLetter).filter(TaxLetter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="Tax letter not found")
    return letter


@router.post("", response_model=LetterResponse)
def create_letter(data: LetterCreate, db: Session = Depends(get_db)):
    """Create a new tax letter."""
    household = db.query(Household).filter(Household.id == data.household_id).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    sections = [s.model_dump() for s in data.sections] if data.sections else []

    letter = TaxLetter(
        household_id=data.household_id,
        tax_year=data.tax_year,
        sections=sections,
        status="draft",
    )
    db.add(letter)
    db.commit()
    db.refresh(letter)
    return letter


@router.put("/{letter_id}", response_model=LetterResponse)
def update_letter(letter_id: int, data: LetterUpdate, db: Session = Depends(get_db)):
    """Update a tax letter."""
    letter = db.query(TaxLetter).filter(TaxLetter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="Tax letter not found")

    if data.sections is not None:
        letter.sections = [s.model_dump() for s in data.sections]
    if data.status is not None:
        if data.status not in ("draft", "in_review", "complete"):
            raise HTTPException(status_code=400, detail="Invalid status")
        letter.status = data.status

    db.commit()
    db.refresh(letter)
    return letter


@router.delete("/{letter_id}")
def delete_letter(letter_id: int, db: Session = Depends(get_db)):
    """Delete a tax letter."""
    letter = db.query(TaxLetter).filter(TaxLetter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="Tax letter not found")

    db.delete(letter)
    db.commit()
    return {"message": "Tax letter deleted"}
