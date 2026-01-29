import os
import json
from openai import AsyncOpenAI
from src.core.models import JobDescription

class LLMExtractor:
    def __init__(self):
        # We take from backend env, not frontend payload
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in backend environment")
        self.client = AsyncOpenAI(api_key=api_key)

    async def extract_jd(self, text: str) -> JobDescription:
        """
        Uses OpenAI Structured Outputs to parse the text into our complex schema.
        """
        print(f"🤖 LLM Extraction: Sending {len(text)} chars to GPT-4o for JD...")
        
        try:
            response = await self.client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": "You are an expert HR Tech extraction engine. Extract the Job Description details into the requested JSON structure.\n\nCRITICAL INSTRUCTIONS:\n0. **VALIDATION**: First, verify if the input text contains **Job Requirements** or **Technical Skills**. If the input is just a list of skills (e.g. 'Required: Java, Python'), **MARK IT AS VALID (`is_valid=True`)**. Only set `is_valid=False` if the text is completely unrelated (e.g. a recipe, random conversation, weather report).\n1. **Metadata**: Extract Title, Location, and Work Mode. If Title is missing but skills are present, infer a generic title (e.g. 'Software Engineer') or leave null.\n2. **Gating Rules (`gating_rules`)**: \n   - `education_min`: Extract minimum degree. \n   - `visa_sponsorship`: True/False.\n3. **Requirements**: Break down into individual **HARD TECHNICAL SKILLS** only.\n   - `skill_id`: **MUST BE THE SKILL NAME** (e.g. 'Java', 'AWS').\n   - `priority`: 'must_have' by default, 'nice_to_have' if 'Preferred'.\n4. **Seniority**: Extract target level.\n5. **Competencies**: Extract soft skills."},
                    {"role": "user", "content": text},
                ],
                response_format=JobDescription,
            )
            
            result = response.choices[0].message.parsed
            
            # OpenAI doesn't always populate the ID, so we set a default if missing
            if not result.id:
                result.id = "llm-extracted-jd"
                
            # Post-Process: Normalize Skills
            from src.core.graph import ontology
            for req in result.requirements:
                # If skill_id is present, normalize it (resolve alias)
                if req.skill_id:
                     req.skill_id = ontology.resolve_alias(req.skill_id)
                # If missing but we have context/req_id that looks like a skill?
                # Only use req_id if it DOES NOT look like a generic ID
                elif req.req_id and len(req.req_id) < 50 and not req.req_id.lower().startswith("req_"):
                     # Fallback: try to treat req_id as skill name if short and not "req_1"
                     req.skill_id = ontology.resolve_alias(req.req_id)
            
            # Post-Process: Dedup Technical vs Soft Skills
            # If a requirement is also listed in competencies, remove it from requirements (it's soft)
            if result.competencies and result.requirements:
                comp_names = set(c.name.lower() for c in result.competencies)
                
                # Filter requirements that are actually competencies
                clean_reqs = []
                for req in result.requirements:
                    # Check if skill_id (e.g. "problem solving" or normalized slug) is in competencies
                    # We check both raw ID and space-replaced version
                    skill_check_name = req.skill_id.lower().replace("_", " ") if req.skill_id else ""
                    
                    if skill_check_name in comp_names:
                        print(f"🧹 Removed duplicated soft skill from Requirements: {req.skill_id}")
                        continue
                    clean_reqs.append(req)
                result.requirements = clean_reqs

            # Normalize Gating Rules
            if result.gating_rules.education_min:
                result.gating_rules.education_min = result.gating_rules.education_min.lower()

            print("✅ LLM JD Extraction Successful")
            return result
            
        except Exception as e:
            print(f"❌ LLM JD Extraction Failed: {e}")
            raise e

    async def extract_resume(self, text: str) -> 'CandidateProfile':
        """
        Parses text into the Advanced CandidateProfile schema.
        """
        from src.core.models import CandidateProfile # Local import to avoid circular dependency if any
        print(f"🤖 LLM Extraction: Sending {len(text)} chars to GPT-4o for Resume...")
        
        try:
            print("⏳ LLMExtractor: Calling OpenAI API...")
            response = await self.client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": "You are an expert Resume Parser. Your goal is to extract the candidate's profile into the requested JSON structure.\n\nCRITICAL INSTRUCTIONS:\n0. **VALIDATION**: First, verify if the input text is actually a **Resume/CV**. If it is unrelated text (e.g. a recipe, random article, or a Job Description), set `is_valid=False` and `parsing_error='Input does not appear to be a Resume'`. Stop extraction if invalid.\n1. **Technical Skills Section**: Always look for a 'Skills', 'Technical Skills', or 'Core Competencies' section. Create a 'SkillProfileEntry' for EVERY skill listed there, even if it doesn't appear in the Work Experience. Mark source as 'resume_skills_section'.\n2. **Timeline**: Construct a precise timeline of work experience. Infer skills used in each job based on the description.\n3. **Education**: Extract all educational qualifications (`education` list). Include Degree, Field of Study, Institution, and Year.\n4. **Normalization**: Normalize standard job titles (e.g. 'SDE II' -> 'Software Engineer').\n5. **Competencies**: Extract soft skills, behavioral traits, and professional attributes (e.g. 'Communication', 'Leadership') found in the Summary or Skills sections."},
                    {"role": "user", "content": text},
                ],
                response_format=CandidateProfile,
            )
            
            result = response.choices[0].message.parsed
            if not result.id:
                result.id = "llm-extracted-candidate"
                
            print("✅ LLM Resume Extraction Successful")
            
            # Post-Processing: Deterministic Analytics
            try:
                from src.core.analytics import calculate_analytics
                result = calculate_analytics(result)
            except Exception as analytics_error:
                print(f"⚠️ Analytics Calculation Failed: {analytics_error}")
                # Don't fail the whole extraction, just return what we have
            
            return result
        except Exception as e:
            print(f"❌ LLM Resume Extraction Failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise e
