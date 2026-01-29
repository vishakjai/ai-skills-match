from typing import List
from src.core.models import (
    CandidateProfile, JobDescription, CandidateSkill, ComputedStats, 
    JobMetadata, GatingRules, Requirement, SenioritySignals,
    CandidateMetadata, ComputedCandidateStats
)
from src.extraction.schemas import ExtractedEntity
from src.extraction.metadata import MetadataExtractor

# Instantiate global metadata extractor
metadata_extractor = MetadataExtractor()

def map_entities_to_candidate(text: str, entities: List[ExtractedEntity]) -> CandidateProfile:
    """
    Converts extracted entities into a CandidateProfile.
    """
    skills = []
    seen = set()
    
    for e in entities:
        if e.skill_id in seen:
            continue
        seen.add(e.skill_id)
        
        # Construct Skill Object
        sk = CandidateSkill(
            skill_id=e.skill_id, # This is the UUID from DB
            computed_stats=ComputedStats(
                months_experience=12, # Placeholder: FlashText doesn't infer dates yet
                recency_decay=1.0,
                evidence_confidence=e.confidence
            ),
            evidence_sources=[] # We could add the span as evidence here
        )
        skills.append(sk)
        
    return CandidateProfile(
        id="extracted-candidate",
        candidate_metadata=CandidateMetadata(),
        computed_stats=ComputedCandidateStats(),
        skills=skills,
        is_valid=True # FlashText fallback assumes validity if entities found
    )

def map_entities_to_jd(text: str, entities: List[ExtractedEntity]) -> JobDescription:
    """
    Converts extracted entities into the Advanced JobDescription Schema.
    """
    # 1. Identify Section Boundaries via Regex/Keywords
    text_lower = text.lower()
    
    # Heuristic: Find split points for Preferred Skills
    preferred_start_idx = len(text) 
    preferred_keywords = [
        "preferred qualifications", "nice to have", "desired skills", "bonus points", "pluses",
        "good to have", "would be a plus"
    ]
    for kw in preferred_keywords:
        idx = text_lower.find(kw)
        if idx != -1 and idx < preferred_start_idx:
            preferred_start_idx = idx
            
    # 2. Extract Metadata & Advanced Signals
    # We call 'extract_advanced' which returns the dictionary of new fields
    meta_dict = metadata_extractor.extract_advanced(text)

    # 3. Build Requirement Objects
    requirements = []
    seen = set()
    
    for i, e in enumerate(entities):
        if e.skill_id in seen:
            continue
        seen.add(e.skill_id)
        
        start_char, _ = e.span
        
        # Determine Priority based on section
        priority = "must_have"
        if start_char >= preferred_start_idx:
            priority = "nice_to_have"
            
        req = Requirement(
            req_id=f"req_{i}",
            skill_id=e.skill_id,
            priority=priority,
            min_years=0 # TODO: Contextual extraction per skill
        )
        requirements.append(req)

    # 4. Construct Final Object
    return JobDescription(
        id="extracted-jd",
        job_metadata=JobMetadata(
            title="Generated JD", # TODO: Extract Title
            location=meta_dict["location"],
            clearance=meta_dict["clearance"]
        ),
        gating_rules=GatingRules(
            visa_sponsorship=meta_dict["visa_sponsorship"],
            education_min=meta_dict["education_min"],
            security_clearance=meta_dict["clearance"]
        ),
        requirements=requirements,
        seniority_signals=SenioritySignals(
            target_level=meta_dict["seniority"]["target_level"],
            keywords_found=meta_dict["seniority"]["keywords_found"]
        ),
        is_valid=True # FlashText fallback
    )
