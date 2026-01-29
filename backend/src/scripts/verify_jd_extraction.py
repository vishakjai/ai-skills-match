import asyncio
import os
import sys
sys.path.append(os.getcwd())

from src.api.main import extract_jd
from src.api.main import ExtractRequest
from src.core.graph import ontology

# Mock the extractor instance if needed, or rely on main's global if initialized
# Actually, main.py relies on a running app state for `extractor_instance`
# So we might need to manually init the extractor here.

from src.extraction.extractor import SkillExtractor

async def test_extraction():
    print("🔬 Verifying JD Extraction...")
    
    # 1. Init resources
    db_url = os.environ.get("SUPABASE_URL")
    if not db_url:
        print("⚠️ No SUPABASE_URL, cannot init FlashText properly.")
        return

    # Manually init for script
    extractor = SkillExtractor(db_url)
    ontology.load_from_db(db_url)
    
    # Text from User Screenshot
    jd_text = """
Core Technical Skills:
- Proficiency in Java programming language (Java 8 or later)
- Knowledge of relational database management systems (SQL Server, Oracle, PostgreSQL)
- Understanding of basic database design and ability to write SQL queries
- Working knowledge of HTML5, CSS3, and JavaScript fundamentals
- Familiarity with Git/GitHub version control systems
- Understanding of RESTful API design principles
- Basic knowledge of HTTP/HTTPS protocols and web services
"""

    print(f"\n📄 Input Text:\n{jd_text}\n")

    # 2. Run Hybrid Extraction (simulating main.py logic)
    # We'll use the LLM if key present, otherwise just FlashText
    
    from src.extraction.llm_extractor import LLMExtractor
    llm_result = None
    if os.getenv("OPENAI_API_KEY"):
        print("🤖 Running LLM Extraction...")
        llm = LLMExtractor()
        llm_result = await llm.extract_jd(jd_text)
        print("LLM extracted requirements:", [r.skill_id for r in llm_result.requirements])

    print("⚡ Running FlashText Extraction...")
    ft_result = extractor.extract(jd_text)
    
    # Map FlashText to IDs
    ft_skills = set()
    for e in ft_result.entities:
        ft_skills.add(e.skill_id)
        
    print("FlashText extracted IDs:", ft_skills)
    
    # 3. Check for specific targets
    targets = [
        "java", "sql_server", "oracle", "postgresql", 
        "html5", "css3", "javascript", 
        "git", "rest_api", "http"
    ]
    
    import src.core.utils as utils
    
    print("\n📊 Verification Results:")
    found_count = 0
    for t in targets:
        # Check LLM
        found_llm = False
        if llm_result:
            for r in llm_result.requirements:
                # LLM might return "Java 8" or "Java", we iterate
                if r.skill_id and (t in r.skill_id.lower() or utils.normalize_skill(r.skill_id) == t):
                    found_llm = True
        
        # Check FlashText
        found_ft = t in ft_skills
        
        status = "❌ MISSING"
        if found_llm and found_ft: status = "✅ BOTH"
        elif found_llm: status = "✅ LLM ONLY"
        elif found_ft: status = "✅ FLASHTEXT ONLY"
        
        print(f" - {t.ljust(15)}: {status}")
        if "✅" in status: found_count += 1
            
    print(f"\nScore: {found_count}/{len(targets)}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
