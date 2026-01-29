import asyncio
import uuid
import logging
from typing import List, Dict, Optional
from datetime import datetime

from src.core.models import JobDescription, CandidateProfile
from src.core.batch_models import BatchJobResult, BatchStatus, CandidateMatchSummary
from src.extraction.llm_extractor import LLMExtractor
from src.core.engine import calculate_match
from src.services.tribunal import TribunalService
from src.services.guardrails import DocumentGuardService, DocumentType

logger = logging.getLogger(__name__)

class InMemoryBatchProcessor:
    def __init__(self, extractor: LLMExtractor, tribunal: TribunalService, guard: DocumentGuardService, keyword_extractor=None, pipeline=None):
        self.extractor = extractor
        self.tribunal = tribunal
        self.guard = guard
        self.keyword_extractor = keyword_extractor
        self.pipeline = pipeline
        # In-Memory Store: {batch_id: BatchJobResult}
        self._jobs: Dict[str, BatchJobResult] = {}

    async def submit_batch(self, jd_input: str | JobDescription, resume_files: List[bytes]) -> str:
        """
        Starts the async batch processing.
        Returns: batch_id
        """
        batch_id = str(uuid.uuid4())
        
        # Initialize Job State
        self._jobs[batch_id] = BatchJobResult(
            job_id=batch_id,
            status=BatchStatus(
                status="pending",
                total_files=len(resume_files),
                processed_count=0,
                progress_percent=0.0
            ),
            candidates=[]
        )

        # 1. Extract JD (if text) or Use Provided JD (if object)
        job_description = None

        if isinstance(jd_input, JobDescription):
             job_description = jd_input
             logger.info(f"Batch {batch_id}: Using pre-configured JD: {jd_input.job_metadata.title}")
        else:
             # Confirm JD Extraction first (Critical Step)
             try:
                 if self.pipeline:
                     job_description = await self.pipeline.extract_jd(jd_input)
                 else:
                     job_description = await self.extractor.extract_jd(jd_input)
                     
                 logger.info(f"Batch {batch_id}: JD Extracted successfully: {job_description.job_metadata.title}")
             except Exception as e:
                 logger.error(f"Batch {batch_id}: JD Extraction Failed - {e}")
                 self._jobs[batch_id].status.status = "failed"
                 return batch_id

        # Launch Background Task for Resumes
        asyncio.create_task(self._process_resumes(batch_id, job_description, resume_files))

        return batch_id

    async def get_status(self, batch_id: str) -> Optional[BatchJobResult]:
        return self._jobs.get(batch_id)

    async def _process_resumes(self, batch_id: str, jd: JobDescription, files: List[bytes]):
        """
        The Background Worker.
        Runs Map-Reduce style logic using asyncio.gather.
        """
        logger.info(f"Batch {batch_id}: Starting processing of {len(files)} files.")
        self._jobs[batch_id].status.status = "processing"

        tasks = []
        for idx, file_bytes in enumerate(files):
            tasks.append(self._process_single_resume(batch_id, idx, file_bytes, jd))

        # Run all matchers in parallel
        # Note: In a real prod env, we'd use a semaphore to limit concurrency (e.g. 5 at a time)
        # For this demo, we'll let asyncio schedule them.
        results = await asyncio.gather(*tasks)

        # Aggregate Results
        valid_candidates = [r for r in results if r is not None]
        
        # Sort by Score
        valid_candidates.sort(key=lambda x: x.total_score, reverse=True)

        # Update Final State
        self._jobs[batch_id].candidates = valid_candidates
        
        if valid_candidates:
            avg = sum(c.total_score for c in valid_candidates) / len(valid_candidates)
            self._jobs[batch_id].average_score = round(avg, 1)
            self._jobs[batch_id].best_candidate_name = valid_candidates[0].name
        
        self._jobs[batch_id].status.status = "completed"
        self._jobs[batch_id].status.progress_percent = 100.0
        logger.info(f"Batch {batch_id}: Completed. {len(valid_candidates)} candidates ranked.")

    async def _process_single_resume(self, batch_id: str, idx: int, file_bytes: bytes, jd: JobDescription) -> Optional[CandidateMatchSummary]:
        try:
            # 1. Validate & Extract Text
            validation = self.guard.validate_upload(file_bytes, f"resume_{idx}.pdf", DocumentType.RESUME)
            
            if not validation.is_valid:
                logger.warning(f"Batch {batch_id}: File {idx} rejected by guardrails: {validation.rejection_reason}")
                return None
            
            text = validation.extracted_text
            
            # --- HYBRID EXTRACTION (Pipeline) ---
            candidate = None
            try:
                if self.pipeline:
                    candidate = await self.pipeline.extract_resume(text)
                else:
                    # Legacy Fallback (should not happen if configured correctly)
                    llm_profile = await self.extractor.extract_resume(text)
                    candidate = llm_profile
            except Exception as e:
                logger.warning(f"Batch {batch_id}: Extraction failed for {idx}: {e}")
                return None
            
            if not candidate:
                 return None

            # 2. Score (Deterministic + Internal Tribunal)
            # engine.calculate_match now handles Tribunal logic internally if score >= 60
            match_result = await calculate_match(candidate, jd)

            # Map Tribunal Tags to Colors
            # Tribunal is now inside match_result.tribunal_verdict
            tag = match_result.tribunal_verdict.narrative_tag if match_result.tribunal_verdict else None
            tribunal_color = None
            if tag:
                if tag == "top_tier_potential": tribunal_color = "Green"
                elif tag == "solid_performer": tribunal_color = "Green"
                elif tag == "high_risk": tribunal_color = "Red"
                elif tag == "mismatch": tribunal_color = "Red"
                elif tag == "analysis_failed": tribunal_color = "Yellow"
                else: tribunal_color = "Yellow" # Default

            # 3. Create Summary
            summary = CandidateMatchSummary(
                candidate_id=candidate.id,
                name=candidate.candidate_metadata.name or f"Candidate {idx+1}",
                total_score=match_result.score,
                education_status="met", # Placeholder
                experience_status="met",
                tribunal_status=tribunal_color,
                top_skills_found=[t.skill_slug for t in match_result.technical_trace if t.status == 'matched'][:5],
                missing_critical_skills=[t.skill_slug for t in match_result.technical_trace if t.priority == 'required' and t.status == 'missing'],
                details=match_result.model_dump()
            )

            # Update Progress
            job = self._jobs[batch_id]
            job.status.processed_count += 1
            job.status.progress_percent = (job.status.processed_count / job.status.total_files) * 100
            
            return summary

        except Exception as e:
            logger.error(f"Error processing resume {idx} in batch {batch_id}: {e}")
            return None
