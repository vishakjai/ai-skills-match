import os
from dotenv import load_dotenv
load_dotenv() # Load .env file
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import io
from pypdf import PdfReader
from src.services.db_persistence import (
    resolve_user, save_jd_extraction, save_cv_extraction, save_analysis_report,
    list_jd_extractions, get_jd_extraction, get_cv_extraction, list_cvs_for_jd,
    count_cvs_for_jd, list_reports_for_jd, get_report_detail,
    update_jd_title, update_jd_extracted_json, delete_jd_extraction, delete_cv_extraction,
)

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

# Log ALL API requests and responses
from src.utils.api_logger import APIRequestLogger
app.add_middleware(APIRequestLogger)

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
async def extract_resume(payload: ExtractRequest, x_user_name: Optional[str] = Header(None)):
    # 1. Try LLM Extraction First
    llm_profile = None
    model_used = None
    if os.getenv("OPENAI_API_KEY"):
        try:
            from src.extraction.llm_extractor import LLMExtractor
            llm = LLMExtractor()
            llm_profile = await llm.extract_resume(payload.text)
            model_used = "gpt-4o-2024-08-06"
            
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
        # Persist to DB
        user_id = resolve_user(x_user_name) if x_user_name else None
        cv_db_id = save_cv_extraction(
            raw_text=payload.text,
            extracted_json=merged_profile.model_dump(),
            uploaded_by=user_id,
            model_used=model_used,
            is_valid=merged_profile.is_valid,
        )
        if cv_db_id:
            print(f"💾 CV extraction saved to DB: {cv_db_id}")
        return merged_profile
    else:
        raise HTTPException(status_code=503, detail="Both Extractors Failed or Not Initialized")

@app.post("/extract/jd", response_model=JobDescription)
async def extract_jd(payload: ExtractRequest, x_user_name: Optional[str] = Header(None)):
    jd = None
    model_used = None
    # UNIFIED PIPELINE APPROACH
    if hasattr(app.state, 'pipeline') and app.state.pipeline:
        try:
            jd = await app.state.pipeline.extract_jd(payload.text)
            model_used = "gpt-4o-2024-08-06"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Pipeline Extraction Failed: {e}")
    else:
        # Fallback if pipeline not initialized (e.g. no DB)
        if not extractor_instance:
             raise HTTPException(status_code=503, detail="Extractor/Pipeline not initialized")
             
        try:
            result = extractor_instance.extract(payload.text)
            jd = map_entities_to_jd(payload.text, result.entities)
            model_used = "flashtext"
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Persist to DB
    if jd:
        user_id = resolve_user(x_user_name) if x_user_name else None
        jd_db_id = save_jd_extraction(
            raw_text=payload.text,
            extracted_json=jd.model_dump(),
            uploaded_by=user_id,
            model_used=model_used,
            is_valid=jd.is_valid,
        )
        if jd_db_id:
            print(f"💾 JD extraction saved to DB: {jd_db_id}")
    return jd

@app.post("/extract/resume/file", response_model=CandidateProfile)
async def extract_resume_file(file: UploadFile = File(...), x_user_name: Optional[str] = Header(None)):
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
        model_used = None
        if os.getenv("OPENAI_API_KEY"):
            try:
                from src.extraction.llm_extractor import LLMExtractor
                llm = LLMExtractor()
                llm_profile = await llm.extract_resume(text)
                model_used = "gpt-4o-2024-08-06"
                
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
        final_profile = None
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
            final_profile = llm_profile
            
        elif llm_profile:
            final_profile = llm_profile
        elif keyword_profile:
            final_profile = keyword_profile
        else:
            raise HTTPException(status_code=503, detail="Both Extractors Failed or Not Initialized")

        # Persist to DB
        user_id = resolve_user(x_user_name) if x_user_name else None
        cv_db_id = save_cv_extraction(
            raw_text=text,
            extracted_json=final_profile.model_dump(),
            uploaded_by=user_id,
            filename=file.filename,
            model_used=model_used,
            is_valid=final_profile.is_valid,
        )
        if cv_db_id:
            print(f"💾 CV extraction saved to DB: {cv_db_id}")
        return final_profile
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File parsing failed: {str(e)}")

