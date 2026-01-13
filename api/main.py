"""
HireCharm Onboarding Form API

Handles form submissions and stores them in Supabase/PostgreSQL.
"""

import os
import json
import logging
from uuid import uuid4
from datetime import datetime
from typing import Optional, List, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="HireCharm Onboarding API",
    description="API for capturing client onboarding form submissions",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Database Configuration
# =============================================================================

def get_database_url() -> str:
    """Build database URL from environment variables."""
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    database = os.getenv('POSTGRES_DB', 'postgres')
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', '')

    # Support Supabase connection string format
    if os.getenv('DATABASE_URL'):
        return os.getenv('DATABASE_URL')

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def get_db_session():
    """Create a database session."""
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    return Session()


# =============================================================================
# Pydantic Models
# =============================================================================

class Segment(BaseModel):
    name: str = Field(default="", alias="segment_name")
    revenue_pct: Optional[int] = Field(default=None, alias="revenue_percentage")
    unique_characteristics: Optional[str] = None
    pain_points: Optional[str] = None
    buying_triggers: Optional[str] = None

    class Config:
        populate_by_name = True


class Persona(BaseModel):
    job_title: str = ""
    primary_segment: Optional[str] = None
    seniority_level: Optional[str] = None
    pain_before_buying: Optional[str] = None
    aha_moment: Optional[str] = None
    objections: Optional[str] = None
    decision_criteria: Optional[str] = None

    class Config:
        populate_by_name = True


class OnboardingSubmission(BaseModel):
    """Full onboarding form submission payload."""

    # Client identifier (required for linking)
    client_id: Optional[str] = None

    # Section 1: Foundation
    company_name: Optional[str] = None
    website: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    employee_count: Optional[str] = None
    funding_stage: Optional[str] = None
    hq_location: Optional[str] = None

    # Section 2: Offering
    core_product: Optional[str] = None
    target_customer: Optional[str] = None
    annual_revenue: Optional[str] = None
    acv: Optional[str] = None
    sales_cycle_length: Optional[str] = None
    self_serve_pct: Optional[Any] = None  # Can be int or string

    # Section 3: Market Signals
    signals: Optional[List[str]] = []
    signal_details: Optional[dict] = None
    custom_signals: Optional[List[str]] = []

    # Section 4: Audience
    segments: Optional[List[dict]] = []
    personas: Optional[List[dict]] = []
    job_titles: Optional[List[str]] = []

    # Section 5: Process
    outbound_tools: Optional[List[str]] = []
    outbound_tools_other: Optional[str] = None
    crm: Optional[str] = None
    lead_sources: Optional[List[str]] = []
    other_channels: Optional[List[str]] = []

    # Section 6: Messaging
    customer_voice: Optional[str] = None
    roi_results: Optional[str] = None
    case_studies_description: Optional[str] = None
    case_studies: Optional[List[dict]] = []
    tone_style: Optional[str] = None
    messaging_notes: Optional[str] = None
    key_differentiators: Optional[List[str]] = []
    competitors: Optional[List[str]] = []

    # Section 7: Goals
    primary_gtm_objective: Optional[str] = None
    primary_gtm_objective_other: Optional[str] = None
    success_metrics: Optional[List[str]] = []
    success_definition: Optional[str] = None
    timeline_urgency: Optional[str] = None
    monthly_budget: Optional[str] = None

    class Config:
        extra = "allow"  # Allow extra fields from form


