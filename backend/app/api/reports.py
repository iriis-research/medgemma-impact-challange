"""
Medical Reports API Routes
Supports PDF parsing, image analysis, and AI-powered summarization
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import os
import uuid
import logging

from app.db.database import get_db
from app.db.models import User, MedicalReport, RiskLevel
from app.security.auth import get_current_user
from app.llm.medgemma_client import medgemma

router = APIRouter()
logger = logging.getLogger(__name__)

# Directory for storing uploaded files
UPLOAD_DIR = "uploads/reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Request/Response Models
class ReportSummary(BaseModel):
    id: int
    filename: str
    report_type: Optional[str]
    risk_level: Optional[str]
    uploaded_at: datetime
    has_summary: bool = False
    
    class Config:
        from_attributes = True

class ReportDetail(BaseModel):
    id: int
    filename: str
    report_type: Optional[str]
    extracted_text: Optional[str]
    summary: Optional[str]
    risk_level: Optional[str]
    extracted_data: Optional[dict]
    uploaded_at: datetime
    
    class Config:
        from_attributes = True

class ReportExplainRequest(BaseModel):
    report_id: int
    specific_question: Optional[str] = None

class ReportExplanation(BaseModel):
    summary: str
    is_emergency: bool
    disclaimer: str

class ImageAnalysisResponse(BaseModel):
    analysis: str
    image_type: str
    images_analyzed: int
    disclaimer: str


async def extract_text_from_file(file_path: str, content_type: str) -> str:
    """Extract text from uploaded file (PDF or image with OCR)."""
    if content_type == "application/pdf":
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            if text.strip():
                logger.info(f"📄 Extracted {len(text)} chars from PDF")
                return text.strip()
            else:
                # PDF has no text - might be scanned, try OCR
                return await extract_text_with_ocr(file_path)
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return await extract_text_with_ocr(file_path)
    else:
        # Image file - use OCR
        return await extract_text_with_ocr(file_path)


async def extract_text_with_ocr(file_path: str) -> str:
    """Extract text from image or scanned PDF using OCR."""
    try:
        import pytesseract
        from PIL import Image
        from pdf2image import convert_from_path
        
        if file_path.lower().endswith('.pdf'):
            # Convert PDF pages to images
            images = convert_from_path(file_path, dpi=300)
            text = ""
            for i, img in enumerate(images):
                page_text = pytesseract.image_to_string(img)
                text += f"\n--- Page {i+1} ---\n{page_text}"
            logger.info(f"🔍 OCR extracted {len(text)} chars from PDF")
            return text.strip() if text.strip() else "OCR could not extract readable text from this document."
        else:
            # Direct image OCR
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            logger.info(f"🔍 OCR extracted {len(text)} chars from image")
            return text.strip() if text.strip() else "OCR could not extract readable text from this image."
    except ImportError:
        logger.warning("pytesseract or pdf2image not available for OCR")
        return "Text extraction requires OCR setup. The image will be analyzed directly by AI."
    except Exception as e:
        logger.error(f"OCR extraction error: {e}")
        return f"Text extraction encountered an error. The image will be analyzed directly by AI."


@router.post("/upload", response_model=ReportDetail)
@router.post("/upload/", response_model=ReportDetail, include_in_schema=False)
async def upload_report(
    file: UploadFile = File(...),
    report_type: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a medical report (PDF or image) and extract text."""
    # Validate file type
    allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: PDF, JPEG, PNG, WebP"
        )
    
    # Generate unique filename
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    logger.info(f"📁 Saved report: {file.filename} -> {file_path}")
    
    # Extract text
    extracted_text = await extract_text_from_file(file_path, file.content_type)
    
    # Create report record
    report = MedicalReport(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        report_type=report_type,
        extracted_text=extracted_text,
        risk_level=None,
        extracted_data={"content_type": file.content_type}
    )
    
    db.add(report)
    await db.commit()
    await db.refresh(report)
    
    logger.info(f"✅ Report uploaded: ID={report.id}")
    
    return ReportDetail(
        id=report.id,
        filename=report.filename,
        report_type=report.report_type,
        extracted_text=report.extracted_text,
        summary=report.summary,
        risk_level=report.risk_level.value if report.risk_level else None,
        extracted_data=report.extracted_data,
        uploaded_at=report.uploaded_at
    )


