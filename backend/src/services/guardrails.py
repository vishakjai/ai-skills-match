import magic
import io
import zipfile
import re
from enum import Enum
from typing import Optional, List, Set
from pydantic import BaseModel
from pypdf import PdfReader
import xml.etree.ElementTree as ET

class DocumentType(str, Enum):
    RESUME = "resume"
    JOB_DESCRIPTION = "jd"

class ValidationResult(BaseModel):
    is_valid: bool
    detected_type: Optional[DocumentType] = None
    confidence: float = 0.0
    rejection_reason: Optional[str] = None
    extracted_text: Optional[str] = None # Return text to save double-extraction

class DocumentGuardService:
    def __init__(self):
        self.RESUME_SIGNALS = {"education", "experience", "skills", "summary", "projects", "languages", "certifications", "gmail.com", "linkedin.com", "career breakdown", "work history"}
        self.JD_SIGNALS = {"responsibilities", "requirements", "qualifications", "benefits", "salary", "equal opportunity", "we are looking for", "reports to", "job description", "about the role", "what you will do"}

    def validate_upload(self, file_bytes: bytes, filename: str, expected_type: DocumentType) -> ValidationResult:
        """
        Validates file type (Magic Bytes) and Content (Keyword Signals).
        """
        # ---------------------------------------------------------
        # Step A: Magic Byte Check
        # ---------------------------------------------------------
        try:
            mime_type = magic.from_buffer(file_bytes[:2048], mime=True)
            print(f"🕵️ Guardrails: Detected MIME: {mime_type} for {filename}")
        except Exception as e:
            return ValidationResult(is_valid=False, rejection_reason=f"MIME check failed: {e}")

        allowed_mimes = {
            "application/pdf", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
            "text/plain"
        }
        
        if mime_type not in allowed_mimes:
            return ValidationResult(is_valid=False, rejection_reason=f"Invalid file format: {mime_type}. Only PDF, DOCX, TXT allowed.")

        # ---------------------------------------------------------
        # Step B: Text Extraction (Quick & Dirty)
        # ---------------------------------------------------------
        text = ""
        try:
            if mime_type == "application/pdf":
                reader = PdfReader(io.BytesIO(file_bytes))
                # Optimization: Read first 5 pages (increased from 2)
                for i, page in enumerate(reader.pages):
                     if i >= 5: break
                     text += page.extract_text() + "\n"
                     
            elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                # Parse DOCX XML (faster than full python-docx)
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    xml_content = z.read('word/document.xml')
                    root = ET.fromstring(xml_content)
                    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    text = "\n".join([node.text for node in root.findall('.//w:t', ns) if node.text])
                    
            elif mime_type == "text/plain":
                text = file_bytes.decode("utf-8", errors="ignore")
                
        except Exception as e:
            return ValidationResult(is_valid=False, rejection_reason=f"Text extraction failed: {str(e)}")

        # Guard: Empty File
        words = text.split()
        if len(words) < 5: # Relaxed from 20 for testing
             return ValidationResult(is_valid=False, rejection_reason="File content too sparse (< 5 words).", extracted_text=text)

        # ---------------------------------------------------------
        # Step C: The Keyword Classifier (Deterministic)
        # ---------------------------------------------------------
        text_lower = text.lower()
        
        resume_score = sum(1 for s in self.RESUME_SIGNALS if s in text_lower)
        jd_score = sum(1 for s in self.JD_SIGNALS if s in text_lower)
        
        total_words = len(words)
        
        # Confidence calculation (arbitrary scaling)
        resume_confidence = (resume_score * 5) # Weighting
        jd_confidence = (jd_score * 5)
        
        print(f"🕵️ Guardrails: Resume Score={resume_score}, JD Score={jd_score}")

        # Logic
        if expected_type == DocumentType.RESUME:
            if jd_score > (resume_score * 2) and jd_score > 2:
                 return ValidationResult(is_valid=False, detected_type=DocumentType.JOB_DESCRIPTION, confidence=jd_confidence, rejection_reason="This looks like a Job Description, not a Resume.", extracted_text=text)
            
            # Require at least SOME signal for Resume
            if resume_score < 1:
                 return ValidationResult(is_valid=False, rejection_reason="No resume keywords (Experience, Education, Skills) found.", extracted_text=text)
                 
            return ValidationResult(is_valid=True, detected_type=DocumentType.RESUME, confidence=resume_confidence, extracted_text=text)

        elif expected_type == DocumentType.JOB_DESCRIPTION:
            if resume_score > (jd_score * 2) and resume_score > 2:
                 return ValidationResult(is_valid=False, detected_type=DocumentType.RESUME, confidence=resume_confidence, rejection_reason="This looks like a Resume, not a Job Description.", extracted_text=text)

            if jd_score < 1:
                 # Warning but maybe valid? 
                 return ValidationResult(is_valid=False, rejection_reason="No JD keywords (Requirements, Responsibilities) found.", extracted_text=text)
                 
            return ValidationResult(is_valid=True, detected_type=DocumentType.JOB_DESCRIPTION, confidence=jd_confidence, extracted_text=text)
            
        return ValidationResult(is_valid=False, rejection_reason="Unknown expected type")
