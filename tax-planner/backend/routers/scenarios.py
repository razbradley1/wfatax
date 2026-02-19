"""Scenario Analysis API routes."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import Scenario, Household
from ..tax_engine.calculator import calculate_tax, calculate_range, find_rate_spike
from ..tax_engine.roth_projection import project_roth_conversions

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


class ScenarioCreate(BaseModel):
    household_id: int
    tax_year: int
    name: str
    source_scenario_id: Optional[int] = None
    inputs: dict = {}
    notes: Optional[str] = None


class ScenarioUpdate(BaseModel):
    name: Optional[str] = None
    inputs: Optional[dict] = None
    notes: Optional[str] = None


class ScenarioResponse(BaseModel):
    id: int
    household_id: int
    tax_year: int
    name: str
    source_return_id: Optional[int]
    is_readonly: bool
    inputs: dict
    calculated_outputs: dict
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RangeCalcRequest(BaseModel):
    income_type: str
    start_amount: float = 0
    end_amount: float = 200000
    step: float = 1000


class RateSpikeRequest(BaseModel):
    income_type: str
    max_additional: float = 500000
    step: float = 500


class RothProjectionRequest(BaseModel):
    current_age: int
    retirement_age: int
    target_end_age: int
    pretax_balance: float
    roth_balance: float
    taxable_balance: float = 0
    annual_return: float = 0.07
    expected_retirement_income: float
    target_bracket_rate: float = 0.22
    annual_contribution_pretax: float = 0
    annual_contribution_roth: float = 0


class CompareRequest(BaseModel):
    scenario_ids: List[int]


@router.get("/household/{household_id}")
def list_scenarios(household_id: int, tax_year: Optional[int] = None, db: Session = Depends(get_db)):
    """List all scenarios for a household."""
    query = db.query(Scenario).filter(Scenario.household_id == household_id)
    if tax_year:
        query = query.filter(Scenario.tax_year == tax_year)
    scenarios = query.order_by(Scenario.tax_year.desc(), Scenario.is_readonly.desc(), Scenario.updated_at.desc()).all()

    return [
        {
            "id": s.id,
            "household_id": s.household_id,
            "tax_year": s.tax_year,
            "name": s.name,
            "is_readonly": s.is_readonly,
            "source_return_id": s.source_return_id,
            "has_outputs": bool(s.calculated_outputs),
            "notes": s.notes,
            "updated_at": s.updated_at.isoformat(),
        }
        for s in scenarios
    ]


@router.get("/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Get a scenario by ID with full inputs and outputs."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.post("", response_model=ScenarioResponse)
def create_scenario(data: ScenarioCreate, db: Session = Depends(get_db)):
    """Create a new scenario, optionally cloning from another."""
    household = db.query(Household).filter(Household.id == data.household_id).first()
    if not household:
        raise HTTPException(status_code=404, detail="Household not found")

    inputs = data.inputs

    # Clone from source scenario if specified
    if data.source_scenario_id:
        source = db.query(Scenario).filter(Scenario.id == data.source_scenario_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source scenario not found")
        inputs = {**source.inputs, **data.inputs}

    # Calculate tax
    outputs = calculate_tax(inputs)

    scenario = Scenario(
        household_id=data.household_id,
        tax_year=data.tax_year,
        name=data.name,
        is_readonly=False,
        inputs=inputs,
        calculated_outputs=outputs,
        notes=data.notes,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.put("/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(scenario_id: int, data: ScenarioUpdate, db: Session = Depends(get_db)):
    """Update a scenario and recalculate."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if scenario.is_readonly:
        raise HTTPException(status_code=400, detail="Cannot edit a read-only scenario")

    if data.name is not None:
        scenario.name = data.name
    if data.notes is not None:
        scenario.notes = data.notes
    if data.inputs is not None:
        scenario.inputs = data.inputs
        scenario.calculated_outputs = calculate_tax(data.inputs)

    db.commit()
    db.refresh(scenario)
    return scenario


@router.delete("/{scenario_id}")
def delete_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Delete a scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    if scenario.is_readonly:
        raise HTTPException(status_code=400, detail="Cannot delete a read-only scenario")

    db.delete(scenario)
    db.commit()
    return {"message": "Scenario deleted"}


