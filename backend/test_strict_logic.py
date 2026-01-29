import asyncio
import sys
import os

# Ensure backend dir is in path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.core.models import (
    CandidateProfile, JobDescription, CandidateSkill, ComputedStats, 
    JobMetadata, GatingRules, Requirement, SenioritySignals,
    TimelineEntry, SkillProfileEntry, CandidateMetadata, ComputedCandidateStats,
    EducationEntry
)
from src.core.engine import calculate_match

async def run_tests():
    print("🚀 Starting Logic Verification Tests...")

    # --- SETUP BASE OBJECTS ---
    base_candidate = CandidateProfile(
        id="c1",
        is_valid=True,
        candidate_metadata=CandidateMetadata(name="Tester", location="New York"),
        computed_stats=ComputedCandidateStats(total_yoe=5),
        education=[],
        skill_profile=[],
        timeline=[],
        skills=[]
    )
    
    base_jd = JobDescription(
        id="j1",
        is_valid=True,
        job_metadata=JobMetadata(title="Dev", location="New York", work_mode="onsite"),
        gating_rules=GatingRules(),
        requirements=[],
        seniority_signals=SenioritySignals(target_level="mid")
    )

    # --- TEST 1: STRICT EDUCATION ---
    print("\n🧪 Test 1: Strict Education Filter")
    jd1 = base_jd.model_copy(deep=True)
    jd1.gating_rules.education_min = "Bachelors"
    jd1.gating_rules.education_strict = True
    
    cand1 = base_candidate.model_copy(deep=True)
    # No education
    
    res1 = await calculate_match(cand1, jd1)
    print(f"   Score: {res1.score}")
    
    edu_status = [a.status for a in res1.analysis if a.title == "Education"][0]
    print(f"   Edu Status: {edu_status}")
    
    if res1.score <= 40.0 and edu_status == "not_met":
        print("   ✅ PASS: Strict Education Enforced")
    else:
        print(f"   ❌ FAIL: Score {res1.score}, Status {edu_status}")


    # --- TEST 2: HARD SKILL FILTER ---
    print("\n🧪 Test 2: Hard Skill Filter (Missing Python)")
    jd2 = base_jd.model_copy(deep=True)
    jd2.requirements = [
        Requirement(req_id="r1", skill_id="Python", priority="must_have", is_hard_filter=True)
    ]
    
    cand2 = base_candidate.model_copy(deep=True)
    # No skills
    
    res2 = await calculate_match(cand2, jd2)
    print(f"   Score: {res2.score}")
    missing_trace = [t for t in res2.technical_trace if t.skill_slug == "python"]
    print(f"   Trace: {missing_trace[0].status if missing_trace else 'None'}")
    
    if res2.score <= 40.0:
        print("   ✅ PASS: Hard Skill Filter Enforced (Score Capped)")
    else:
        print(f"   ❌ FAIL: Score {res2.score} (Should be <= 40)")


    # --- TEST 3: LEVEL PENALTY ---
    print("\n🧪 Test 3: Level Penalty (Senior Req vs Junior Cand)")
    jd3 = base_jd.model_copy(deep=True)
    jd3.requirements = [
        Requirement(req_id="r1", skill_id="Python", priority="must_have", level="senior", is_hard_filter=False)
    ]
    
    cand3 = base_candidate.model_copy(deep=True)
    cand3.skill_profile = [
        SkillProfileEntry(skill_slug="python", total_months=12, competency_level="junior")
    ]
    # Need to populate 'skills' map logic inside engine uses 'skill_profile' or 'skills'? 
    # Engine uses 'candidate_skills_map' built from 'skill_profile' AND 'skills' list.
    # Let's populate 'skills' too to be safe/consistent
    cand3.skills = [
        CandidateSkill(skill_id="python", computed_stats=ComputedStats(evidence_confidence=1.0), evidence_sources=[])
    ]
    
    res3 = await calculate_match(cand3, jd3)
    print(f"   Score: {res3.score}")
    # Python item
    py_trace = [t for t in res3.technical_trace if t.skill_slug == "python"][0]
    print(f"   Trace Score: {py_trace.score}")
    print(f"   Trace Seniority: {py_trace.seniority_level}")
    
    print("   --- Breakdown ---")
    for a in res3.analysis:
        print(f"   {a.title}: {a.status} ({a.summary})")
    
    # Check trace item details
    # Logic:
    # 10 (Comp) + 10 (Exp - default met) + 10 (Edu - default met or review) 
    # + 20 (Pref - default met if empty) + 25 (Req - 0.5 * 50).
    # Total = 75.
    # If penalty NOT applied: Total = 100.
    # So 75 proves the penalty is working (25 pts deduction).

    if 74 <= res3.score <= 76:
        print("   ✅ PASS: Level Penalty Applied (Score ~75, down from 100)")
    else:
        print(f"   ❌ FAIL: Score {res3.score} (Expected ~75)")

if __name__ == "__main__":
    asyncio.run(run_tests())
