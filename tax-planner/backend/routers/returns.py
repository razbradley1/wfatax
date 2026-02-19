"""Tax Return API routes — upload, manual entry, extraction."""

import os
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import TaxReturn, Scenario, Household
from ..tax_engine.calculator import calculate_tax

router = APIRouter(prefix="/api/returns", tags=["returns"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class TaxReturnCreate(BaseModel):
    household_id: int
    tax_year: int
    filing_status: str
    extracted_data: dict = {}


class TaxReturnUpdate(BaseModel):
    filing_status: Optional[str] = None
    extracted_data: Optional[dict] = None


class TaxReturnResponse(BaseModel):
    id: int
    household_id: int
    tax_year: int
    filing_status: Optional[str]
    raw_pdf_path: Optional[str]
    extracted_data: dict
    needs_review_fields: list
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/{return_id}", response_model=TaxReturnResponse)
def get_return(return_id: int, db: Session = Depends(get_db)):
    """Get a tax return by ID."""
    tax_return = db.query(TaxReturn).filter(TaxReturn.id == return_id).first()
    if not tax_return:
        raise HTTPException(status_code=404, detail="Tax return not found")
    return tax_return


@router.get("/household/{household_id}")
def list_returns(household_id: int, db: Session = Depends(get_db)):
    """List all tax returns for a household."""
    returns = (
        db.query(TaxReturn)
        .filter(TaxReturn.household_id == household_id)
        .order_by(TaxReturn.tax_year.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "household_id": r.household_id,
            "tax_year": r.tax_year,
            "filing_status": r.filing_status,
            "has_pdf": bool(r.raw_pdf_path),
            "needs_review": bool(r.needs_review_fields),
            "created_at": r.created_at.isoformat(),
        }
        for r in returns
    ]


@router.post("", response_model=TaxReturnResponse)
def create_return(data: TaxReturnCreate, db: Session = Depends(get_db)):
    """Create a tax return via manual entry."""
    # Verify household exists
    household = db.query(Household).filter(Household.id == data.household_id).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    tax_return = TaxReturn(
        household_id=data.household_id,
        tax_year=data.tax_year,
        filing_status=data.filing_status,
        extracted_data=data.extracted_data,
        needs_review_fields=[],
    )
    db.add(tax_return)
    db.commit()
    db.refresh(tax_return)

    # Auto-create readonly scenario from this return
    _create_baseline_scenario(tax_return, household, db)

    return tax_return


@router.post("/upload")
async def upload_return(
    household_id: int = Form(...),
    tax_year: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a Form 1040 PDF for extraction."""
    household = db.query(Household).filter(Household.id == household_id).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Save file
    filename = f"household_{household_id}_{tax_year}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract data from PDF
    try:
        from ..pdf_engine.extractor import extract_1040_data
        extracted, needs_review = extract_1040_data(filepath)
    except Exception as e:
        extracted = {}
        needs_review = ["extraction_failed"]

    tax_return = TaxReturn(
        household_id=household_id,
        tax_year=tax_year,
        filing_status=extracted.get("filing_status", household.filing_status),
        raw_pdf_path=filepath,
        extracted_data=extracted,
        needs_review_fields=needs_review,
    )
    db.add(tax_return)
    db.commit()
    db.refresh(tax_return)

    # Auto-create baseline scenario
    _create_baseline_scenario(tax_return, household, db)

    return {
        "id": tax_return.id,
        "extracted_fields": len(extracted),
        "needs_review_fields": needs_review,
        "message": f"Extracted {len(extracted)} fields. {len(needs_review)} fields need review."
    }


@router.put("/{return_id}", response_model=TaxReturnResponse)
def update_return(return_id: int, data: TaxReturnUpdate, db: Session = Depends(get_db)):
    """Update a tax return (manual corrections after extraction)."""
    tax_return = db.query(TaxReturn).filter(TaxReturn.id == return_id).first()
    if not tax_return:
        raise HTTPException(status_code=404, detail="Tax return not found")

    if data.filing_status is not None:
        tax_return.filing_status = data.filing_status
    if data.extracted_data is not None:
        tax_return.extracted_data = data.extracted_data
        tax_return.needs_review_fields = []  # Clear review flags on manual update

    db.commit()
    db.refresh(tax_return)

    # Update associated readonly scenario
    scenario = (
        db.query(Scenario)
        .filter(
            Scenario.source_return_id == return_id,
            Scenario.is_readonly == True,
        )
        .first()
    )
    if scenario:
        household = db.query(Household).filter(Household.id == tax_return.household_id).first()
        inputs = _build_scenario_inputs(tax_return, household)
        scenario.inputs = inputs
        scenario.calculated_outputs = calculate_tax(inputs)
        db.commit()

    return tax_return


@router.delete("/{return_id}")
def delete_return(return_id: int, db: Session = Depends(get_db)):
    """Delete a tax return."""
    tax_return = db.query(TaxReturn).filter(TaxReturn.id == return_id).first()
    if not tax_return:
        raise HTTPException(status_code=404, detail="Tax return not found")

    # Delete associated readonly scenario
    db.query(Scenario).filter(
        Scenario.source_return_id == return_id,
        Scenario.is_readonly == True,
    ).delete()

    # Delete PDF file if exists
    if tax_return.raw_pdf_path and os.path.exists(tax_return.raw_pdf_path):
        os.remove(tax_return.raw_pdf_path)

    db.delete(tax_return)
    db.commit()
    return {"message": "Tax return deleted"}


def _build_scenario_inputs(tax_return: TaxReturn, household: Household) -> dict:
    """Build scenario inputs from a tax return's extracted data."""
    data = tax_return.extracted_data or {}
    inputs = {
        "tax_year": tax_return.tax_year,
        "filing_status": tax_return.filing_status or household.filing_status,
        "state": household.state or "",
    }
    # Map all extracted fields
    field_mappings = [
        "wages_salaries", "interest_income_taxable", "interest_income_exempt",
        "qualified_dividends", "ordinary_dividends", "ira_distributions_total",
        "ira_distributions_taxable", "pension_annuity_total", "pension_annuity_taxable",
        "social_security_total", "social_security_taxable", "capital_gain_loss",
        "st_gains_losses", "lt_gains_losses", "other_income", "business_income",
        "rental_income", "k1_income", "medical_expenses", "state_local_taxes",
        "mortgage_interest", "charitable_contributions", "other_itemized",
        "qbi_eligible_income", "federal_withholding", "estimated_tax_payments",
        "capital_loss_carryforward", "num_qualifying_children",
    ]
    for field in field_mappings:
        if field in data:
            inputs[field] = data[field]

    # Set use_itemized if itemized was used
    if data.get("standard_or_itemized_deduction") and data.get("total_itemized"):
        inputs["use_itemized"] = data.get("total_itemized", 0) > 0

    return inputs


def _create_baseline_scenario(
    tax_return: TaxReturn, household: Household, db: Session
):
    """Create a read-only baseline scenario from a tax return."""
    inputs = _build_scenario_inputs(tax_return, household)
    outputs = calculate_tax(inputs)

    scenario = Scenario(
        household_id=tax_return.household_id,
        tax_year=tax_return.tax_year,
        name=f"Prior Year Return {tax_return.tax_year}",
        source_return_id=tax_return.id,
        is_readonly=True,
        inputs=inputs,
        calculated_outputs=outputs,
    )
    db.add(scenario)
    db.commit()
