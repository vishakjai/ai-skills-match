import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.graph import ontology

def test_ontology():
    # Load env for DB URL
    load_dotenv()
    db_url = os.getenv("SUPABASE_URL")
    if not db_url:
        print("❌ SUPABASE_URL not found")
        return

    # Load from DB
    ontology.load_from_db(db_url)
    
    # Test Cases
    test_cases = {
        'Agile Methodology': 'agile',
        'Scrum Master': 'scrum',
        'GitHub': 'git',
        'Git': 'git',
        'Rest': 'rest_api',
        'RESTful': 'rest_api',
        'Http': 'http',
        'ReactJS': 'react',
        'aws': 'aws'
    }

    print("\n🔍 Verifying Aliases...")
    failed = 0
    for alias, expected in test_cases.items():
        resolved = ontology.resolve_alias(alias)
        if resolved == expected:
            print(f"✅ '{alias}' -> '{resolved}'")
        else:
            print(f"❌ '{alias}' -> '{resolved}' (Expected: '{expected}')")
            failed += 1
    
    if failed == 0:
        print("\n✨ All alias tests passed!")
    else:
        print(f"\n⚠️ {failed} alias tests failed.")

if __name__ == "__main__":
    test_ontology()
