"""
Health Dashboard API Routes
Provides comprehensive health summaries and insights
"""

from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging

from app.db.database import get_db
from app.db.models import User, Medication, SymptomEntry, MedicalReport, Conversation, Message
from app.security.auth import get_current_user
from app.llm.medgemma_client import medgemma

router = APIRouter()
logger = logging.getLogger(__name__)


# Response Models
class HealthOverview(BaseModel):
    active_medications: int
    recent_symptoms: int
    medical_reports: int
    recent_conversations: int

class MedicationBrief(BaseModel):
    id: int
    name: str
    dosage: str
    purpose: Optional[str]

class SymptomBrief(BaseModel):
    id: int
    symptom: str
    severity: int
    recorded_at: datetime

class ReportBrief(BaseModel):
    id: int
    filename: str
    report_type: Optional[str]
    has_summary: bool
    uploaded_at: datetime

class HealthSummaryResponse(BaseModel):
    summary: str
    overview: HealthOverview
    medications: List[MedicationBrief]
    recent_symptoms: List[SymptomBrief]
    reports: List[ReportBrief]
    generated_at: datetime
    disclaimer: str

class QuickStatsResponse(BaseModel):
    overview: HealthOverview
    symptom_trend: str
    medication_adherence: Optional[float]
    last_report_date: Optional[datetime]


@router.get("/stats", response_model=QuickStatsResponse)
@router.get("/stats/", response_model=QuickStatsResponse, include_in_schema=False)
async def get_quick_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get quick health statistics for the dashboard."""
    # Get counts
    meds_result = await db.execute(
        select(Medication)
        .where(Medication.user_id == current_user.id)
        .where(Medication.is_active == True)
    )
    medications = list(meds_result.scalars().all())
    
    since_30_days = datetime.utcnow() - timedelta(days=30)
    
    symptoms_result = await db.execute(
        select(SymptomEntry)
        .where(SymptomEntry.user_id == current_user.id)
        .where(SymptomEntry.recorded_at >= since_30_days)
        .order_by(SymptomEntry.recorded_at.desc())
    )
    symptoms = list(symptoms_result.scalars().all())
    
    reports_result = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.user_id == current_user.id)
        .order_by(MedicalReport.uploaded_at.desc())
    )
    reports = list(reports_result.scalars().all())
    
    convos_result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .where(Conversation.updated_at >= since_30_days)
    )
    conversations = list(convos_result.scalars().all())
    
    # Calculate symptom trend
    if len(symptoms) >= 2:
        first_half = symptoms[len(symptoms)//2:]
        second_half = symptoms[:len(symptoms)//2]
        avg_first = sum(s.severity for s in first_half) / len(first_half) if first_half else 0
        avg_second = sum(s.severity for s in second_half) / len(second_half) if second_half else 0
        
        if avg_second > avg_first + 1:
            trend = "worsening"
        elif avg_second < avg_first - 1:
            trend = "improving"
        else:
            trend = "stable"
    elif symptoms:
        trend = "insufficient_data"
    else:
        trend = "no_data"
    
    return QuickStatsResponse(
        overview=HealthOverview(
            active_medications=len(medications),
            recent_symptoms=len(symptoms),
            medical_reports=len(reports),
            recent_conversations=len(conversations)
        ),
        symptom_trend=trend,
        medication_adherence=None,  # TODO: Calculate from logs
        last_report_date=reports[0].uploaded_at if reports else None
    )


@router.get("/health-summary", response_model=HealthSummaryResponse)
@router.get("/health-summary/", response_model=HealthSummaryResponse, include_in_schema=False)
async def get_health_summary(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive AI-generated health summary."""
    since = datetime.utcnow() - timedelta(days=days)
    
    logger.info(f"📊 Generating health summary for user {current_user.id}")
    
    # Fetch all user data
    meds_result = await db.execute(
        select(Medication)
        .where(Medication.user_id == current_user.id)
        .where(Medication.is_active == True)
    )
    medications = list(meds_result.scalars().all())
    
    symptoms_result = await db.execute(
        select(SymptomEntry)
        .where(SymptomEntry.user_id == current_user.id)
        .where(SymptomEntry.recorded_at >= since)
        .order_by(SymptomEntry.recorded_at.desc())
    )
    symptoms = list(symptoms_result.scalars().all())
    
    reports_result = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.user_id == current_user.id)
        .order_by(MedicalReport.uploaded_at.desc())
        .limit(10)
    )
    reports = list(reports_result.scalars().all())
    
    # Get recent conversation queries (user messages only)
    messages_result = await db.execute(
        select(Message)
        .join(Conversation)
        .where(Conversation.user_id == current_user.id)
        .where(Message.role == "user")
        .where(Message.created_at >= since)
        .order_by(Message.created_at.desc())
        .limit(20)
    )
    recent_queries = [m.content for m in messages_result.scalars().all()]
    
    # Prepare data for AI summary
    user_data = {
        "medications": [
            {
                "name": m.name,
                "dosage": m.dosage,
                "purpose": m.purpose,
                "frequency": m.frequency
            }
            for m in medications
        ],
        "symptoms": [
            {
                "symptom": s.symptom,
                "severity": s.severity,
                "duration": s.duration,
                "recorded_at": s.recorded_at.isoformat()
            }
            for s in symptoms[:20]  # Last 20 symptoms
        ],
        "reports": [
            {
                "filename": r.filename,
                "report_type": r.report_type,
                "summary": r.summary[:200] if r.summary else None
            }
            for r in reports[:5]  # Last 5 reports
        ],
        "recent_queries": recent_queries[:10]
    }
    
    # Generate AI summary
    logger.info("🤖 Calling MedGemma for health summary generation")
    ai_result = await medgemma.generate_health_summary(user_data)
    
    return HealthSummaryResponse(
        summary=ai_result["summary"],
        overview=HealthOverview(
            active_medications=len(medications),
            recent_symptoms=len(symptoms),
            medical_reports=len(reports),
            recent_conversations=len(recent_queries)
        ),
        medications=[
            MedicationBrief(
                id=m.id,
                name=m.name,
                dosage=m.dosage,
                purpose=m.purpose
            )
            for m in medications[:5]
        ],
        recent_symptoms=[
            SymptomBrief(
                id=s.id,
                symptom=s.symptom,
                severity=s.severity,
                recorded_at=s.recorded_at
            )
            for s in symptoms[:5]
        ],
        reports=[
            ReportBrief(
                id=r.id,
                filename=r.filename,
                report_type=r.report_type,
                has_summary=r.summary is not None,
                uploaded_at=r.uploaded_at
            )
            for r in reports[:5]
        ],
        generated_at=datetime.utcnow(),
        disclaimer=ai_result["disclaimer"]
    )


