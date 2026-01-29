import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.graph import ontology

def test_inference():
    # Load env for DB URL
    load_dotenv()
    db_url = os.getenv("SUPABASE_URL")
    if not db_url:
        print("❌ SUPABASE_URL not found")
        return

    # Load from DB
    ontology.load_from_db(db_url)
    
    # Test Inference Logic
    # Scenario: JD requires 'sdlc' (Parent). Candidate has 'agile' (Child).
    # Expected: get_related_scores('sdlc', ['agile']) should return > 0 for agile.
    
    print("\n🔍 Verifying Implicit Match Inference...")
    
    # Check Graph Edges directly first
    # We expect 'agile' -> 'sdlc' with type 'implies'
    if ontology.graph.has_edge('agile', 'sdlc'):
        edge_data = ontology.graph.get_edge_data('agile', 'sdlc')
        print(f"✅ Edge Exists: Agile -> SDLC ({edge_data})")
    else:
        print("❌ Edge Missing: Agile -> SDLC")

    if ontology.graph.has_edge('git', 'version_control'):
        edge_data = ontology.graph.get_edge_data('git', 'version_control')
        print(f"✅ Edge Exists: Git -> Version Control ({edge_data})")
    else:
        print("❌ Edge Missing: Git -> Version Control")

    # Check Traversal Logic using get_related_scores
    # If I require 'sdlc', does 'agile' score?
    # get_related_scores(req_skill, candidate_skills)
    # returns float (max score)
    
    score_sdlc = ontology.get_related_scores('sdlc', ['agile', 'python'])
    if score_sdlc > 0:
        print(f"✅ Inference Match: Candidate 'agile' satisfies Requirement 'sdlc' (Score: {score_sdlc})")
    else:
         print(f"❌ Inference Failed: Candidate 'agile' did NOT match 'sdlc'")

    score_vcs = ontology.get_related_scores('version_control', ['git', 'java'])
    if score_vcs > 0:
        print(f"✅ Inference Match: Candidate 'git' satisfies Requirement 'version_control' (Score: {score_vcs})")
    else:
         print(f"❌ Inference Failed: Candidate 'git' did NOT match 'version_control'")

if __name__ == "__main__":
    test_inference()
