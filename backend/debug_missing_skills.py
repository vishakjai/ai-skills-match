import asyncio
from src.core.models import CandidateProfile, JobDescription, CandidateSkill, Requirement, ComputedStats, JobMetadata, GatingRules, SenioritySignals
from src.core.engine import calculate_match

# Mock Data
candidate = CandidateProfile(
    id="debug_cand_1",
    candidate_metadata={"name": "Debug Candidate"},
    computed_stats={"total_yoe": 5, "avg_tenure_months": 24, "management_experience_years": 0},
    is_valid=True,
    skills=[
        CandidateSkill(skill_id="Git", computed_stats=ComputedStats(months_experience=12, recency_decay=1.0, evidence_confidence=1.0), evidence_sources=[]),
        CandidateSkill(skill_id="Maven", computed_stats=ComputedStats(months_experience=12, recency_decay=1.0, evidence_confidence=1.0), evidence_sources=[]),
        CandidateSkill(skill_id="Gradle", computed_stats=ComputedStats(months_experience=12, recency_decay=1.0, evidence_confidence=1.0), evidence_sources=[]),
        CandidateSkill(skill_id="AWS", computed_stats=ComputedStats(months_experience=12, recency_decay=1.0, evidence_confidence=1.0), evidence_sources=[]),
    ]
)

jd = JobDescription(
    id="debug_jd_1",
    job_metadata=JobMetadata(title="DevOps Engineer"),
    gating_rules=GatingRules(),
    seniority_signals=SenioritySignals(keywords_found=[]),
    is_valid=True,
    requirements=[
        Requirement(req_id="r1", skill_id="git", priority="must_have", min_years=1),
        Requirement(req_id="r2", skill_id="maven", priority="must_have", min_years=1),
        Requirement(req_id="r3", skill_id="gradle", priority="nice_to_have", min_years=1),
        Requirement(req_id="r4", skill_id="aws", priority="must_have", min_years=1),
    ]
)

async def test():
    print("🚀 Running Match Debug...")
    result = await calculate_match(candidate, jd)
    print(f"Score: {result.score}")
    
    print("\n--- Technical Trace ---")
    for trace in result.technical_trace:
        print(f"Skill: {trace.skill_slug} | Status: {trace.status} | Score: {trace.score}")

if __name__ == "__main__":
    asyncio.run(test())
