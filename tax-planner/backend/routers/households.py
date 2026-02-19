"""Household management API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import Household, TaxReturn, Scenario, TaxLetter
from ..tax_engine.calculator import calculate_tax

router = APIRouter(prefix="/api/households", tags=["households"])


class HouseholdCreate(BaseModel):
    name: str
    primary_name: Optional[str] = None
    primary_dob: Optional[str] = None
    primary_ssn_last4: Optional[str] = None
    secondary_name: Optional[str] = None
    secondary_dob: Optional[str] = None
    filing_status: str = "single"
    state: Optional[str] = None
    notes: Optional[str] = None


class HouseholdUpdate(HouseholdCreate):
    pass


class HouseholdResponse(BaseModel):
    id: int
    name: str
    primary_name: Optional[str]
    primary_dob: Optional[str]
    primary_ssn_last4: Optional[str]
    secondary_name: Optional[str]
    secondary_dob: Optional[str]
    filing_status: str
    state: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HouseholdListItem(BaseModel):
    id: int
    name: str
    filing_status: str
    state: Optional[str]
    tax_year: Optional[int] = None
    agi: Optional[float] = None
    marginal_bracket: Optional[float] = None
    effective_rate: Optional[float] = None
    carryforward_loss: Optional[float] = None
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[HouseholdListItem])
def list_households(
    search: Optional[str] = Query(None),
    filing_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List all households with summary info."""
    query = db.query(Household)

    if search:
        query = query.filter(Household.name.ilike(f"%{search}%"))
    if filing_status:
        query = query.filter(Household.filing_status == filing_status)

    query = query.order_by(Household.updated_at.desc())
    households = query.all()

    result = []
    for h in households:
        item = HouseholdListItem(
            id=h.id,
            name=h.name,
            filing_status=h.filing_status,
            state=h.state,
            updated_at=h.updated_at,
        )

        # Get latest scenario for summary data
        latest_scenario = (
            db.query(Scenario)
            .filter(Scenario.household_id == h.id)
            .order_by(Scenario.tax_year.desc(), Scenario.updated_at.desc())
            .first()
        )
        if latest_scenario and latest_scenario.calculated_outputs:
            outputs = latest_scenario.calculated_outputs
            item.tax_year = latest_scenario.tax_year
            item.agi = outputs.get("agi")
            item.marginal_bracket = outputs.get("marginal_bracket_pct")
            item.effective_rate = outputs.get("effective_rate")
            item.carryforward_loss = outputs.get("capital_loss_carryforward_remaining")

        result.append(item)

    return result


@router.post("", response_model=HouseholdResponse)
def create_household(data: HouseholdCreate, db: Session = Depends(get_db)):
    """Create a new household."""
    household = Household(**data.model_dump())
    db.add(household)
    db.commit()
    db.refresh(household)
    return household


@router.get("/{household_id}", response_model=HouseholdResponse)
def get_household(household_id: int, db: Session = Depends(get_db)):
    """Get a household by ID."""
    household = db.query(Household).filter(Household.id == household_id).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")
    return household


@router.put("/{household_id}", response_model=HouseholdResponse)
def update_household(household_id: int, data: HouseholdUpdate, db: Session = Depends(get_db)):
    """Update a household."""
    household = db.query(Household).filter(Household.id == household_id).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(household, key, value)

    db.commit()
    db.refresh(household)
    return household


@router.delete("/{household_id}")
def delete_household(household_id: int, db: Session = Depends(get_db)):
    """Delete a household and all related data."""
    household = db.query(Household).filter(Household.id == household_id).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    db.delete(household)
    db.commit()
    return {"message": "Household deleted"}


@router.get("/{household_id}/summary")
def get_household_summary(household_id: int, db: Session = Depends(get_db)):
    """Get complete household summary including returns, scenarios, letters."""
    household = db.query(Household).filter(Household.id == household_id).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    returns = (
        db.query(TaxReturn)
        .filter(TaxReturn.household_id == household_id)
        .order_by(TaxReturn.tax_year.desc())
        .all()
    )

    scenarios = (
        db.query(Scenario)
        .filter(Scenario.household_id == household_id)
        .order_by(Scenario.tax_year.desc(), Scenario.updated_at.desc())
        .all()
    )

    letters = (
        db.query(TaxLetter)
        .filter(TaxLetter.household_id == household_id)
        .order_by(TaxLetter.tax_year.desc())
        .all()
    )

    return {
        "household": {
            "id": household.id,
            "name": household.name,
            "primary_name": household.primary_name,
            "primary_dob": household.primary_dob,
            "secondary_name": household.secondary_name,
            "secondary_dob": household.secondary_dob,
            "filing_status": household.filing_status,
            "state": household.state,
            "notes": household.notes,
        },
        "tax_returns": [
            {
                "id": r.id,
                "tax_year": r.tax_year,
                "filing_status": r.filing_status,
                "has_pdf": bool(r.raw_pdf_path),
                "needs_review": bool(r.needs_review_fields),
                "created_at": r.created_at.isoformat(),
            }
            for r in returns
        ],
        "scenarios": [
            {
                "id": s.id,
                "tax_year": s.tax_year,
                "name": s.name,
                "is_readonly": s.is_readonly,
                "has_outputs": bool(s.calculated_outputs),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in scenarios
        ],
        "tax_letters": [
            {
                "id": l.id,
                "tax_year": l.tax_year,
                "status": l.status,
                "section_count": len(l.sections) if l.sections else 0,
                "updated_at": l.updated_at.isoformat(),
            }
            for l in letters
        ],
    }