@router.get("/recent-activity")
@router.get("/recent-activity/", include_in_schema=False)
async def get_recent_activity(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent health-related activity."""
    activities = []
    
    # Recent symptoms
    symptoms_result = await db.execute(
        select(SymptomEntry)
        .where(SymptomEntry.user_id == current_user.id)
        .order_by(SymptomEntry.recorded_at.desc())
        .limit(5)
    )
    for s in symptoms_result.scalars().all():
        activities.append({
            "type": "symptom",
            "title": f"Logged symptom: {s.symptom}",
            "detail": f"Severity: {s.severity}/10",
            "timestamp": s.recorded_at.isoformat(),
            "id": s.id
        })
    
    # Recent reports
    reports_result = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.user_id == current_user.id)
        .order_by(MedicalReport.uploaded_at.desc())
        .limit(5)
    )
    for r in reports_result.scalars().all():
        activities.append({
            "type": "report",
            "title": f"Uploaded: {r.filename}",
            "detail": r.report_type or "Medical document",
            "timestamp": r.uploaded_at.isoformat(),
            "id": r.id
        })
    
    # Recent conversations
    convos_result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(5)
    )
    for c in convos_result.scalars().all():
        activities.append({
            "type": "conversation",
            "title": c.title or "Health conversation",
            "detail": "AI chat session",
            "timestamp": c.updated_at.isoformat(),
            "id": c.id
        })
    
    # Sort by timestamp and limit
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return {"activities": activities[:limit]}
