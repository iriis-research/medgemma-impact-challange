"""
Medications API Routes
Includes AI-powered medication summaries and explanations
"""

from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
import logging

from app.db.database import get_db
from app.db.models import User, Medication, MedicationLog, SideEffect
from app.security.auth import get_current_user
from app.llm.medgemma_client import medgemma

router = APIRouter()
logger = logging.getLogger(__name__)

# Request/Response Models
class MedicationCreate(BaseModel):
    name: str
    dosage: str
    frequency: str
    purpose: Optional[str] = None
    instructions: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    reminder_times: List[str] = []  # ["08:00", "20:00"]

class MedicationUpdate(BaseModel):
    name: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    purpose: Optional[str] = None
    instructions: Optional[str] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    reminder_times: Optional[List[str]] = None

class MedicationResponse(BaseModel):
    id: int
    name: str
    dosage: str
    frequency: str
    purpose: Optional[str]
    instructions: Optional[str]
    start_date: datetime
    end_date: Optional[datetime]
    is_active: bool
    reminder_times: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class MedicationLogCreate(BaseModel):
    medication_id: int
    scheduled_time: datetime
    was_taken: bool = True
    notes: Optional[str] = None

class MedicationLogResponse(BaseModel):
    id: int
    medication_id: int
    taken_at: datetime
    scheduled_time: datetime
    was_taken: bool
    notes: Optional[str]
    
    class Config:
        from_attributes = True

class SideEffectCreate(BaseModel):
    medication_id: int
    description: str
    severity: int  # 1-5

class SideEffectResponse(BaseModel):
    id: int
    medication_id: int
    description: str
    severity: int
    reported_at: datetime
    
    class Config:
        from_attributes = True

class MedicationExplanation(BaseModel):
    explanation: str
    reminder: str

class MedicationSummaryResponse(BaseModel):
    summary: str
    medication_count: int
    disclaimer: str

class DailyChecklist(BaseModel):
    date: date
    medications: List[dict]


def strip_timezone(dt: datetime) -> datetime:
    """Convert timezone-aware datetime to naive UTC datetime."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


@router.post("/", response_model=MedicationResponse)
@router.post("", response_model=MedicationResponse, include_in_schema=False)
async def create_medication(
    med_data: MedicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new medication to track."""
    medication = Medication(
        user_id=current_user.id,
        name=med_data.name,
        dosage=med_data.dosage,
        frequency=med_data.frequency,
        purpose=med_data.purpose,
        instructions=med_data.instructions,
        start_date=strip_timezone(med_data.start_date),
        end_date=strip_timezone(med_data.end_date),
        reminder_times=med_data.reminder_times
    )
    
    db.add(medication)
    await db.commit()
    await db.refresh(medication)
    
    logger.info(f"💊 Medication added: {med_data.name}")
    
    return medication


