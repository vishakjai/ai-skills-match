import os
from dotenv import load_dotenv
load_dotenv() # Load .env file
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import io
from pypdf import PdfReader

from src.core.models import (
    CandidateProfile, JobDescription, CandidateSkill, ComputedStats, 
    JobMetadata, GatingRules, Requirement, SenioritySignals,
    CandidateMetadata, ComputedCandidateStats, TimelineEntry, EducationEntry, SkillProfileEntry, TimelineSkill
)
from src.core.engine import calculate_match, MatchResult
from src.core.utils import normalize_skill
from src.core.graph import ontology
from src.extraction.extractor import SkillExtractor
from src.extraction.schemas import ExtractedEntity
from src.services.guardrails import DocumentGuardService, DocumentType

# Global Extractor Instance
extractor_instance = None
guard_service = DocumentGuardService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load the dictionary AND Ontology
    global extractor_instance
    db_url = os.environ.get("SUPABASE_URL")
    if not db_url:
        print("⚠️ SUPABASE_URL not set. Hybrid Extractor will depend on vector fallback or fail.")
    else:
        print("🚀 Initializing Hybrid Skill Extractor & Graph Ontology...")
        extractor_instance = SkillExtractor(db_url)
        # Load Graph from DB
        ontology.load_from_db(db_url)
        
        # Initialize Unified Pipeline
        global batch_processor
        # We need to re-init batch processor or inject dependencies
        # But first let's create the pipeline
        from src.extraction.pipeline import ExtractionPipeline
        pipeline = ExtractionPipeline(extractor_instance)
        
        # Inject into Global State (hacky but works for now)
        app.state.pipeline = pipeline
        
        # Inject into Batch Processor
        batch_processor.pipeline = pipeline
        batch_processor.keyword_extractor = extractor_instance # Keep for now if needed specific access
        
    yield
    # Shutdown: Clean up?
    extractor_instance = None
    batch_processor.keyword_extractor = None
    batch_processor.stop()

app = FastAPI(title="AI Skills Match Engine", version="0.1.0", lifespan=lifespan)

# Allow CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MatchRequest(BaseModel):
    candidate: CandidateProfile
    job_description: JobDescription

class ExtractRequest(BaseModel):
    text: str
    api_key: str | None = None  # Legacy param (not needed for FlashText, but kept for interface compat)

# --- Helpers to Map Flat Entities -> Hierarchical Profile ---

from src.extraction.mappers import map_entities_to_candidate, map_entities_to_jd
from src.extraction.metadata import MetadataExtractor

# ... (Previous imports)

metadata_extractor = MetadataExtractor()


@app.post("/extract/resume", response_model=CandidateProfile)
async def extract_resume(payload: ExtractRequest):
    # 1. Try LLM Extraction First
    llm_profile = None
    if os.getenv("OPENAI_API_KEY"):
        try:
            from src.extraction.llm_extractor import LLMExtractor
            llm = LLMExtractor()
            llm_profile = await llm.extract_resume(payload.text)
            
            # GUARDRAIL: Document Validation
            if not llm_profile.is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid Document: {llm_profile.parsing_error or 'Does not appear to be a Resume'}")
                
        except HTTPException:
            raise
        except Exception as e:
            print(f"⚠️ LLM Failed ({e}), falling back to Hybrid...")

    # 2. Run FlashText (Keyword Matching) - Always run for high recall
    keyword_profile = None
    if extractor_instance:
        try:
            result = extractor_instance.extract(payload.text)
            keyword_profile = map_entities_to_candidate(payload.text, result.entities)
        except Exception as e:
            print(f"⚠️ FlashText Failed ({e})")

    # 3. Merge Strategies
    from src.extraction.utils import merge_profiles
    merged_profile = merge_profiles(llm_profile, keyword_profile)
    
    if merged_profile:
        return merged_profile
    else:
        raise HTTPException(status_code=503, detail="Both Extractors Failed or Not Initialized")

