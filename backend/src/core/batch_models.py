from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from src.extraction.schemas.intelligence import TribunalVerdict
from src.core.models import JobDescription, CandidateProfile

class BatchStatus(BaseModel):
    status: Literal["pending", "processing", "completed", "failed"]
    total_files: int
    processed_count: int
    progress_percent: float

class CandidateMatchSummary(BaseModel):
    candidate_id: str
    name: str = "Unknown Candidate"
    total_score: float
    education_status: Literal["met", "not_met", "review_needed"]
    experience_status: Literal["met", "not_met", "review_needed"]
    tribunal_status: Optional[Literal["Green", "Yellow", "Red"]] = None
    top_skills_found: List[str] = []
    missing_critical_skills: List[str] = []
    # Full deep dive details (optional, loaded on demand or if small enough)
    details: Optional[dict] = None 

class BatchJobResult(BaseModel):
    job_id: str
    status: BatchStatus
    candidates: List[CandidateMatchSummary] = []
    average_score: float = 0.0
    best_candidate_name: Optional[str] = None
