import asyncio
import os
from src.extraction.llm_extractor import LLMExtractor

JD_TEXT = """
Senior Python Engineer
Location: New York, NY (Hybrid)

We are looking for a Senior Python Engineer to join our team.
You will be working with FastAPI, AWS, and PostgreSQL.

Requirements:
- 5+ years of experience with Python (Must Have).
- Experience with AWS (Must Have).
- Familiarity with Kubernetes (Nice to Have).
- Bachelor's degree in Computer Science or related field is required.

Responsibilities:
- Build scalable APIs.
- Optimize database queries.
"""

async def test_extraction():
    extractor = LLMExtractor()
    print("Testing JD Extraction...")
    try:
        jd = await extractor.extract_jd(JD_TEXT)
        print("\n--- Extracted JD JSON ---")
        print(jd.model_dump_json(indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
