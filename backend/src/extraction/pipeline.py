import os
from typing import Optional
from src.core.models import JobDescription, CandidateProfile
from src.extraction.extractor import SkillExtractor
from src.extraction.mappers import map_entities_to_jd
from src.core.utils import normalize_skill

class ExtractionPipeline:
    def __init__(self, keyword_extractor: Optional[SkillExtractor]):
        self.keyword_extractor = keyword_extractor
        self.llm_extractor = None
        if os.getenv("OPENAI_API_KEY"):
            from src.extraction.llm_extractor import LLMExtractor
            self.llm_extractor = LLMExtractor()

    async def extract_jd(self, text: str) -> JobDescription:
        """
        Unified extraction logic for JDs.
        1. Try LLM
        2. Fallback/Supplement with FlashText
        """
        llm_jd = None
        if self.llm_extractor:
            try:
                llm_jd = await self.llm_extractor.extract_jd(text)
                if not llm_jd.is_valid:
                    print(f"⚠️ LLM JD Extraction Invalid: {llm_jd.parsing_error}")
                    llm_jd = None 
            except Exception as e:
                print(f"⚠️ LLM JD Extraction Failed: {e}")
        
        # Always run Hybrid/Keyword extraction to find missed skills
        keyword_jd = None
        if self.keyword_extractor:
            try:
                result = self.keyword_extractor.extract(text)
                keyword_jd = map_entities_to_jd(text, result.entities)
            except Exception as e:
                print(f"⚠️ FlashText JD Extraction Failed: {e}")

        # MERGE LOGIC
        if llm_jd and keyword_jd:
            print("🔗 Merging LLM and FlashText JD Results...")
            existing_skills = set()
            for r in llm_jd.requirements:
                if r.skill_id:
                    existing_skills.add(normalize_skill(r.skill_id))
            
            count_added = 0
            for k_req in keyword_jd.requirements:
                if k_req.skill_id:
                    norm_id = normalize_skill(k_req.skill_id)
                    if norm_id not in existing_skills:
                        # Add missing skill from FlashText
                        # Ensure ID is unique
                        k_req.req_id = f"ft_req_{count_added}"
                        llm_jd.requirements.append(k_req)
                        existing_skills.add(norm_id)
                        count_added += 1
            
            print(f"✅ Merged: Added {count_added} skills from FlashText to LLM JD.")
            print(f"✅ Merged: Added {count_added} skills from FlashText to LLM JD.")
            return llm_jd

        if llm_jd: return llm_jd
        if keyword_jd: return keyword_jd
        
        raise Exception("Both Extractors Failed or Not Initialized")

    async def extract_resume(self, text: str) -> CandidateProfile:
        """
        Unified extraction for Resumes.
        """
        llm_profile = None
        if self.llm_extractor:
            try:
                llm_profile = await self.llm_extractor.extract_resume(text)
                if not llm_profile.is_valid:
                    print(f"⚠️ LLM Resume Extraction Invalid: {llm_profile.parsing_error}")
                    # Don't discard if invalid, might be partially good, but let's warn
            except Exception as e:
                print(f"⚠️ LLM Resume Extraction Failed: {e}")

        keyword_profile = None
        if self.keyword_extractor:
            try:
                from src.extraction.mappers import map_entities_to_candidate
                result = self.keyword_extractor.extract(text)
                keyword_profile = map_entities_to_candidate(text, result.entities)
            except Exception as e:
                print(f"⚠️ FlashText Resume Extraction Failed: {e}")

        # MERGE
        from src.extraction.utils import merge_profiles
        merged = merge_profiles(llm_profile, keyword_profile)
        
        if merged: return merged
        raise Exception("No extractor available or both failed")
