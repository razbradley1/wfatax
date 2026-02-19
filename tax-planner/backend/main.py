"""FastAPI application entry point."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .database import init_db, get_db, SessionLocal
from .routers import households, returns, scenarios, letters, reports, settings
from .pdf_engine.exporter import (
    generate_tax_report_pdf,
    generate_scenario_comparison_pdf,
    generate_letter_pdf,
    generate_explainer_pdf,
)

app = FastAPI(
    title="Tax Planner",
    description="Personal tax planning application for financial advisors",
    version="1.0.0",
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(households.router)
app.include_router(returns.router)
app.include_router(scenarios.router)
app.include_router(letters.router)
app.include_router(reports.router)
app.include_router(settings.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


# PDF export endpoints
@app.get("/api/export/tax-report/{scenario_id}")
def export_tax_report_pdf(scenario_id: int):
    """Export Tax Report as PDF."""
    db = SessionLocal()
    try:
        report_data = reports.get_tax_report(scenario_id, db)
        pdf_bytes = generate_tax_report_pdf(report_data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=tax_report_{scenario_id}.pdf"},
        )
    finally:
        db.close()


@app.post("/api/export/scenario-comparison")
def export_scenario_comparison_pdf(request: dict):
    """Export Scenario Comparison as PDF."""
    db = SessionLocal()
    try:
        from .routers.scenarios import CompareRequest
        compare_data = scenarios.compare_scenarios(
            CompareRequest(scenario_ids=request.get("scenario_ids", [])), db
        )
        household_name = request.get("household_name", "")
        pdf_bytes = generate_scenario_comparison_pdf(compare_data, household_name)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=scenario_comparison.pdf"},
        )
    finally:
        db.close()


@app.get("/api/export/letter/{letter_id}")
def export_letter_pdf(letter_id: int):
    """Export Tax Letter as PDF."""
    db = SessionLocal()
    try:
        from .models import TaxLetter, Household, Settings
        letter = db.query(TaxLetter).filter(TaxLetter.id == letter_id).first()
        if not letter:
            return Response(status_code=404)
        household = db.query(Household).filter(Household.id == letter.household_id).first()

        advisor = db.query(Settings).filter(Settings.key == "advisor_name").first()
        firm = db.query(Settings).filter(Settings.key == "firm_name").first()

        letter_data = {
            "sections": letter.sections or [],
            "tax_year": letter.tax_year,
        }
        pdf_bytes = generate_letter_pdf(
            letter_data,
            household.name if household else "",
            advisor.value if advisor else "Financial Advisor",
            firm.value if firm else "",
        )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=tax_letter_{letter_id}.pdf"},
        )
    finally:
        db.close()


@app.get("/api/export/explainer/{explainer_type}/{scenario_id}")
def export_explainer_pdf(explainer_type: str, scenario_id: int):
    """Export Explainer as PDF."""
    db = SessionLocal()
    try:
        if explainer_type == "tax":
            data = reports.get_tax_explainer(scenario_id, db)
        elif explainer_type == "roth":
            data = reports.get_roth_explainer(scenario_id, db)
        elif explainer_type == "qcd":
            data = reports.get_qcd_explainer(scenario_id, db)
        elif explainer_type == "daf":
            data = reports.get_daf_explainer(scenario_id, db)
        else:
            return Response(status_code=400)

        pdf_bytes = generate_explainer_pdf(data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=explainer_{explainer_type}_{scenario_id}.pdf"
            },
        )
    finally:
        db.close()


# Serve frontend static files in production
static_dir = os.environ.get("STATIC_DIR")
if static_dir and os.path.isdir(static_dir):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(static_dir, "index.html"))

    app.mount("/", StaticFiles(directory=static_dir), name="static")
else:

    @app.get("/")
    def root():
        return {"message": "Tax Planner API. Frontend at http://localhost:5173"}
