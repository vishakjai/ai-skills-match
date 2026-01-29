import os
from dotenv import load_dotenv
load_dotenv()
from src.extraction.extractor import SkillExtractor
from src.core.utils import normalize_skill

# Text with "Missing" Skills
text = """
Experienced DevOps Engineer with strong background in AWS Cloud services.
Proficient in Build tools like Maven and Gradle.
Expert in Git for version control and CI/CD pipelines.
"""

def test():
    db_url = os.environ.get("SUPABASE_URL")
    if not db_url:
        print("❌ SUPABASE_URL not set")
        return

    print(f"🔎 Testing Extraction on: \n{text}")
    
    extractor = SkillExtractor(db_url)
    result = extractor.extract(text)
    
    print(f"\n✅ Extracted {len(result.entities)} entities:")
    found_ids = set()
    for e in result.entities:
        print(f" - {e.canonical_name} (ID: {e.skill_id}) [Verbatim: '{e.verbatim_text}']")
        found_ids.add(e.skill_id)
        
    print("\n--- Verification ---")
    missing = []
    for expected in ["maven", "gradle", "git", "aws"]:
        if expected not in found_ids:
            # Try normalizing found IDs to check if it's just a slug mismatch
            found_normalized = {normalize_skill(fid) for fid in found_ids}
            if normalize_skill(expected) not in found_normalized:
                missing.append(expected)
    
    if missing:
        print(f"❌ FAILED: The following skills were NOT extracted: {missing}")
    else:
        print("✅ SUCCESS: All expected skills were extracted.")

if __name__ == "__main__":
    test()