@router.get("/", response_model=List[MedicationResponse])
@router.get("", response_model=List[MedicationResponse], include_in_schema=False)
async def get_medications(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all medications for current user."""
    query = select(Medication).where(Medication.user_id == current_user.id)
    if active_only:
        query = query.where(Medication.is_active == True)
    query = query.order_by(Medication.created_at.desc())
    
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/summary", response_model=MedicationSummaryResponse)
async def get_medication_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get AI-powered summary of all active medications."""
    # Get active medications
    result = await db.execute(
        select(Medication)
        .where(Medication.user_id == current_user.id)
        .where(Medication.is_active == True)
    )
    medications = result.scalars().all()
    
    if not medications:
        return MedicationSummaryResponse(
            summary="You don't have any active medications tracked. Add your medications to get helpful summaries and reminders!",
            medication_count=0,
            disclaimer="Add your medications to receive AI-powered medication management tips."
        )
    
    # Format medications for AI
    meds_data = [
        {
            "name": m.name,
            "dosage": m.dosage,
            "frequency": m.frequency,
            "purpose": m.purpose
        }
        for m in medications
    ]
    
    logger.info(f"🤖 Generating medication summary for {len(meds_data)} medications")
    
    # Get AI summary
    result = await medgemma.summarize_medications(meds_data)
    
    return MedicationSummaryResponse(
        summary=result["summary"],
        medication_count=result["medication_count"],
        disclaimer=result["disclaimer"]
    )


@router.get("/checklist", response_model=DailyChecklist)
async def get_daily_checklist(
    target_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get daily medication checklist."""
    if not target_date:
        target_date = date.today()
    
    # Get active medications
    result = await db.execute(
        select(Medication)
        .where(Medication.user_id == current_user.id)
        .where(Medication.is_active == True)
    )
    medications = result.scalars().all()
    
    checklist = []
    for med in medications:
        # Get logs for this date
        start_of_day = datetime.combine(target_date, datetime.min.time())
        end_of_day = datetime.combine(target_date, datetime.max.time())
        
        log_result = await db.execute(
            select(MedicationLog)
            .where(MedicationLog.medication_id == med.id)
            .where(MedicationLog.scheduled_time >= start_of_day)
            .where(MedicationLog.scheduled_time <= end_of_day)
        )
        logs = {log.scheduled_time.strftime("%H:%M"): log for log in log_result.scalars().all()}
        
        # Build schedule with status
        schedule = []
        for time_str in med.reminder_times or []:
            schedule.append({
                "time": time_str,
                "taken": time_str in logs,
                "log_id": logs.get(time_str).id if time_str in logs else None
            })
        
        checklist.append({
            "medication_id": med.id,
            "name": med.name,
            "dosage": med.dosage,
            "instructions": med.instructions,
            "schedule": schedule
        })
    
    return DailyChecklist(date=target_date, medications=checklist)


@router.get("/{medication_id}", response_model=MedicationResponse)
async def get_medication(
    medication_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific medication."""
    result = await db.execute(
        select(Medication)
        .where(Medication.id == medication_id)
        .where(Medication.user_id == current_user.id)
    )
    medication = result.scalar_one_or_none()
    
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    return medication


@router.put("/{medication_id}", response_model=MedicationResponse)
async def update_medication(
    medication_id: int,
    med_data: MedicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a medication."""
    result = await db.execute(
        select(Medication)
        .where(Medication.id == medication_id)
        .where(Medication.user_id == current_user.id)
    )
    medication = result.scalar_one_or_none()
    
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    update_data = med_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(medication, field, value)
    
    await db.commit()
    await db.refresh(medication)
    
    return medication


@router.post("/{medication_id}/explain", response_model=MedicationExplanation)
async def explain_medication(
    medication_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get AI explanation of a medication."""
    result = await db.execute(
        select(Medication)
        .where(Medication.id == medication_id)
        .where(Medication.user_id == current_user.id)
    )
    medication = result.scalar_one_or_none()
    
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    logger.info(f"🤖 Explaining medication: {medication.name}")
    
    explanation = await medgemma.explain_medication(
        medication.name,
        medication.dosage,
        medication.purpose
    )
    
    return MedicationExplanation(
        explanation=explanation["explanation"],
        reminder=explanation["reminder"]
    )


@router.post("/log", response_model=MedicationLogResponse)
async def log_medication(
    log_data: MedicationLogCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log a medication as taken or missed."""
    # Verify medication belongs to user
    result = await db.execute(
        select(Medication)
        .where(Medication.id == log_data.medication_id)
        .where(Medication.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Medication not found")
    
    log = MedicationLog(
        medication_id=log_data.medication_id,
        scheduled_time=log_data.scheduled_time,
        was_taken=log_data.was_taken,
        notes=log_data.notes
    )
    
    db.add(log)
    await db.commit()
    await db.refresh(log)
    
    return log


@router.get("/{medication_id}/logs", response_model=List[MedicationLogResponse])
async def get_medication_logs(
    medication_id: int,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get medication logs for a specific medication."""
    # Verify medication belongs to user
    result = await db.execute(
        select(Medication)
        .where(Medication.id == medication_id)
        .where(Medication.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Medication not found")
    
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(MedicationLog)
        .where(MedicationLog.medication_id == medication_id)
        .where(MedicationLog.taken_at >= since)
        .order_by(MedicationLog.taken_at.desc())
    )
    
    return result.scalars().all()


@router.post("/side-effects", response_model=SideEffectResponse)
async def report_side_effect(
    effect_data: SideEffectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Report a medication side effect."""
    # Verify medication belongs to user
    result = await db.execute(
        select(Medication)
        .where(Medication.id == effect_data.medication_id)
        .where(Medication.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Medication not found")
    
    if not 1 <= effect_data.severity <= 5:
        raise HTTPException(status_code=400, detail="Severity must be between 1 and 5")
    
    side_effect = SideEffect(
        medication_id=effect_data.medication_id,
        description=effect_data.description,
        severity=effect_data.severity
    )
    
    db.add(side_effect)
    await db.commit()
    await db.refresh(side_effect)
    
    return side_effect


@router.get("/{medication_id}/side-effects", response_model=List[SideEffectResponse])
async def get_side_effects(
    medication_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get reported side effects for a medication."""
    # Verify medication belongs to user
    result = await db.execute(
        select(Medication)
        .where(Medication.id == medication_id)
        .where(Medication.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Medication not found")
    
    result = await db.execute(
        select(SideEffect)
        .where(SideEffect.medication_id == medication_id)
        .order_by(SideEffect.reported_at.desc())
    )
    
    return result.scalars().all()


@router.delete("/{medication_id}")
async def delete_medication(
    medication_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a medication."""
    result = await db.execute(
        select(Medication)
        .where(Medication.id == medication_id)
        .where(Medication.user_id == current_user.id)
    )
    medication = result.scalar_one_or_none()
    
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    
    await db.delete(medication)
    await db.commit()
    
    return {"message": "Medication deleted successfully"}
