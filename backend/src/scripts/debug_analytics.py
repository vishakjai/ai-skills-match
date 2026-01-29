import asyncio
import os
import sys
sys.path.append(os.getcwd())

from src.core.models import CandidateProfile, TimelineEntry, CandidateMetadata, ComputedCandidateStats, TimelineSkill
from src.core.analytics import calculate_analytics
from src.core.graph import ontology

def test_analytics():
    print("🔬 Debugging Analytics (Time Aware Logic)...")
    
    # Load Ontology
    db_url = os.environ.get("SUPABASE_URL")
    if db_url:
        ontology.load_from_db(db_url)
        
    # Create Candidate with Overlapping Jobs
    c = CandidateProfile(
        id="c_overlap",
        candidate_metadata=CandidateMetadata(),
        computed_stats=ComputedCandidateStats(),
        skills=[],
        timeline=[
            # Job A: Jan 2020 - Dec 2020 (12 months)
            TimelineEntry(
                employer="Company A",
                title="Dev",
                start_date="2020-01",
                end_date="2020-12",
                description="Python dev",
                extracted_skills=[TimelineSkill(skill_id="python")]
            ),
            # Job B: Jun 2020 - Jun 2021 (13 months)
            TimelineEntry(
                employer="Company B",
                title="Consultant",
                start_date="2020-06",
                end_date="2021-06",
                description="More Python",
                extracted_skills=[TimelineSkill(skill_id="python")]
            )
        ]
    )
    
    # Run Analytics
    updated_c = calculate_analytics(c)
    
    # Check Python Experience
    python_exp = 0
    for sp in updated_c.skill_profile:
        if sp.skill_slug == "python":
            python_exp = sp.total_months
            
    print(f"\n🐍 Python Experience: {python_exp} months")
    
    # Expected: 2020-01 to 2021-06 = 18 months overlap logic.
    # Naive Sum: 12 + 13 = 25 months.
    
    if 17 <= python_exp <= 19:
        print("✅ SUCCESS: Overlap handled correctly (approx 18 months)")
    else:
        print(f"❌ FAILURE: Expected ~18, got {python_exp}")

if __name__ == "__main__":
    test_analytics()
