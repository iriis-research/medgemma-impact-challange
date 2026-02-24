"""
Database Models for NidanMitra
"""

from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Integer, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base
import enum


def utc_now() -> datetime:
    """Return current UTC time without timezone info (for PostgreSQL TIMESTAMP WITHOUT TIME ZONE)."""
    return datetime.utcnow()

class MessageCategory(str, enum.Enum):
    SYMPTOM = "symptom"
    MEDICATION = "medication"
    GENERAL = "general"
    REPORT = "report"
    EMERGENCY = "emergency"

class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(10), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reports: Mapped[list["MedicalReport"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    medications: Mapped[list["Medication"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    symptoms: Mapped[list["SymptomEntry"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"))
    role: Mapped[str] = mapped_column(String(20))  # user, assistant
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[MessageCategory] = mapped_column(Enum(MessageCategory), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    
    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

class MedicalReport(Base):
    __tablename__ = "medical_reports"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    report_type: Mapped[str] = mapped_column(String(100), nullable=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), nullable=True)
    extracted_data: Mapped[dict] = mapped_column(JSON, nullable=True)  # diagnoses, lab values, medications
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="reports")

class Medication(Base):
    __tablename__ = "medications"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    dosage: Mapped[str] = mapped_column(String(100))
    frequency: Mapped[str] = mapped_column(String(100))
    purpose: Mapped[str] = mapped_column(Text, nullable=True)
    instructions: Mapped[str] = mapped_column(Text, nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_times: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="medications")
    logs: Mapped[list["MedicationLog"]] = relationship(back_populates="medication", cascade="all, delete-orphan")
    side_effects: Mapped[list["SideEffect"]] = relationship(back_populates="medication", cascade="all, delete-orphan")

class MedicationLog(Base):
    __tablename__ = "medication_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    medication_id: Mapped[int] = mapped_column(ForeignKey("medications.id"))
    taken_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime)
    was_taken: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    
    # Relationships
    medication: Mapped["Medication"] = relationship(back_populates="logs")

class SideEffect(Base):
    __tablename__ = "side_effects"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    medication_id: Mapped[int] = mapped_column(ForeignKey("medications.id"))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[int] = mapped_column(Integer)  # 1-5 scale
    reported_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    
    # Relationships
    medication: Mapped["Medication"] = relationship(back_populates="side_effects")

class SymptomEntry(Base):
    __tablename__ = "symptom_entries"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    symptom: Mapped[str] = mapped_column(String(255))
    severity: Mapped[int] = mapped_column(Integer)  # 1-10 scale
    description: Mapped[str] = mapped_column(Text, nullable=True)
    triggers: Mapped[str] = mapped_column(Text, nullable=True)
    duration: Mapped[str] = mapped_column(String(100), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="symptoms")

