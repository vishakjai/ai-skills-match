import asyncio
from dotenv import load_dotenv
load_dotenv()
from src.extraction.llm_extractor import LLMExtractor
from src.core.models import JobDescription

# Mock "Pasted Text" - Barebones
jd_text = """
Required: Python, Java, AWS.
Nice to have: React.
"""

async def test():
    print("🚀 Testing JD Extraction...")
    try:
        llm = LLMExtractor()
        result = await llm.extract_jd(jd_text)
        
        print("\n✅ Extraction Success:")
        print(f"Title: {result.job_metadata.title}")
        print(f"Valid: {result.is_valid}")
        if not result.is_valid:
            print(f"Error: {result.parsing_error}")
            
    except Exception as e:
        print(f"\n❌ Extraction Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test())