@app.post("/extract/jd", response_model=JobDescription)
async def extract_jd(payload: ExtractRequest):
    # UNIFIED PIPELINE APPROACH
    if hasattr(app.state, 'pipeline') and app.state.pipeline:
        try:
            jd = await app.state.pipeline.extract_jd(payload.text)
            return jd
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Pipeline Extraction Failed: {e}")
    else:
        # Fallback if pipeline not initialized (e.g. no DB)
        # Should probably warn or fail, but let's try manual FlashText if available
        if not extractor_instance:
             raise HTTPException(status_code=503, detail="Extractor/Pipeline not initialized")
             
        try:
            result = extractor_instance.extract(payload.text)
            jd = map_entities_to_jd(payload.text, result.entities)
            return jd
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract/resume/file", response_model=CandidateProfile)
async def extract_resume_file(file: UploadFile = File(...)):
    if not extractor_instance and not os.getenv("OPENAI_API_KEY"):
         raise HTTPException(status_code=503, detail="Extractor not initialized")
    
    try:
        content = await file.read()
        
        # 0. Deterministic Guardrails (Magic + Keywords)
        validation = guard_service.validate_upload(content, file.filename, DocumentType.RESUME)
        
        # Relaxed Guard: If text exists, proceed even if validation (keywords) failed
        if not validation.extracted_text:
            print(f"🛑 Guardrail Blocked: {validation.rejection_reason}")
            raise HTTPException(status_code=400, detail=f"Invalid Document: {validation.rejection_reason}")
            
        text = validation.extracted_text # Use the text extracted during validation!
        
        # If text is too short (maybe it was a scanned PDF), we might need OCR, 
        # but for now we assume text extraction worked if validation passed.
        if not text:
             raise HTTPException(status_code=400, detail="Could not extract text from document.")
              
        # 1. Try LLM Extraction First
        llm_profile = None
        if os.getenv("OPENAI_API_KEY"):
            try:
                from src.extraction.llm_extractor import LLMExtractor
                llm = LLMExtractor()
                llm_profile = await llm.extract_resume(text)
                
                print(f"🧐 DEBUG: LLM Extraction Complete. Valid: {llm_profile.is_valid}, Error: {llm_profile.parsing_error}")
                print(f"🧐 DEBUG: LLM Profile Dump: {llm_profile.model_dump_json(exclude={'timeline', 'skills'})}") # minimalist dump

                # GUARDRAIL: Document Validation
                if not llm_profile.is_valid:
                    print("🛑 GUARDRAIL TRIGGERED: Raising 400")
                    raise HTTPException(status_code=400, detail=f"Invalid Document: {llm_profile.parsing_error or 'Does not appear to be a Resume'}")
                    
            except HTTPException:
                print("🛑 GUARDRAIL: Re-raising HTTPException")
                raise
            except Exception as e:
                print(f"⚠️ LLM Failed completely ({type(e).__name__}: {e}), falling back to FlashText...")

        # 2. Run FlashText (Keyword Matching)
        keyword_profile = None
        if extractor_instance:
            try:
                result = extractor_instance.extract(text)
                keyword_profile = map_entities_to_candidate(text, result.entities)
            except Exception as e:
                print(f"⚠️ FlashText Failed ({e})")

        # 3. Merge Strategies
        if llm_profile and keyword_profile:
            # Merge keyword skills into LLM profile if missing
            print("🔗 Merging LLM and FlashText Results...")
            
            existing_ids = set()
            for s in llm_profile.skills:
                existing_ids.add(normalize_skill(s.skill_id))
                
            count_added = 0
            for k_skill in keyword_profile.skills:
                norm_k_id = normalize_skill(k_skill.skill_id)
                if norm_k_id not in existing_ids:
                    llm_profile.skills.append(k_skill)
                    existing_ids.add(norm_k_id)
                    count_added += 1
                    
            print(f"✅ Merged: Added {count_added} skills from FlashText to LLM result.")
            return llm_profile
            
        elif llm_profile:
            return llm_profile
        elif keyword_profile:
            return keyword_profile
        else:
            raise HTTPException(status_code=503, detail="Both Extractors Failed or Not Initialized")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File parsing failed: {str(e)}")

