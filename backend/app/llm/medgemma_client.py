"""
MedGemma LLM Client
Handles AI interactions with MedGemma via Ollama
Supports text, images, and document analysis
"""

import httpx
import base64
from pathlib import Path
from typing import Optional, List, Dict, Union
from PIL import Image
import logging
import io

from app.config import settings
from app.llm.prompts import (
    SYSTEM_PROMPT, 
    EXPLAIN_REPORT_PROMPT,
    MEDICATION_EXPLAIN_PROMPT,
    SYMPTOM_ASSESSMENT_PROMPT,
    GENERAL_HEALTH_PROMPT,
    CONVERSATION_PROMPT,
    IMAGE_ANALYSIS_PROMPT,
    HEALTH_SUMMARY_PROMPT,
    MEDICATION_SUMMARY_PROMPT,
    SYMPTOM_HEALTH_CHECK_PROMPT,
    check_emergency,
    EMERGENCY_RESPONSE
)

logger = logging.getLogger(__name__)


def encode_image_base64(image_path: str) -> str:
    """Encode an image file to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def pil_image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffered = io.BytesIO()
    # Convert to RGB if necessary (for PNG with transparency)
    if image.mode in ('RGBA', 'LA', 'P'):
        image = image.convert('RGB')
    image.save(buffered, format="JPEG", quality=85)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


class MedGemmaClient:
    """Client for interacting with MedGemma via Ollama for medical explanations."""
    
    def __init__(self):
        self.model = settings.ollama_model
        self.base_url = settings.ollama_base_url
        self.timeout = httpx.Timeout(180.0, connect=10.0)  # 180s for generation (images take longer)
        
        print(f"🏥 MedGemma configured for Ollama inference")
        print(f"   Model: {self.model}")
        print(f"   Ollama URL: {self.base_url}")
        logger.info(f"MedGemma configured for Ollama inference with model: {self.model}")
    
    async def _check_ollama_connection(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    if self.model in model_names:
                        logger.info(f"✅ Ollama connected, model {self.model} available")
                        return True
                    else:
                        logger.warning(f"⚠️ Model {self.model} not found. Available: {model_names}")
                        return False
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to Ollama: {e}")
            return False
    
    async def _generate_response(
        self, 
        prompt: str, 
        context: str = "", 
        images: Optional[List[str]] = None,  # List of base64 encoded images
        history: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
        skip_emergency_check: bool = False
    ) -> str:
        """Generate a response from MedGemma via Ollama with safety checks."""
        # Check for emergency first (skip when summarizing documents - they often mention clinical terms)
        if not skip_emergency_check and (check_emergency(prompt) or check_emergency(context)):
            return EMERGENCY_RESPONSE
        
        num_images = len(images) if images else 0
        logger.info(f"Generating response via Ollama (prompt length: {len(prompt)}, images: {num_images}, history: {len(history) if history else 0} messages)")
        
        try:
            # Build messages array with proper multi-turn format
            messages = []
            
            # Add system message
            messages.append({
                "role": "system",
                "content": system_prompt or SYSTEM_PROMPT
            })
            
            # Add conversation history if provided
            if history:
                for msg in history[-10:]:  # Last 10 messages for context
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            # Build current user message
            if context:
                user_content = f"Context: {context}\n\nQuestion: {prompt}"
            else:
                user_content = prompt
            
            user_message = {"role": "user", "content": user_content}
            
            # Add images if provided (Ollama multimodal support)
            if images and len(images) > 0:
                user_message["images"] = images
                logger.info(f"📷 Sending {len(images)} image(s) to model")
            
            messages.append(user_message)
            
            # Prepare the request payload
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": settings.max_new_tokens,
                    "temperature": 0.7,
                }
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                
                if response.status_code != 200:
                    error_msg = f"Ollama API error: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                
                result = response.json()
                generated_text = result.get("message", {}).get("content", "")
                
                if not generated_text:
                    logger.warning("Empty response from Ollama")
                    raise ValueError("Model generated empty response")
                
                logger.info(f"✅ Generated response (length: {len(generated_text)})")
                return generated_text.strip()
                
        except httpx.TimeoutException:
            logger.error("❌ Ollama request timed out")
            raise RuntimeError("Request to Ollama timed out. The model may be loading or processing a complex query.")
        except httpx.ConnectError:
            logger.error("❌ Cannot connect to Ollama. Is it running?")
            raise RuntimeError("Cannot connect to Ollama. Please ensure 'ollama serve' is running.")
        except Exception as e:
            logger.error(f"❌ Ollama generation error: {type(e).__name__}: {e}")
            raise

    async def explain_report(
        self, 
        report_text: str, 
        report_type: Optional[str] = None,
        image_paths: Optional[List[str]] = None
    ) -> Dict:
        """Generate a patient-friendly explanation of a medical report."""
        prompt = EXPLAIN_REPORT_PROMPT.format(report_text=report_text)
        if report_type:
            prompt = f"Report Type: {report_type}\n\n" + prompt
        
        # Encode images if provided
        images = None
        if image_paths:
            images = []
            for path in image_paths:
                if Path(path).exists():
                    images.append(encode_image_base64(path))
                    logger.info(f"📷 Added image: {path}")
        
        explanation = await self._generate_response(
            prompt, report_text, images=images, skip_emergency_check=True
        )
        
        return {
            "summary": explanation,
            "is_emergency": check_emergency(report_text),
            "disclaimer": "This explanation is for educational purposes only. Please discuss your results with your healthcare provider."
        }
    
    async def analyze_medical_image(
        self,
        image_paths: List[str],
        image_type: str = "medical image",
        question: Optional[str] = None
    ) -> Dict:
        """Analyze medical images (X-rays, scans, reports, etc.) using MedGemma's vision capabilities."""
        # Encode all valid images
        images = []
        valid_paths = []
        for path in image_paths:
            if Path(path).exists():
                images.append(encode_image_base64(path))
                valid_paths.append(path)
        
        if not images:
            return {
                "analysis": "No valid images provided for analysis.",
                "image_type": image_type,
                "disclaimer": "Please provide valid image files."
            }
        
        # Build prompt
        prompt = IMAGE_ANALYSIS_PROMPT.format(
            image_type=image_type,
            num_images=len(images),
            question=question or f"Please analyze this {image_type} and describe what you observe."
        )
        
        # Add image file references to prompt
        image_labels = "\n".join(f"  - Image {i+1}: {Path(p).name}" for i, p in enumerate(valid_paths))
        prompt += f"\n\n## Attached Images ({len(images)} provided)\n{image_labels}"
        
        response = await self._generate_response(
            prompt, image_type, images=images, skip_emergency_check=True
        )
        
        return {
            "analysis": response,
            "image_type": image_type,
            "images_analyzed": len(images),
            "disclaimer": "This AI analysis is for educational purposes only and should not replace professional medical interpretation. Always consult with your healthcare provider."
        }
    
    async def explain_medication(
        self, 
        medication_name: str, 
        dosage: str, 
        purpose: Optional[str] = None
    ) -> Dict:
        """Generate a patient-friendly medication explanation."""
        prompt = MEDICATION_EXPLAIN_PROMPT.format(
            medication_name=medication_name,
            dosage=dosage,
            purpose=purpose or "Not specified"
        )
        
        explanation = await self._generate_response(prompt)
        
        return {
            "explanation": explanation,
            "reminder": "Always take medications exactly as prescribed by your doctor. If you have questions, ask your pharmacist."
        }
    
    async def summarize_medications(
        self,
        medications: List[Dict]
    ) -> Dict:
        """Generate a summary of all medications a user is taking."""
        if not medications:
            return {
                "summary": "No active medications to summarize.",
                "interactions_warning": False,
                "disclaimer": "Please add your medications to get a summary."
            }
        
        # Format medications for the prompt
        meds_text = "\n".join([
            f"- {m['name']} ({m['dosage']}): {m.get('frequency', 'as directed')} - Purpose: {m.get('purpose', 'Not specified')}"
            for m in medications
        ])
        
        prompt = MEDICATION_SUMMARY_PROMPT.format(
            medications=meds_text,
            count=len(medications)
        )
        
        summary = await self._generate_response(prompt)
        
        return {
            "summary": summary,
            "medication_count": len(medications),
            "disclaimer": "This summary is for educational purposes. Always consult your pharmacist or doctor about drug interactions and proper medication management."
        }
    
    async def assess_symptoms(
        self, 
        symptoms: str, 
        duration: str, 
        severity: int
    ) -> Dict:
        """Provide educational information about symptoms."""
        # Emergency check first
        if check_emergency(symptoms):
            return {
                "response": EMERGENCY_RESPONSE,
                "is_emergency": True,
                "action_required": "SEEK IMMEDIATE MEDICAL ATTENTION"
            }
        
        prompt = SYMPTOM_ASSESSMENT_PROMPT.format(
            symptoms=symptoms,
            duration=duration,
            severity=severity
        )
        
        response = await self._generate_response(prompt, symptoms)
        
        return {
            "response": response,
            "is_emergency": False,
            "recommendation": "Consider scheduling an appointment with your healthcare provider to discuss these symptoms."
        }
    
    async def check_symptom_health(
        self,
        symptoms: List[Dict],
        days: int = 30
    ) -> Dict:
        """Analyze symptom patterns and provide health assessment."""
        if not symptoms:
            return {
                "assessment": "No symptoms recorded to assess.",
                "risk_level": "unknown",
                "recommendations": ["Start tracking your symptoms to get health insights."],
                "disclaimer": "Please log symptoms to receive health assessments."
            }
        
        # Format symptoms for the prompt
        symptoms_text = "\n".join([
            f"- {s['symptom']} (Severity: {s['severity']}/10, Duration: {s.get('duration', 'unknown')}, "
            f"Recorded: {s.get('recorded_at', 'unknown')}, Triggers: {s.get('triggers', 'none identified')})"
            for s in symptoms
        ])
        
        prompt = SYMPTOM_HEALTH_CHECK_PROMPT.format(
            symptoms=symptoms_text,
            count=len(symptoms),
            days=days
        )
        
        response = await self._generate_response(prompt)
        
        # Determine risk level based on severities
        avg_severity = sum(s.get('severity', 5) for s in symptoms) / len(symptoms)
        max_severity = max(s.get('severity', 5) for s in symptoms)
        
        if max_severity >= 8 or avg_severity >= 7:
            risk_level = "high"
        elif max_severity >= 6 or avg_severity >= 5:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "assessment": response,
            "risk_level": risk_level,
            "average_severity": round(avg_severity, 1),
            "max_severity": max_severity,
            "symptom_count": len(symptoms),
            "disclaimer": "This assessment is for educational purposes only. Please consult your healthcare provider for proper diagnosis."
        }
    
    async def generate_health_summary(
        self,
        user_data: Dict
    ) -> Dict:
        """Generate a comprehensive health summary based on user's data."""
        # Extract data
        medications = user_data.get("medications", [])
        symptoms = user_data.get("symptoms", [])
        reports = user_data.get("reports", [])
        conversations = user_data.get("recent_queries", [])
        
        # Format data for prompt
        meds_text = "\n".join([
            f"- {m['name']} ({m['dosage']}): {m.get('purpose', 'purpose not specified')}"
            for m in medications
        ]) if medications else "No active medications"
        
        symptoms_text = "\n".join([
            f"- {s['symptom']} (Severity: {s['severity']}/10)"
            for s in symptoms[:10]  # Last 10 symptoms
        ]) if symptoms else "No recent symptoms"
        
        reports_text = "\n".join([
            f"- {r.get('report_type', 'Report')}: {r.get('filename', 'Unknown')} - {r.get('summary', 'No summary')[:100]}..."
            for r in reports[:5]  # Last 5 reports
        ]) if reports else "No medical reports"
        
        queries_text = "\n".join([
            f"- {q[:100]}..." for q in conversations[:5]
        ]) if conversations else "No recent health queries"
        
        prompt = HEALTH_SUMMARY_PROMPT.format(
            medications=meds_text,
            symptoms=symptoms_text,
            reports=reports_text,
            queries=queries_text,
            medication_count=len(medications),
            symptom_count=len(symptoms),
            report_count=len(reports)
        )
        
        summary = await self._generate_response(prompt)
        
        return {
            "summary": summary,
            "data_summary": {
                "active_medications": len(medications),
                "recent_symptoms": len(symptoms),
                "medical_reports": len(reports)
            },
            "generated_at": "now",
            "disclaimer": "This health summary is AI-generated for educational purposes. It is not a medical diagnosis. Please consult your healthcare provider for professional medical advice."
        }
    
    async def chat(
        self, 
        message: str, 
        history: Optional[List[Dict]] = None
    ) -> Dict:
        """Handle general conversation with the patient."""
        # Emergency check first
        if check_emergency(message):
            return {
                "response": EMERGENCY_RESPONSE,
                "is_emergency": True,
                "category": "emergency"
            }
        
        # Use Ollama's multi-turn conversation format with history
        response = await self._generate_response(
            prompt=message,
            context="",
            images=None,
            history=history
        )
        
        # Categorize the message
        category = self._categorize_message(message)
        
        return {
            "response": response,
            "is_emergency": False,
            "category": category
        }
    
    def _categorize_message(self, message: str) -> str:
        """Categorize a patient's message."""
        message_lower = message.lower()
        
        medication_keywords = ["medicine", "medication", "pill", "drug", "dose", "taking", "prescription"]
        symptom_keywords = ["pain", "ache", "feel", "feeling", "symptom", "hurt", "sick", "tired", "nausea"]
        report_keywords = ["report", "test", "result", "lab", "blood", "scan", "xray", "mri", "ct"]
        
        if any(kw in message_lower for kw in medication_keywords):
            return "medication"
        elif any(kw in message_lower for kw in symptom_keywords):
            return "symptom"
        elif any(kw in message_lower for kw in report_keywords):
            return "report"
        else:
            return "general"
    
    def get_model_info(self) -> Dict:
        """Get information about the current model configuration."""
        return {
            "model_id": self.model,
            "backend": "ollama",
            "ollama_url": self.base_url,
            "max_tokens": settings.max_new_tokens,
            "supports_images": True
        }


# Global client instance
medgemma = MedGemmaClient()