@router.post("/{scenario_id}/calculate")
def recalculate_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Force recalculate a scenario."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    scenario.calculated_outputs = calculate_tax(scenario.inputs)
    db.commit()
    return scenario.calculated_outputs


@router.post("/compare")
def compare_scenarios(data: CompareRequest, db: Session = Depends(get_db)):
    """Side-by-side comparison of multiple scenarios."""
    scenarios = db.query(Scenario).filter(Scenario.id.in_(data.scenario_ids)).all()

    if len(scenarios) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 scenarios to compare")

    comparison_fields = [
        "agi", "taxable_income", "total_tax", "effective_rate",
        "marginal_bracket_pct", "niit", "se_tax", "total_credits",
        "ordinary_tax", "ltcg_tax", "qbi_deduction", "total_income",
        "deduction_used", "deduction_type", "social_security_taxable",
        "additional_medicare_tax", "total_other_taxes",
        "refund_or_owed", "effective_tax_on_next_1000",
    ]

    columns = []
    for s in scenarios:
        outputs = s.calculated_outputs or {}
        col = {
            "scenario_id": s.id,
            "scenario_name": s.name,
            "is_readonly": s.is_readonly,
            "values": {field: outputs.get(field) for field in comparison_fields},
        }
        # Add IRMAA tier
        irmaa = outputs.get("irmaa", {})
        col["values"]["irmaa_tier"] = irmaa.get("tier")
        col["values"]["irmaa_surcharge"] = irmaa.get("annual_total_surcharge")
        columns.append(col)

    # Calculate changes between each scenario and the first (baseline)
    baseline = columns[0]["values"]
    for col in columns[1:]:
        col["changes"] = {}
        for field in comparison_fields:
            bval = baseline.get(field) or 0
            sval = col["values"].get(field) or 0
            if isinstance(bval, (int, float)) and isinstance(sval, (int, float)):
                col["changes"][field] = {
                    "dollar": round(sval - bval, 2),
                    "percent": round(((sval - bval) / bval * 100), 1) if bval != 0 else 0,
                }

    return {
        "scenarios": columns,
        "comparison_fields": comparison_fields,
    }


@router.post("/{scenario_id}/range-calc")
def range_calc(scenario_id: int, data: RangeCalcRequest, db: Session = Depends(get_db)):
    """Calculate marginal rate across a range of income values."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    points = calculate_range(
        base_inputs=scenario.inputs,
        income_type=data.income_type,
        start_amount=data.start_amount,
        end_amount=data.end_amount,
        step=data.step,
    )
    return {"data_points": points, "income_type": data.income_type}


@router.post("/{scenario_id}/find-spike")
def find_spike(scenario_id: int, data: RateSpikeRequest, db: Session = Depends(get_db)):
    """Find where effective marginal rate spikes."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    result = find_rate_spike(
        base_inputs=scenario.inputs,
        income_type=data.income_type,
        max_additional=data.max_additional,
        step=data.step,
    )
    return result


@router.post("/{scenario_id}/roth-projection")
def roth_projection(scenario_id: int, data: RothProjectionRequest, db: Session = Depends(get_db)):
    """Multi-year Roth conversion projection."""
    scenario = db.query(Scenario).filter(Scenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    filing_status = scenario.inputs.get("filing_status", "single")
    tax_year = scenario.inputs.get("tax_year", 2024)

    result = project_roth_conversions(
        current_age=data.current_age,
        retirement_age=data.retirement_age,
        target_end_age=data.target_end_age,
        pretax_balance=data.pretax_balance,
        roth_balance=data.roth_balance,
        taxable_balance=data.taxable_balance,
        annual_return=data.annual_return,
        expected_retirement_income=data.expected_retirement_income,
        filing_status=filing_status,
        target_bracket_rate=data.target_bracket_rate,
        tax_year=tax_year,
        annual_contribution_pretax=data.annual_contribution_pretax,
        annual_contribution_roth=data.annual_contribution_roth,
    )
    return result


@router.post("/quick-calc")
def quick_calc(inputs: dict):
    """Quick calculation without saving — for live preview."""
    return calculate_tax(inputs)
