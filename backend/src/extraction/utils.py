from typing import Optional
from src.core.models import CandidateProfile
from src.core.utils import normalize_skill
import logging

logger = logging.getLogger(__name__)

def merge_profiles(llm_profile: Optional[CandidateProfile], keyword_profile: Optional[CandidateProfile]) -> Optional[CandidateProfile]:
    """
    Merges a FlashText (Keyword) profile into an LLM profile.
    Priority: LLM Profile is the base (structure, metadata). 
    Keyword skills are added if they are missing from LLM.
    """
    if llm_profile and keyword_profile:
        # Build set of normalized IDs from LLM
        existing_ids = set()
        for s in llm_profile.skills:
            existing_ids.add(normalize_skill(s.skill_id))
            
        count_added = 0
        for k_skill in keyword_profile.skills:
            norm_k_id = normalize_skill(k_skill.skill_id)
            if norm_k_id not in existing_ids:
                # Add it!
                llm_profile.skills.append(k_skill)
                existing_ids.add(norm_k_id)
                count_added += 1
                
        logger.info(f"🔗 Merged: Added {count_added} skills from FlashText to LLM result.")
        return llm_profile
        
    elif llm_profile:
        return llm_profile
    elif keyword_profile:
        return keyword_profile
    else:
        return None
