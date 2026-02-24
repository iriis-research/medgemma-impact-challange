"""
Symptom Journal API Routes
Includes AI-powered health assessment
"""

from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
import logging

from app.db.database import get_db
from app.db.models import User, SymptomEntry
from app.security.auth import get_current_user
from app.llm.medgemma_client import medgemma

router = APIRouter()
logger = logging.getLogger(__name__)

# Request/Response Models
class SymptomCreate(BaseModel):
    symptom: str
    severity: int  # 1-10
    description: Optional[str] = None
    triggers: Optional[str] = None
    duration: Optional[str] = None

class SymptomUpdate(BaseModel):
    symptom: Optional[str] = None
    severity: Optional[int] = None
    description: Optional[str] = None
    triggers: Optional[str] = None
    duration: Optional[str] = None

class SymptomResponse(BaseModel):
    id: int
    symptom: str
    severity: int
    description: Optional[str]
    triggers: Optional[str]
    duration: Optional[str]
    recorded_at: datetime
    
    class Config:
        from_attributes = True

class SymptomAssessment(BaseModel):
    response: str
    is_emergency: bool
    recommendation: str

class HealthCheckResponse(BaseModel):
    assessment: str
    risk_level: str
    average_severity: float
    max_severity: int
    symptom_count: int
    disclaimer: str

class SymptomSummary(BaseModel):
    period: str
    total_entries: int
    symptoms: List[dict]
    severity_trend: str
    doctor_summary: str

class SymptomTimeline(BaseModel):
    date: date
    entries: List[SymptomResponse]


@router.post("/", response_model=SymptomResponse)
@router.post("", response_model=SymptomResponse, include_in_schema=False)
async def log_symptom(
    symptom_data: SymptomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log a new symptom entry."""
    if not 1 <= symptom_data.severity <= 10:
        raise HTTPException(status_code=400, detail="Severity must be between 1 and 10")
    
    entry = SymptomEntry(
        user_id=current_user.id,
        symptom=symptom_data.symptom,
        severity=symptom_data.severity,
        description=symptom_data.description,
        triggers=symptom_data.triggers,
        duration=symptom_data.duration
    )
    
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    
    logger.info(f"📝 Symptom logged: {symptom_data.symptom} (severity: {symptom_data.severity})")
    
    return entry


@router.get("/", response_model=List[SymptomResponse])
@router.get("", response_model=List[SymptomResponse], include_in_schema=False)
async def get_symptoms(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get symptom entries for the specified period."""
    since = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(SymptomEntry)
        .where(SymptomEntry.user_id == current_user.id)
        .where(SymptomEntry.recorded_at >= since)
        .order_by(SymptomEntry.recorded_at.desc())
    )
    
    return result.scalars().all()