@app.post("/extract/jd/file", response_model=JobDescription)
async def extract_jd_file(file: UploadFile = File(...), x_user_name: Optional[str] = Header(None)):
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

    jd = None
    model_used = None
    # UNIFIED PIPELINE APPROACH
    if hasattr(app.state, 'pipeline') and app.state.pipeline:
        try:
            jd = await app.state.pipeline.extract_jd(text)
            model_used = "gpt-4o-2024-08-06"
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Pipeline Extraction Failed: {e}")
    else:
        # Fallback
        if not extractor_instance:
            raise HTTPException(status_code=503, detail="Extractor not initialized")

        try:
            result = extractor_instance.extract(text)
            jd = map_entities_to_jd(text, result.entities)
            model_used = "flashtext"
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    # Persist to DB
    if jd:
        user_id = resolve_user(x_user_name) if x_user_name else None
        jd_db_id = save_jd_extraction(
            raw_text=text,
            extracted_json=jd.model_dump(),
            uploaded_by=user_id,
            filename=file.filename,
            model_used=model_used,
            is_valid=jd.is_valid,
        )
        if jd_db_id:
            print(f"💾 JD extraction saved to DB: {jd_db_id}")
    return jd

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}

# ---------------------------------------------------------------------------
# History / Browse Endpoints
# ---------------------------------------------------------------------------

@app.get("/jds")
async def get_all_jds(limit: int = 50, offset: int = 0):
    """List all uploaded JDs (newest first) with report counts."""
    rows = list_jd_extractions(limit=limit, offset=offset)
    return {"jds": rows, "count": len(rows)}

@app.get("/jds/{jd_id}")
async def get_jd_detail(jd_id: str):
    """Get full detail of a single JD extraction."""
    row = get_jd_extraction(jd_id)
    if not row:
        raise HTTPException(status_code=404, detail="JD not found")
    return row

@app.get("/jds/{jd_id}/cvs")
async def get_cvs_for_jd(jd_id: str):
    """List all CVs that have been analysed against this JD, with latest scores."""
    rows = list_cvs_for_jd(jd_id)
    return {"jd_id": jd_id, "cvs": rows, "count": len(rows)}

@app.get("/jds/{jd_id}/reports")
async def get_reports_for_jd(jd_id: str):
    """List all analysis reports for this JD (newest first), including candidate name and score."""
    rows = list_reports_for_jd(jd_id)
    return {"jd_id": jd_id, "reports": rows, "count": len(rows)}

@app.get("/cvs/{cv_id}")
async def get_cv_detail(cv_id: str):
    """Get full detail of a single CV extraction."""
    row = get_cv_extraction(cv_id)
    if not row:
        raise HTTPException(status_code=404, detail="CV not found")
    return row

