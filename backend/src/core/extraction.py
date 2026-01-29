import os
from openai import OpenAI
from src.core.models import CandidateProfile, JobDescription

# Initialize client (expects OPENAI_API_KEY in env)
# In a real app, we might pass the key per request or use a global setting.
def get_client(api_key: str = None):
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OpenAI API Key not found. Please set OPENAI_API_KEY environment variable or pass it explicitly.")
    return OpenAI(api_key=key)

SYSTEM_PROMPT_CANDIDATE = """
You are an expert Resume Parser. 
Extract the candidate's skills and experience into the structured format provided.
- For 'evidence_sources', finding the EXACT verbatim text from the resume is critical.
- Infer 'months_experience' conservatively based on job dates.
- Infer 'evidence_confidence' based on how explicit the skill mention is (1.0 = specific tool listed, 0.5 = implied by generic term).
"""

SYSTEM_PROMPT_JD = """
You are an expert Job Description Parser.
Extract the required and preferred skills into the structured format.
- 'required_skills' are non-negotiable must-haves.
- 'preferred_skills' are nice-to-haves (bonus points).
- normalization: Use standard canonical slugs (e.g. 'python', 'react', 'aws') where possible, but mapped to the source text.
"""

def extract_candidate_profile(text: str, api_key: str = None) -> CandidateProfile:
    client = get_client(api_key)
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_CANDIDATE},
            {"role": "user", "content": text},
        ],
        response_format=CandidateProfile,
    )
    return completion.choices[0].message.parsed

def extract_job_description(text: str, api_key: str = None) -> JobDescription:
    client = get_client(api_key)
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_JD},
            {"role": "user", "content": text},
        ],
        response_format=JobDescription,
    )
    return completion.choices[0].message.parsed
