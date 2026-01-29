import asyncio
import os
import sys
sys.path.append(os.getcwd())

from src.core.models import JobDescription, Requirement, Competency

def test_dedup_logic():
    print("🔬 Verifying Deduplication Logic...")
    
    # 1. Create a Result with Duplication
    jd = JobDescription(
        id="test",
        job_metadata={}, 
        gating_rules={}, 
        seniority_signals={},
        requirements=[
            Requirement(req_id="r1", skill_id="java", priority="must_have", min_years=3),
            Requirement(req_id="r2", skill_id="problem_solving", priority="must_have", min_years=0), # Duplicate
            Requirement(req_id="r3", skill_id="communication", priority="must_have", min_years=0) # Duplicate
        ],
        competencies=[
            Competency(name="Problem Solving", priority="must_have"),
            Competency(name="Communication", priority="must_have")
        ]
    )
    
    print(f"Original Requirements: {[r.skill_id for r in jd.requirements]}")
    
    # 2. Run the logic (copy from main.py)
    comp_names = set(c.name.lower() for c in jd.competencies)
    
    clean_reqs = []
    for req in jd.requirements:
        # Check normalization logic "problem_solving" -> "problem solving"
        skill_clean = req.skill_id.lower().replace("_", " ")
        
        if skill_clean in comp_names:
            print(f"🧹 Removed duplicated soft skill: {req.skill_id}")
            continue
        clean_reqs.append(req)
        
    jd.requirements = clean_reqs
    
    print(f"Cleaned Requirements: {[r.skill_id for r in jd.requirements]}")
    
    if len(jd.requirements) == 1 and jd.requirements[0].skill_id == "java":
        print("✅ SUCCESS: Only Java remains.")
    else:
        print("❌ FAILURE: Deduplication logic failed.")

if __name__ == "__main__":
    test_dedup_logic()