@router.get("/", response_model=List[ReportSummary])
@router.get("", response_model=List[ReportSummary], include_in_schema=False)
async def get_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all reports for current user."""
    result = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.user_id == current_user.id)
        .order_by(MedicalReport.uploaded_at.desc())
    )
    reports = result.scalars().all()
    
    return [
        ReportSummary(
            id=r.id,
            filename=r.filename,
            report_type=r.report_type,
            risk_level=r.risk_level.value if r.risk_level else None,
            uploaded_at=r.uploaded_at,
            has_summary=r.summary is not None
        )
        for r in reports
    ]


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific report."""
    result = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.id == report_id)
        .where(MedicalReport.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return ReportDetail(
        id=report.id,
        filename=report.filename,
        report_type=report.report_type,
        extracted_text=report.extracted_text,
        summary=report.summary,
        risk_level=report.risk_level.value if report.risk_level else None,
        extracted_data=report.extracted_data,
        uploaded_at=report.uploaded_at
    )


@router.post("/{report_id}/summarize", response_model=ReportExplanation)
async def summarize_report(
    report_id: int,
    specific_question: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate AI summary of a report using MedGemma."""
    result = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.id == report_id)
        .where(MedicalReport.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    logger.info(f"🤖 Generating AI summary for report {report_id}")
    
    # Determine if we should use image analysis
    is_image = report.extracted_data and report.extracted_data.get("content_type", "").startswith("image/")
    
    if is_image and os.path.exists(report.file_path):
        # Use image analysis for image files
        explanation = await medgemma.analyze_medical_image(
            image_paths=[report.file_path],
            image_type=report.report_type or "medical document",
            question=specific_question
        )
        summary_text = explanation["analysis"]
    else:
        # Use text analysis
        if not report.extracted_text or "could not extract" in report.extracted_text.lower():
            # Try image analysis as fallback if file exists
            if os.path.exists(report.file_path):
                explanation = await medgemma.analyze_medical_image(
                    image_paths=[report.file_path],
                    image_type=report.report_type or "medical document",
                    question=specific_question
                )
                summary_text = explanation["analysis"]
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="Report text not available and file not found for image analysis."
                )
        else:
            # Use text-based analysis
            report_text = report.extracted_text
            if specific_question:
                report_text += f"\n\nPatient's specific question: {specific_question}"

            # Only send images for true image reports; PDFs and other formats confuse Ollama's image handling
            image_paths = None
            content_type = (report.extracted_data or {}).get("content_type", "")
            if content_type.startswith("image/") and os.path.exists(report.file_path):
                image_paths = [report.file_path]

            explanation = await medgemma.explain_report(
                report_text,
                report.report_type,
                image_paths=image_paths,
            )
            summary_text = explanation["summary"]
    
    # Update report with summary
    report.summary = summary_text
    await db.commit()
    
    logger.info(f"✅ Summary generated for report {report_id}")
    
    return ReportExplanation(
        summary=summary_text,
        is_emergency=explanation.get("is_emergency", False),
        disclaimer=explanation.get("disclaimer", "This explanation is for educational purposes only.")
    )


@router.post("/{report_id}/explain", response_model=ReportExplanation)
async def explain_report(
    report_id: int,
    specific_question: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get AI explanation of a report (alias for summarize)."""
    return await summarize_report(report_id, specific_question, db)


@router.post("/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_uploaded_image(
    file: UploadFile = File(...),
    image_type: Optional[str] = Form("medical image"),
    question: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Analyze a medical image directly without saving to reports."""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: JPEG, PNG, WebP"
        )
    
    # Save temporarily
    file_ext = os.path.splitext(file.filename)[1]
    temp_filename = f"temp_{uuid.uuid4()}{file_ext}"
    temp_path = os.path.join(UPLOAD_DIR, temp_filename)
    
    content = await file.read()
    with open(temp_path, "wb") as f:
        f.write(content)
    
    try:
        # Analyze image
        result = await medgemma.analyze_medical_image(
            image_paths=[temp_path],
            image_type=image_type or "medical image",
            question=question
        )
        
        return ImageAnalysisResponse(
            analysis=result["analysis"],
            image_type=result["image_type"],
            images_analyzed=result["images_analyzed"],
            disclaimer=result["disclaimer"]
        )
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a report."""
    result = await db.execute(
        select(MedicalReport)
        .where(MedicalReport.id == report_id)
        .where(MedicalReport.user_id == current_user.id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Delete file
    if os.path.exists(report.file_path):
        os.remove(report.file_path)
    
    await db.delete(report)
    await db.commit()
    
    return {"message": "Report deleted successfully"}
