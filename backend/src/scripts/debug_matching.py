import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.graph import ontology

def debug_mismatch():
    # Load env for DB URL
    load_dotenv()
    db_url = os.getenv("SUPABASE_URL")
    if not db_url:
        print("❌ SUPABASE_URL not found")
        return

    # Load from DB
    ontology.load_from_db(db_url)
    
    print("\n🧐 Debugging Mismatches...")
    
    # CASE 1: HTML5
    # Hypothesis: JD wants 'html5', Candidate has 'html_css' (or 'HTML')
    req_slug = 'html5'
    
    # Test 1a: Candidate has 'html_css'
    cand_slugs_1 = {'html_css'}
    score_1 = ontology.get_related_scores(req_slug, cand_slugs_1)
    print(f"Test 1a: Req='{req_slug}' vs Cand={{'html_css'}} -> Score: {score_1}")
    
    # Test 1b: Candidate has 'html5' (should be 1.0)
    cand_slugs_2 = {'html5'}
    score_2 = ontology.get_related_scores(req_slug, cand_slugs_2)
    print(f"Test 1b: Req='{req_slug}' vs Cand={{'html5'}} -> Score: {score_2}")

    # Test 1c: Candidate has 'html' (alias check)
    alias_res = ontology.resolve_alias('HTML')
    print(f"Test 1c: 'HTML' resolves to -> '{alias_res}'")
    
    # CASE 2: REST API
    # Hypothesis: JD wants 'rest_api' (displayed as Rest Api), Candidate has ???
    req_slug_rest = 'rest_api'
    
    # Test 2a: Candidate has 'restful' (alias)
    alias_rest = ontology.resolve_alias('Restful')
    print(f"Test 2a: 'Restful' resolves to -> '{alias_rest}'")
    
    # Test 2b: Candidate has 'Rest Api' (Exact string)
    alias_rest_api = ontology.resolve_alias('Rest Api')
    print(f"Test 2b: 'Rest Api' resolves to -> '{alias_rest_api}'")

    # Test 2c: Edge Case?
    # Maybe JD has 'rest_api' but Candidate has 'http'?
    cand_slugs_rest = {'http'}
    score_rest = ontology.get_related_scores(req_slug_rest, cand_slugs_rest)
    print(f"Test 2c: Req='{req_slug_rest}' vs Cand={{'http'}} -> Score: {score_rest}")

if __name__ == "__main__":
    debug_mismatch()