class SubmissionResponse(BaseModel):
    success: bool
    submission_id: Optional[str] = None
    message: Optional[str] = None


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/onboarding/submit", response_model=SubmissionResponse)
async def submit_onboarding(submission: OnboardingSubmission):
    """
    Handle onboarding form submission.

    Stores the submission in:
    - client_onboarding_submissions (main data)
    - client_segments (segment array)
    - client_personas (persona array)
    """
    session = None

    try:
        session = get_db_session()
        submission_id = str(uuid4())

        # Resolve client_id
        client_id = submission.client_id

        # If no client_id provided, try to find/create by company_name
        if not client_id and submission.company_name:
            result = session.execute(
                text("SELECT id FROM clients WHERE name = :name LIMIT 1"),
                {"name": submission.company_name}
            )
            row = result.fetchone()
            if row:
                client_id = str(row[0])
            else:
                # Create new client
                client_id = str(uuid4())
                session.execute(
                    text("""
                        INSERT INTO clients (id, name, created_at)
                        VALUES (:id, :name, NOW())
                    """),
                    {"id": client_id, "name": submission.company_name}
                )
                logger.info(f"Created new client: {submission.company_name} ({client_id})")

        if not client_id:
            raise HTTPException(
                status_code=400,
                detail="Either client_id or company_name is required"
            )

        # Normalize self_serve_pct
        self_serve_pct = None
        if submission.self_serve_pct is not None:
            if isinstance(submission.self_serve_pct, int):
                self_serve_pct = str(submission.self_serve_pct)
            else:
                self_serve_pct = submission.self_serve_pct

        # Insert main submission
        session.execute(
            text("""
                INSERT INTO client_onboarding_submissions (
                    id, client_id, submission_version,
                    company_name, website, contact_name, contact_email,
                    employee_count, funding_stage, hq_location,
                    core_product, target_customer, annual_revenue, acv,
                    sales_cycle_length, self_serve_pct,
                    signals, signal_details, job_titles,
                    outbound_tools, outbound_tools_other, crm, lead_sources,
                    customer_voice, roi_results, case_studies_description,
                    case_studies, tone_style, messaging_notes,
                    primary_gtm_objective, primary_gtm_objective_other,
                    success_metrics, success_definition, timeline_urgency, monthly_budget,
                    submission_status, submitted_at, created_at
                ) VALUES (
                    :id, :client_id, 1,
                    :company_name, :website, :contact_name, :contact_email,
                    :employee_count, :funding_stage, :hq_location,
                    :core_product, :target_customer, :annual_revenue, :acv,
                    :sales_cycle_length, :self_serve_pct,
                    :signals, :signal_details, :job_titles,
                    :outbound_tools, :outbound_tools_other, :crm, :lead_sources,
                    :customer_voice, :roi_results, :case_studies_description,
                    :case_studies, :tone_style, :messaging_notes,
                    :primary_gtm_objective, :primary_gtm_objective_other,
                    :success_metrics, :success_definition, :timeline_urgency, :monthly_budget,
                    'submitted', NOW(), NOW()
                )
            """),
            {
                "id": submission_id,
                "client_id": client_id,
                "company_name": submission.company_name,
                "website": submission.website,
                "contact_name": submission.contact_name,
                "contact_email": submission.contact_email,
                "employee_count": submission.employee_count,
                "funding_stage": submission.funding_stage,
                "hq_location": submission.hq_location,
                "core_product": submission.core_product,
                "target_customer": submission.target_customer,
                "annual_revenue": submission.annual_revenue,
                "acv": submission.acv,
                "sales_cycle_length": submission.sales_cycle_length,
                "self_serve_pct": self_serve_pct,
                "signals": submission.signals or [],
                "signal_details": json.dumps(submission.signal_details) if submission.signal_details else None,
                "job_titles": submission.job_titles or [],
                "outbound_tools": submission.outbound_tools or [],
                "outbound_tools_other": submission.outbound_tools_other,
                "crm": submission.crm,
                "lead_sources": submission.lead_sources or [],
                "customer_voice": submission.customer_voice,
                "roi_results": submission.roi_results,
                "case_studies_description": submission.case_studies_description,
                "case_studies": json.dumps(submission.case_studies) if submission.case_studies else None,
                "tone_style": submission.tone_style,
                "messaging_notes": submission.messaging_notes,
                "primary_gtm_objective": submission.primary_gtm_objective,
                "primary_gtm_objective_other": submission.primary_gtm_objective_other,
                "success_metrics": submission.success_metrics or [],
                "success_definition": submission.success_definition,
                "timeline_urgency": submission.timeline_urgency,
                "monthly_budget": submission.monthly_budget,
            }
        )

        # Insert segments
        segments = submission.segments or []
        for idx, seg in enumerate(segments):
            if not seg.get('name') and not seg.get('segment_name'):
                continue

            session.execute(
                text("""
                    INSERT INTO client_segments (
                        id, submission_id, segment_order,
                        segment_name, revenue_percentage, unique_characteristics,
                        pain_points, buying_triggers, created_at
                    ) VALUES (
                        :id, :submission_id, :segment_order,
                        :segment_name, :revenue_percentage, :unique_characteristics,
                        :pain_points, :buying_triggers, NOW()
                    )
                """),
                {
                    "id": str(uuid4()),
                    "submission_id": submission_id,
                    "segment_order": idx,
                    "segment_name": seg.get('name') or seg.get('segment_name', ''),
                    "revenue_percentage": seg.get('revenue_pct') or seg.get('revenue_percentage'),
                    "unique_characteristics": seg.get('unique_characteristics'),
                    "pain_points": seg.get('pain_points'),
                    "buying_triggers": seg.get('buying_triggers'),
                }
            )

        # Insert personas
        personas = submission.personas or []
        for idx, persona in enumerate(personas):
            if not persona.get('job_title'):
                continue

            session.execute(
                text("""
                    INSERT INTO client_personas (
                        id, submission_id, persona_order,
                        job_title, primary_segment, seniority_level,
                        pain_before_buying, aha_moment, objections,
                        decision_criteria, created_at
                    ) VALUES (
                        :id, :submission_id, :persona_order,
                        :job_title, :primary_segment, :seniority_level,
                        :pain_before_buying, :aha_moment, :objections,
                        :decision_criteria, NOW()
                    )
                """),
                {
                    "id": str(uuid4()),
                    "submission_id": submission_id,
                    "persona_order": idx,
                    "job_title": persona.get('job_title', ''),
                    "primary_segment": persona.get('primary_segment'),
                    "seniority_level": persona.get('seniority_level'),
                    "pain_before_buying": persona.get('pain_before_buying'),
                    "aha_moment": persona.get('aha_moment'),
                    "objections": persona.get('objections'),
                    "decision_criteria": persona.get('decision_criteria'),
                }
            )

        session.commit()

        logger.info(f"Onboarding submission saved: {submission_id} for client {client_id}")

        return SubmissionResponse(
            success=True,
            submission_id=submission_id,
            message="Onboarding form submitted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving submission: {e}")
        if session:
            session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if session:
            session.close()


@app.get("/onboarding/{submission_id}")
async def get_submission(submission_id: str):
    """Retrieve a submission by ID."""
    session = None

    try:
        session = get_db_session()

        # Get main submission
        result = session.execute(
            text("""
                SELECT * FROM client_onboarding_submissions
                WHERE id = :id
            """),
            {"id": submission_id}
        )
        row = result.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Convert to dict
        columns = result.keys()
        submission = dict(zip(columns, row))

        # Get segments
        seg_result = session.execute(
            text("""
                SELECT * FROM client_segments
                WHERE submission_id = :id
                ORDER BY segment_order
            """),
            {"id": submission_id}
        )
        seg_columns = seg_result.keys()
        submission['segments'] = [dict(zip(seg_columns, r)) for r in seg_result.fetchall()]

        # Get personas
        persona_result = session.execute(
            text("""
                SELECT * FROM client_personas
                WHERE submission_id = :id
                ORDER BY persona_order
            """),
            {"id": submission_id}
        )
        persona_columns = persona_result.keys()
        submission['personas'] = [dict(zip(persona_columns, r)) for r in persona_result.fetchall()]

        return submission

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving submission: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if session:
            session.close()


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
