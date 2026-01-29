import asyncio
import os
import sys
# Add logic to append project root to path
sys.path.append(os.getcwd())

from src.core.models import CandidateProfile, JobDescription, CandidateSkill, ComputedStats, JobMetadata, GatingRules, Requirement, SenioritySignals, CandidateMetadata, ComputedCandidateStats
from src.core.engine import calculate_match
from src.core.graph import ontology

async def test_matching():
    print("🔬 Debugging Matching Logic...")
    
    # 1. Load Ontology
    db_url = os.environ.get("SUPABASE_URL")
    if db_url:
        ontology.load_from_db(db_url)
    else:
        print("⚠️ No DB URL, Ontology Empty.")

    # 2. Mock Candidate (What we expect the resume to have)
    cand = CandidateProfile(
        id="c1",
        candidate_metadata=CandidateMetadata(),
        computed_stats=ComputedCandidateStats(),
        skills=[
            CandidateSkill(skill_id="html", computed_stats=ComputedStats(months_experience=24, evidence_confidence=1.0)), # Canonical "html5"? Or Alias "html"?
            CandidateSkill(skill_id="git", computed_stats=ComputedStats(months_experience=24, evidence_confidence=1.0)),
            CandidateSkill(skill_id="javascript", computed_stats=ComputedStats(months_experience=60, evidence_confidence=1.0)),
            CandidateSkill(skill_id="css3", computed_stats=ComputedStats(months_experience=24, evidence_confidence=1.0)),
            CandidateSkill(skill_id="rest_api", computed_stats=ComputedStats(months_experience=24, evidence_confidence=1.0)),
        ]
    )
    
    # 3. Mock JD (What we see in the screenshot - Red items)
    jd = JobDescription(
        id="j1",
        job_metadata=JobMetadata(title="Test Role", location="Remote", clearance="None"),
        gating_rules=GatingRules(),
        requirements=[
            Requirement(req_id="r1", skill_id="Html5", priority="must_have", min_years=1), # Capitalized logic?
            Requirement(req_id="r2", skill_id="Git", priority="must_have", min_years=1),
            Requirement(req_id="r3", skill_id="Http", priority="must_have", min_years=1),
            Requirement(req_id="r4", skill_id="Javascript", priority="must_have", min_years=1), # Green
        ],
        seniority_signals=SenioritySignals(target_level="Mid")
    )
    
    # 4. Run Match
    result = calculate_match(cand, jd)
    
    # 5. Inspect Trace
    print("\n📊 Score:", result.score)
    print("\nTrace:")
    for item in result.explanation.required_trace:
        print(f" - {item.skill_slug}: {item.status} (Score: {item.score:.2f})")
        if item.status == "missing":
            print(f"   ❌ FAILED TO MATCH: {item.skill_slug}")
        else:
            print(f"   ✅ MATCHED: {item.skill_slug}")

if __name__ == "__main__":
    asyncio.run(test_matching())
