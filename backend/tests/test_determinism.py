import pytest
from src.core.models import CandidateProfile, JobDescription, CandidateSkill, ComputedStats
from src.core.engine import calculate_match

def create_candidate(skills: list[str]) -> CandidateProfile:
    c_skills = [
        CandidateSkill(
            skill_id=s,
            computed_stats=ComputedStats(months_experience=12, evidence_confidence=1.0)
        ) for s in skills
    ]
    return CandidateProfile(id="test_cand", skills=c_skills)

def create_jd(req: list[str], pref: list[str]) -> JobDescription:
    return JobDescription(id="test_jd", required_skills=req, preferred_skills=pref)

def test_perfect_match():
    c = create_candidate(["python", "fastapi"])
    jd = create_jd(["python"], ["fastapi"])
    
    result = calculate_match(c, jd)
    assert result.score == 100.0
    assert result.explanation.matched_required == ["python"]
    assert result.explanation.matched_preferred == ["fastapi"]

def test_normalization():
    # Candidate has "node_js", JD asks for "Node.js"
    # normalize_skill("Node.js") -> "node_js"
    c = create_candidate(["node_js"]) 
    jd = create_jd(["Node.js"], [])
    
    result = calculate_match(c, jd)
    assert result.score == 100.0, "Normalization failed to align 'Node.js' with 'node_js'"

def test_partial_match():
    # 2 Required: Python, Go. Candidate has Python.
    # Score should be 50% of the Required Component (70 pts) + 0% of Preferred (30 pts) -> 35.0
    c = create_candidate(["python"])
    jd = create_jd(["python", "go"], [])
    
    result = calculate_match(c, jd)
    
    # Required component is 70 points. We have 1/2. So 35 points.
    # Preferred component is 30 points. We have 0/0 -> Actually, logic says if req matches, bonus?
    # Wait, if preferred list is empty, calculate_match gives full preferred score (30) if reqs exist?
    # Let's check logic:
    # "if req_ids: pref_score = MAX_PREF_SCORE" if pref_ids is empty.
    # So score should be 35 + 30 = 65.
    
    assert result.score == 65.0

def test_determinism():
    c = create_candidate(["python", "docker", "k8s"])
    jd = create_jd(["python", "docker"], ["aws"])
    
    initial_result = calculate_match(c, jd)
    
    for _ in range(100):
        new_result = calculate_match(c, jd)
        assert new_result.score == initial_result.score
        assert new_result.explanation == initial_result.explanation
