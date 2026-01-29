import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from extraction.extractor import SkillExtractor

def verify_extraction_fix():
    # Load env for DB URL
    load_dotenv()
    db_url = os.getenv("SUPABASE_URL")
    if not db_url:
        print("❌ SUPABASE_URL not found")
        return

    print("\n🔍 Verifying Extraction Fix...")
    try:
        extractor = SkillExtractor(db_url)
        
        # Test Text
        text = "Candidate has strong knowledge of HTML5, REST API, and Agile."
        
        result = extractor.extract(text)
        
        found_ids = [e.skill_id for e in result.entities]
        found_names = [e.canonical_name for e in result.entities]
        
        print(f"Input Text: '{text}'")
        print(f"Extracted IDs: {found_ids}")
        print(f"Extracted Names: {found_names}")
        
        # Checks
        if 'html5' in found_ids:
            print("✅ HTML5 found!")
        else:
            print("❌ HTML5 NOT found!")
            
        if 'rest_api' in found_ids:
            print("✅ REST API found!")
        else:
            print("❌ REST API NOT found!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_extraction_fix()
