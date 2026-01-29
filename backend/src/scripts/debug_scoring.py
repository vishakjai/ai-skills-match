import asyncio
import os
import sys
sys.path.append(os.getcwd())

from src.core.models import CandidateProfile, JobDescription, Requirement, JobMetadata, GatingRules, SenioritySignals, CandidateMetadata, ComputedCandidateStats, TimelineEntry, TimelineSkill, SkillProfileEntry, Competency
from src.core.engine import calculate_match

def test_scoring():
    print("🔬 Debugging Scoring Engine...")
    
    # 1. Create Mock JD (Senior Java)
    jd = JobDescription(
        id="jd_1",
        job_metadata=JobMetadata(title="Senior Java Dev"),
        gating_rules=GatingRules(education_min="Bachelors"),
        requirements=[
            Requirement(req_id="r1", skill_id="java", priority="must_have", min_years=5),
            Requirement(req_id="r2", skill_id="python", priority="nice_to_have", min_years=2)
        ],
        seniority_signals=SenioritySignals(target_level="senior"),
        competencies=[
            Competency(name="Communication", priority="must_have"),
            Competency(name="Leadership", priority="must_have")
        ]
    )
    
    # 2. Create Mock Candidate (Mid-Level, Missing Leadership)
    cand = CandidateProfile(
        id="c_1",
        candidate_metadata=CandidateMetadata(name="Mid Dev"),
        computed_stats=ComputedCandidateStats(total_yoe=3.0),
        education=[], # Missing Degree -> Edu Score 0 or 5?
        skill_profile=[
            SkillProfileEntry(skill_slug="java", total_months=36, competency_level="mid", sources=["experience"])
        ],
        competencies=["Communication"], # Missing Leadership -> Comp Score 5/10
        timeline=[],
        skills=[]
    )
    
    # 3. Calculate Match
    result = calculate_match(cand, jd)
    
    print(f"\n🏆 Total Score: {result.score}")
    print("📊 Breakdown:")
    for k, v in result.explanation.score_breakdown.items():
        print(f"  - {k}: {v}")
        
    # Validation Logic
    # Edu: 0 (No degree)
    # Exp: 0 (3 years < 4 years for Senior) -> "not_met" -> 0.0
    # Comp: 5.0 (1/2 matched * 10)
    # Req: Java (Mid) vs Senior Target. Multiplier?
    #      Mid(2) vs Senior(3) -> Diff 1 -> 0.8 modifier.
    #      Score = 50 * 0.8 = 40.0?
    #      Actually weight per req = 50 / 1 = 50.
    #      Skill Score = 1.0 (Exact match) * 0.8 (Seniority) = 0.8
    #      Total Req = 50 * 0.8 = 40.0
    # Pref: Missing Python -> 0.0
    
    # Expected Total: 0 + 0 + 5.0 + 40.0 + 0 = 45.0
    
    if 44 <= result.score <= 46:
        print("✅ SUCCESS: Score is approx 45.0 as expected.")
    else:
        print(f"❌ FAILURE: Expected ~45.0, got {result.score}")

if __name__ == "__main__":
    test_scoring()