@app.post("/extract/jd/file", response_model=JobDescription)
async def extract_jd_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        
        # 0. Deterministic Guardrails
        validation = guard_service.validate_upload(content, file.filename, DocumentType.JOB_DESCRIPTION)
        
        # Relaxed Guard: If text exists, proceed even if validation (keywords) failed
        if not validation.extracted_text:
             print(f"🛑 Guardrail Blocked: {validation.rejection_reason}")
             raise HTTPException(status_code=400, detail=f"Invalid Document: {validation.rejection_reason}")
             
        text = validation.extracted_text
        print(f"📄 DEBUG JD: Received {len(text)} chars of raw text.")
    except HTTPException:
        raise
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"File reading failed: {e}")

    # UNIFIED PIPELINE APPROACH
    if hasattr(app.state, 'pipeline') and app.state.pipeline:
        try:
            jd = await app.state.pipeline.extract_jd(text)
            return jd
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Pipeline Extraction Failed: {e}")

    # Fallback
    if not extractor_instance:
        raise HTTPException(status_code=503, detail="Extractor not initialized")

    try:
        result = extractor_instance.extract(text)
        jd = map_entities_to_jd(text, result.entities)
        return jd
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}

@app.post("/match", response_model=MatchResult)
async def match_profiles(payload: MatchRequest):
    """
    Deterministic matching endpoint.
    """
    try:
        # Normalize inputs on the fly? 
        # Ideally inputs are pre-normalized, but we can do a pass here if needed.
        # But our engine handles JD normalization. Candidate skills are assumed structured.
        
        result = await calculate_match(payload.candidate, payload.job_description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/normalize")
async def normalize_text(text: str):
    """
    Helper to see how text is slugified.
    """
    return {"original": text, "normalized": normalize_skill(text)}

from src.services.batch_processor import InMemoryBatchProcessor
from src.core.batch_models import BatchJobResult
from src.extraction.llm_extractor import LLMExtractor
from src.services.tribunal import TribunalService
from src.services.guardrails import DocumentGuardService
from fastapi import Form

# Batch Processor Dependencies
llm_extractor = LLMExtractor()
tribunal_service = TribunalService()

# Initializes the processor (Lazy init later or update global?)
# Problem: extractor_instance is None at module level until lifespan startup.
# Solution: We assign it inside lifespan.
batch_processor = InMemoryBatchProcessor(llm_extractor, tribunal_service, guard_service, keyword_extractor=None)

@app.post("/batch/upload", response_model=dict)
async def submit_batch_job(
    jd: Optional[str] = Form(None),
    jd_json: Optional[str] = Form(None),
    files: List[UploadFile] = File(...)
):
    print(f"📥 Batch Upload: Received {len(files)} files.")
    
    # Check Inputs
    jd_input = None
    if jd_json:
        try:
            jd_input = JobDescription.model_validate_json(jd_json)
            print("📦 Batch: Using Pre-Configured JD JSON")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON for JD: {e}")
    elif jd:
        jd_input = jd
    else:
        raise HTTPException(status_code=400, detail="Must provide either 'jd' (text) or 'jd_json' (structure)")

    # Read files into memory
    file_data = []
    for f in files:
        if f.filename:
            content = await f.read()
            file_data.append(content) 
    
    batch_id = await batch_processor.submit_batch(jd_input, file_data)
    
    return {
        "batch_id": batch_id, 
        "message": "Batch processing started",
        "poll_url": f"/batch/{batch_id}"
    }

@app.get("/batch/{batch_id}", response_model=BatchJobResult)
async def get_batch_status(batch_id: str):
    result = await batch_processor.get_status(batch_id)
    if not result:
        raise HTTPException(status_code=404, detail="Batch Job not found")
    return result

@app.post("/utils/parse_doc")
async def parse_document_text(file: UploadFile = File(...)):
    """
    Utility to extract raw text from a document (PDF, DOCX, TXT).
    Used for frontend "Upload to Fill" features.
    """
    try:
        content = await file.read()
        validation = guard_service.validate_upload(content, file.filename, DocumentType.JOB_DESCRIPTION)
        
        if not validation.extracted_text:
            raise HTTPException(status_code=400, detail=f"Could not extract text: {validation.rejection_reason}")
            
        print(f"📄 Parsed Document. Valid: {validation.is_valid}. Text Len: {len(validation.extracted_text)}")
        return {"text": validation.extracted_text, "filename": file.filename}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")
