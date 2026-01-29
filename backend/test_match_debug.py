import requests
import json

API_URL = "http://localhost:8000/match"

candidate = {
  "id": "jane-doe",
  "candidate_metadata": {
    "name": "Jane Doe",
    "location": "Remote",
    "links": ["github.com/jane"]
  },
  "computed_stats": {
    "total_yoe": 6.0,
    "avg_tenure_months": 24,
    "management_experience_years": 1
  },
  "timeline": [
    {
      "company": "TechCorp",
      "title_raw": "Senior Engineer",
      "start_date": "2021-01",
      "end_date": "Present",
      "extracted_skills": [
        { "skill_id": "java", "context": "Backend API" },
        { "skill_id": "html5", "context": "Frontend" },
        { "skill_id": "javascript", "context": "Frontend" },
        { "skill_id": "git", "context": "Version Control" }
      ]
    }
  ],
  "skills": [],
  "competencies": ["Problem Solving", "Communication"]
}

jd = {
  "id": "senior-engineer-real",
  "job_metadata": {
    "title": "Senior Java Engineer",
    "location": "New York (Hybrid)",
    "clearance": "None"
  },
  "gating_rules": {
    "visa_sponsorship": True,
    "education_min": "Bachelors"
  },
  "requirements": [
    { "req_id": "r1", "skill_id": "java", "priority": "must_have", "min_years": 4 },
    { "req_id": "r6", "skill_id": "javascript", "priority": "must_have", "min_years": 2 }
  ],
  "seniority_signals": {
    "target_level": "Senior",
    "keywords_found": ["Lead", "Mentor"]
  },
  "competencies": []
}

try:
    print("🚀 Sending Request...")
    resp = requests.post(API_URL, json={"candidate": candidate, "job_description": jd})
    resp.raise_for_status()
    
    data = resp.json()
    print(f"✅ Status: {resp.status_code}")
    print(f"✅ Score: {data.get('score')}")
    
    print("\n🔍 Tribunal Verdict:")
    print(json.dumps(data.get('tribunal_verdict'), indent=2))
    
    print("\n🔍 Technical Trace (First 3 items):")
    trace = data.get('technical_trace', [])
    print(json.dumps(trace[:3], indent=2))
    
except Exception as e:
    print(f"❌ Error: {e}")
    if 'resp' in locals():
        print(f"Response text: {resp.text}")