@router.get("/timeline", response_model=List[SymptomTimeline])
async def get_symptom_timeline(
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get symptom timeline grouped by date."""
    since = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(SymptomEntry)
        .where(SymptomEntry.user_id == current_user.id)
        .where(SymptomEntry.recorded_at >= since)
        .order_by(SymptomEntry.recorded_at.desc())
    )
    entries = result.scalars().all()
    
    # Group by date
    timeline = {}
    for entry in entries:
        entry_date = entry.recorded_at.date()
        if entry_date not in timeline:
            timeline[entry_date] = []
        timeline[entry_date].append(SymptomResponse(
            id=entry.id,
            symptom=entry.symptom,
            severity=entry.severity,
            description=entry.description,
            triggers=entry.triggers,
            duration=entry.duration,
            recorded_at=entry.recorded_at
        ))
    
    return [
        SymptomTimeline(date=d, entries=entries)
        for d, entries in sorted(timeline.items(), reverse=True)
    ]


@router.get("/summary", response_model=SymptomSummary)
async def get_symptom_summary(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a summary of symptoms for doctor visits."""
    since = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(SymptomEntry)
        .where(SymptomEntry.user_id == current_user.id)
        .where(SymptomEntry.recorded_at >= since)
        .order_by(SymptomEntry.recorded_at)
    )
    entries = list(result.scalars().all())
    
    if not entries:
        return SymptomSummary(
            period=f"Last {days} days",
            total_entries=0,
            symptoms=[],
            severity_trend="No data",
            doctor_summary="No symptoms recorded in this period."
        )
    
    # Aggregate symptoms
    symptom_stats = {}
    for entry in entries:
        if entry.symptom not in symptom_stats:
            symptom_stats[entry.symptom] = {
                "name": entry.symptom,
                "occurrences": 0,
                "severities": [],
                "triggers": []
            }
        symptom_stats[entry.symptom]["occurrences"] += 1
        symptom_stats[entry.symptom]["severities"].append(entry.severity)
        if entry.triggers:
            symptom_stats[entry.symptom]["triggers"].append(entry.triggers)
    
    # Calculate averages and format
    symptoms_list = []
    for symptom, stats in symptom_stats.items():
        avg_severity = sum(stats["severities"]) / len(stats["severities"])
        symptoms_list.append({
            "name": symptom,
            "occurrences": stats["occurrences"],
            "average_severity": round(avg_severity, 1),
            "max_severity": max(stats["severities"]),
            "common_triggers": list(set(stats["triggers"]))[:3]
        })
    
    # Sort by occurrences
    symptoms_list.sort(key=lambda x: x["occurrences"], reverse=True)
    
    # Calculate overall trend
    if len(entries) >= 2:
        first_half = entries[:len(entries)//2]
        second_half = entries[len(entries)//2:]
        avg_first = sum(e.severity for e in first_half) / len(first_half)
        avg_second = sum(e.severity for e in second_half) / len(second_half)
        
        if avg_second > avg_first + 1:
            trend = "Worsening"
        elif avg_second < avg_first - 1:
            trend = "Improving"
        else:
            trend = "Stable"
    else:
        trend = "Insufficient data"
    
    # Generate doctor summary
    doctor_summary = generate_doctor_summary(symptoms_list, days, len(entries), trend)
    
    return SymptomSummary(
        period=f"Last {days} days",
        total_entries=len(entries),
        symptoms=symptoms_list,
        severity_trend=trend,
        doctor_summary=doctor_summary
    )


def generate_doctor_summary(symptoms: List[dict], days: int, total: int, trend: str) -> str:
    """Generate a summary suitable for sharing with a doctor."""
    if not symptoms:
        return "No symptoms recorded during this period."
    
    summary_parts = [f"**Symptom Summary ({days} days, {total} entries)**\n"]
    
    for s in symptoms[:5]:  # Top 5 symptoms
        triggers_str = ", ".join(s["common_triggers"]) if s["common_triggers"] else "not identified"
        summary_parts.append(
            f"• **{s['name']}**: {s['occurrences']} occurrences, "
            f"avg severity {s['average_severity']}/10 (max: {s['max_severity']}), "
            f"triggers: {triggers_str}"
        )
    
    summary_parts.append(f"\n**Overall trend**: {trend}")
    
    return "\n".join(summary_parts)


@router.post("/assess", response_model=SymptomAssessment)
async def assess_symptoms(
    symptom_data: SymptomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get AI assessment of symptoms (educational only)."""
    logger.info(f"🤖 Assessing symptoms: {symptom_data.symptom}")
    
    assessment = await medgemma.assess_symptoms(
        symptoms=symptom_data.symptom + (f"\n{symptom_data.description}" if symptom_data.description else ""),
        duration=symptom_data.duration or "Not specified",
        severity=symptom_data.severity
    )
    
    return SymptomAssessment(
        response=assessment["response"],
        is_emergency=assessment["is_emergency"],
        recommendation=assessment.get("recommendation", "Please consult your healthcare provider.")
    )


@router.get("/health-check", response_model=HealthCheckResponse)
async def get_health_check(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get AI-powered health assessment based on symptom patterns."""
    since = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(SymptomEntry)
        .where(SymptomEntry.user_id == current_user.id)
        .where(SymptomEntry.recorded_at >= since)
        .order_by(SymptomEntry.recorded_at.desc())
    )
    entries = list(result.scalars().all())
    
    if not entries:
        return HealthCheckResponse(
            assessment="No symptoms have been recorded in the past {days} days. Keep tracking your symptoms to get personalized health insights!",
            risk_level="unknown",
            average_severity=0,
            max_severity=0,
            symptom_count=0,
            disclaimer="Start logging symptoms to receive AI-powered health assessments."
        )
    
    # Format symptoms for AI analysis
    symptoms_data = [
        {
            "symptom": e.symptom,
            "severity": e.severity,
            "duration": e.duration,
            "triggers": e.triggers,
            "recorded_at": e.recorded_at.isoformat()
        }
        for e in entries
    ]
    
    logger.info(f"🤖 Running health check on {len(symptoms_data)} symptoms")
    
    # Get AI assessment
    result = await medgemma.check_symptom_health(symptoms_data, days)
    
    return HealthCheckResponse(
        assessment=result["assessment"],
        risk_level=result["risk_level"],
        average_severity=result["average_severity"],
        max_severity=result["max_severity"],
        symptom_count=result["symptom_count"],
        disclaimer=result["disclaimer"]
    )


@router.get("/{symptom_id}", response_model=SymptomResponse)
async def get_symptom(
    symptom_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific symptom entry."""
    result = await db.execute(
        select(SymptomEntry)
        .where(SymptomEntry.id == symptom_id)
        .where(SymptomEntry.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Symptom entry not found")
    
    return entry


@router.put("/{symptom_id}", response_model=SymptomResponse)
async def update_symptom(
    symptom_id: int,
    symptom_data: SymptomUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a symptom entry."""
    result = await db.execute(
        select(SymptomEntry)
        .where(SymptomEntry.id == symptom_id)
        .where(SymptomEntry.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Symptom entry not found")
    
    update_data = symptom_data.model_dump(exclude_unset=True)
    
    if "severity" in update_data and not 1 <= update_data["severity"] <= 10:
        raise HTTPException(status_code=400, detail="Severity must be between 1 and 10")
    
    for field, value in update_data.items():
        setattr(entry, field, value)
    
    await db.commit()
    await db.refresh(entry)
    
    return entry


@router.delete("/{symptom_id}")
async def delete_symptom(
    symptom_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a symptom entry."""
    result = await db.execute(
        select(SymptomEntry)
        .where(SymptomEntry.id == symptom_id)
        .where(SymptomEntry.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Symptom entry not found")
    
    await db.delete(entry)
    await db.commit()
    
    return {"message": "Symptom entry deleted successfully"}
