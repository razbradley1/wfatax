"""Settings and data management API routes."""

import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from ..database import get_db
from ..models import Settings, Household, TaxReturn, Scenario, TaxLetter

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingUpdate(BaseModel):
    value: str


DEFAULT_SETTINGS = {
    "advisor_name": "Financial Advisor",
    "firm_name": "",
    "default_tax_year": "2024",
    "show_experimental": "false",
}


@router.get("")
def get_all_settings(db: Session = Depends(get_db)):
    """Get all settings."""
    settings = db.query(Settings).all()
    result = dict(DEFAULT_SETTINGS)
    for s in settings:
        result[s.key] = s.value
    return result


@router.put("/{key}")
def update_setting(key: str, data: SettingUpdate, db: Session = Depends(get_db)):
    """Update a setting."""
    setting = db.query(Settings).filter(Settings.key == key).first()
    if setting:
        setting.value = data.value
    else:
        setting = Settings(key=key, value=data.value)
        db.add(setting)
    db.commit()
    return {"key": key, "value": data.value}


@router.get("/export")
def export_all_data(db: Session = Depends(get_db)):
    """Export all data as JSON backup."""
    households = db.query(Household).all()
    returns = db.query(TaxReturn).all()
    scenarios = db.query(Scenario).all()
    letters = db.query(TaxLetter).all()
    settings = db.query(Settings).all()

    data = {
        "exported_at": datetime.utcnow().isoformat(),
        "version": "1.0",
        "households": [
            {
                "id": h.id, "name": h.name, "primary_name": h.primary_name,
                "primary_dob": h.primary_dob, "primary_ssn_last4": h.primary_ssn_last4,
                "secondary_name": h.secondary_name, "secondary_dob": h.secondary_dob,
                "filing_status": h.filing_status, "state": h.state, "notes": h.notes,
            }
            for h in households
        ],
        "tax_returns": [
            {
                "id": r.id, "household_id": r.household_id, "tax_year": r.tax_year,
                "filing_status": r.filing_status, "extracted_data": r.extracted_data,
            }
            for r in returns
        ],
        "scenarios": [
            {
                "id": s.id, "household_id": s.household_id, "tax_year": s.tax_year,
                "name": s.name, "source_return_id": s.source_return_id,
                "is_readonly": s.is_readonly, "inputs": s.inputs,
                "calculated_outputs": s.calculated_outputs, "notes": s.notes,
            }
            for s in scenarios
        ],
        "tax_letters": [
            {
                "id": l.id, "household_id": l.household_id, "tax_year": l.tax_year,
                "sections": l.sections, "status": l.status,
            }
            for l in letters
        ],
        "settings": {s.key: s.value for s in settings},
    }

    return JSONResponse(content=data)


@router.post("/import")
def import_data(data: dict, db: Session = Depends(get_db)):
    """Import data from JSON backup."""
    imported = {"households": 0, "returns": 0, "scenarios": 0, "letters": 0}

    for h_data in data.get("households", []):
        h = Household(
            name=h_data["name"],
            primary_name=h_data.get("primary_name"),
            primary_dob=h_data.get("primary_dob"),
            primary_ssn_last4=h_data.get("primary_ssn_last4"),
            secondary_name=h_data.get("secondary_name"),
            secondary_dob=h_data.get("secondary_dob"),
            filing_status=h_data.get("filing_status", "single"),
            state=h_data.get("state"),
            notes=h_data.get("notes"),
        )
        db.add(h)
        db.flush()
        old_id = h_data.get("id")

        # Import returns for this household
        for r_data in data.get("tax_returns", []):
            if r_data.get("household_id") == old_id:
                r = TaxReturn(
                    household_id=h.id,
                    tax_year=r_data["tax_year"],
                    filing_status=r_data.get("filing_status"),
                    extracted_data=r_data.get("extracted_data", {}),
                )
                db.add(r)
                imported["returns"] += 1

        # Import scenarios
        for s_data in data.get("scenarios", []):
            if s_data.get("household_id") == old_id:
                s = Scenario(
                    household_id=h.id,
                    tax_year=s_data["tax_year"],
                    name=s_data["name"],
                    is_readonly=s_data.get("is_readonly", False),
                    inputs=s_data.get("inputs", {}),
                    calculated_outputs=s_data.get("calculated_outputs", {}),
                    notes=s_data.get("notes"),
                )
                db.add(s)
                imported["scenarios"] += 1

        # Import letters
        for l_data in data.get("tax_letters", []):
            if l_data.get("household_id") == old_id:
                l = TaxLetter(
                    household_id=h.id,
                    tax_year=l_data["tax_year"],
                    sections=l_data.get("sections", []),
                    status=l_data.get("status", "draft"),
                )
                db.add(l)
                imported["letters"] += 1

        imported["households"] += 1

    # Import settings
    for key, value in data.get("settings", {}).items():
        setting = db.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = value
        else:
            db.add(Settings(key=key, value=value))

    db.commit()
    return {"message": "Import complete", "imported": imported}


@router.delete("/clear-all")
def clear_all_data(confirm: str = "", db: Session = Depends(get_db)):
    """Clear all data (requires confirm=yes)."""
    if confirm != "yes":
        raise HTTPException(
            status_code=400,
            detail="Must pass confirm=yes to clear all data"
        )

    db.query(TaxLetter).delete()
    db.query(Scenario).delete()
    db.query(TaxReturn).delete()
    db.query(Household).delete()
    db.commit()

    return {"message": "All data cleared"}