@app.get("/reports/{report_id}")
async def get_single_report(report_id: str):
    """Get full detail of a single analysis report."""
    row = get_report_detail(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return row

# ---------------------------------------------------------------------------
# JD Management (Rename, Delete, Upload CVs)
# ---------------------------------------------------------------------------

class RenameJDRequest(BaseModel):
    title: str

@app.patch("/jds/{jd_id}")
async def rename_jd(jd_id: str, payload: RenameJDRequest):
    """Rename a JD (update job_metadata.title)."""
    ok = update_jd_title(jd_id, payload.title)
    if not ok:
        raise HTTPException(status_code=404, detail="JD not found or update failed")
    return {"status": "ok", "jd_id": jd_id, "new_title": payload.title}

@app.put("/jds/{jd_id}/extracted")
async def update_jd_json(jd_id: str, payload: JobDescription):
    """Replace the full extracted JD JSON (after editing requirements, metadata, etc.)."""
    ok = update_jd_extracted_json(jd_id, payload.model_dump())
    if not ok:
        raise HTTPException(status_code=404, detail="JD not found or update failed")
    return {"status": "ok", "jd_id": jd_id}

@app.get("/jds/{jd_id}/cv-count")
async def get_jd_cv_count(jd_id: str):
    """Return the number of CVs linked to a JD (for pre-delete confirmation)."""
    jd_row = get_jd_extraction(jd_id)
    if not jd_row:
        raise HTTPException(status_code=404, detail="JD not found")
    cv_count = count_cvs_for_jd(jd_id)
    return {"jd_id": jd_id, "cv_count": cv_count}

@app.delete("/jds/{jd_id}")
async def delete_jd(jd_id: str):
    """Delete a JD and all its linked reports and associated CVs."""
    print(f"🗑️ DELETE /jds/{jd_id} requested")
    ok = delete_jd_extraction(jd_id)
    if not ok:
        print(f"⚠️ DELETE /jds/{jd_id} failed")
        raise HTTPException(status_code=404, detail="JD not found or delete failed")
    print(f"✅ DELETE /jds/{jd_id} succeeded")
    return {"status": "deleted", "jd_id": jd_id}

@app.delete("/cvs/{cv_id}")
async def delete_cv(cv_id: str):
    """Delete a CV and its linked analysis reports."""
    print(f"🗑️ DELETE /cvs/{cv_id} requested")
    ok = delete_cv_extraction(cv_id)
    if not ok:
        print(f"⚠️ DELETE /cvs/{cv_id} failed")
        raise HTTPException(status_code=404, detail="CV not found or delete failed")
    print(f"✅ DELETE /cvs/{cv_id} succeeded")
    return {"status": "deleted", "cv_id": cv_id}

@app.post("/jds/{jd_id}/upload-cvs")
async def upload_cvs_for_jd(
    jd_id: str,
    files: List[UploadFile] = File(...),
    x_user_name: Optional[str] = Header(None),
):
    """
    Upload one or more CV files against an existing JD.
    Each file is extracted, saved, and then matched against the JD.
    Returns a summary of all processed CVs with their scores.
    """
    # Verify JD exists
    jd_row = get_jd_extraction(jd_id)
    if not jd_row:
        raise HTTPException(status_code=404, detail="JD not found")

    user_id = resolve_user(x_user_name) if x_user_name else None
    jd_obj = JobDescription.model_validate(jd_row["extracted_json"])

    results = []
    for file in files:
        entry = {"filename": file.filename, "status": "error", "score": None, "cv_id": None, "report_id": None, "error": None}
        try:
            content = await file.read()

            # 1. Extract text from file (PDF, DOCX, TXT) via guardrails
            validation = guard_service.validate_upload(content, file.filename, DocumentType.RESUME)
            text = validation.extracted_text

            if not text or len(text.strip()) < 50:
                entry["error"] = validation.rejection_reason or "Could not extract sufficient text from file"
                results.append(entry)
                continue

            # 2. LLM extraction
            llm_profile = None
            model_used = None
            if os.getenv("OPENAI_API_KEY"):
                try:
                    from src.extraction.llm_extractor import LLMExtractor
                    llm = LLMExtractor()
                    llm_profile = await llm.extract_resume(text)
                    model_used = "gpt-4o-2024-08-06"
                except Exception as e:
                    print(f"⚠️ LLM extraction failed for {file.filename}: {e}")

            # 3. FlashText extraction
            keyword_profile = None
            if extractor_instance:
                try:
                    result = extractor_instance.extract(text)
                    keyword_profile = map_entities_to_candidate(text, result.entities)
                except Exception as e:
                    print(f"⚠️ FlashText failed for {file.filename}: {e}")

            # 4. Merge
            final_profile = None
            if llm_profile and keyword_profile:
                existing_ids = {normalize_skill(s.skill_id) for s in llm_profile.skills}
                for k_skill in keyword_profile.skills:
                    if normalize_skill(k_skill.skill_id) not in existing_ids:
                        llm_profile.skills.append(k_skill)
                        existing_ids.add(normalize_skill(k_skill.skill_id))
                final_profile = llm_profile
            elif llm_profile:
                final_profile = llm_profile
            elif keyword_profile:
                final_profile = keyword_profile

            if not final_profile:
                entry["error"] = "Extraction failed for this file"
                results.append(entry)
                continue

            # 5. Save CV to DB
            cv_db_id = save_cv_extraction(
                raw_text=text,
                extracted_json=final_profile.model_dump(),
                uploaded_by=user_id,
                filename=file.filename,
                model_used=model_used,
                is_valid=final_profile.is_valid,
            )
            entry["cv_id"] = cv_db_id

            # 6. Run match and save report
            if cv_db_id:
                match_result = await calculate_match(final_profile, jd_obj)
                report_id = save_analysis_report(
                    jd_id=jd_id,
                    cv_id=cv_db_id,
                    score=match_result.score,
                    analysis_json=match_result.model_dump(),
                    run_by=user_id,
                )
                entry["report_id"] = report_id
                entry["score"] = match_result.score
                entry["status"] = "success"
                entry["candidate_name"] = final_profile.candidate_metadata.name if final_profile.candidate_metadata else None
            else:
                entry["error"] = "Failed to save CV to database"

        except Exception as e:
            entry["error"] = str(e)

        results.append(entry)

    return {
        "jd_id": jd_id,
        "processed": len(results),
        "successful": sum(1 for r in results if r["status"] == "success"),
        "results": results,
    }

class ReanalyseRequest(BaseModel):
    jd_id: str
    cv_id: str

@app.post("/reanalyse", response_model=MatchResult)
async def reanalyse(payload: ReanalyseRequest, x_user_name: Optional[str] = Header(None)):
    """Re-run analysis for an existing JD + CV pair using their stored extracted data."""
    jd_row = get_jd_extraction(payload.jd_id)
    if not jd_row:
        raise HTTPException(status_code=404, detail="JD not found")
    cv_row = get_cv_extraction(payload.cv_id)
    if not cv_row:
        raise HTTPException(status_code=404, detail="CV not found")

    try:
        candidate = CandidateProfile.model_validate(cv_row["extracted_json"])
    except Exception as e:
        print(f"⚠️ Reanalyse: CV validation failed for cv_id={payload.cv_id}: {e}")
        raise HTTPException(status_code=500, detail=f"CV data validation failed: {str(e)}")

    try:
        jd = JobDescription.model_validate(jd_row["extracted_json"])
    except Exception as e:
        print(f"⚠️ Reanalyse: JD validation failed for jd_id={payload.jd_id}: {e}")
        raise HTTPException(status_code=500, detail=f"JD data validation failed: {str(e)}")

    try:
        result = await calculate_match(candidate, jd)

        # Persist new report
        user_id = resolve_user(x_user_name) if x_user_name else None
        report_id = save_analysis_report(
            jd_id=payload.jd_id,
            cv_id=payload.cv_id,
            score=result.score,
            analysis_json=result.model_dump(),
            run_by=user_id,
        )
        if report_id:
            print(f"💾 Re-analysis report saved to DB: {report_id}")

        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Re-analysis failed: {str(e)}")

@app.post("/match", response_model=MatchResult)
async def match_profiles(payload: MatchRequest, x_user_name: Optional[str] = Header(None)):
    """
    Deterministic matching endpoint.
    """
    try:
        result = await calculate_match(payload.candidate, payload.job_description)

        # Persist to DB: save JD, CV, and analysis report
        user_id = resolve_user(x_user_name) if x_user_name else None
        jd_db_id = save_jd_extraction(
            raw_text="(submitted via /match)",
            extracted_json=payload.job_description.model_dump(),
            uploaded_by=user_id,
            model_used="pre-extracted",
            is_valid=payload.job_description.is_valid,
        )
        cv_db_id = save_cv_extraction(
            raw_text="(submitted via /match)",
            extracted_json=payload.candidate.model_dump(),
            uploaded_by=user_id,
            model_used="pre-extracted",
            is_valid=payload.candidate.is_valid,
        )
        if jd_db_id and cv_db_id:
            report_id = save_analysis_report(
                jd_id=jd_db_id,
                cv_id=cv_db_id,
                score=result.score,
                analysis_json=result.model_dump(),
                run_by=user_id,
            )
            if report_id:
                print(f"💾 Analysis report saved to DB: {report_id}")

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
