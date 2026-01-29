import requests
import time
import sys

# Constants
BASE_URL = "http://localhost:8000"
JD_TEXT = """
Senior Python Developer
London (Remote)
Must have: Python (Expert), Django, PostgreSQL.
Nice to have: AWS, Kubernetes.
"""

RESUME_1 = """
Alice Pythonista
London
Skills: Python, Django, PostgreSQL, AWS
Experience: Senior Dev at TechCorp (5 years)
"""

RESUME_2 = """
Bob Java
Boston
Skills: Java, Spring Boot, MySQL
Experience: Junior Dev (1 year)
"""

def create_files():
    # Write mock files to disk so requests can read them
    with open("alice_resume.txt", "w") as f: f.write(RESUME_1)
    with open("bob_resume.txt", "w") as f: f.write(RESUME_2)

def run_test():
    create_files()
    
    print(f"🚀 Submitting Batch to {BASE_URL}...")
    
    files = [
        ('files', ('alice_resume.txt', open('alice_resume.txt', 'rb'), 'text/plain')),
        ('files', ('bob_resume.txt', open('bob_resume.txt', 'rb'), 'text/plain'))
    ]
    data = {'jd': JD_TEXT}
    
    try:
        res = requests.post(f"{BASE_URL}/batch/upload", files=files, data=data)
        if res.status_code != 200:
            print(f"❌ Upload Failed: {res.text}")
            return
            
        json_resp = res.json()
        batch_id = json_resp['batch_id']
        print(f"✅ Batch Submitted! ID: {batch_id}")
        
        # Poll
        while True:
            status_res = requests.get(f"{BASE_URL}/batch/{batch_id}")
            if status_res.status_code != 200:
                print(f"❌ Poll Failed: {status_res.text}")
                break
                
            status_json = status_res.json()
            state = status_json['status']['status']
            processed = status_json['status']['processed_count']
            total = status_json['status']['total_files']
            
            print(f"⏳ Status: {state.upper()} ({processed}/{total})")
            
            if state in ['completed', 'failed']:
                print("\n🏁 FINAL RESULTS:")
                for cand in status_json['candidates']:
                    print(f"  - {cand['name']}: {cand['total_score']} ({cand['tribunal_status']})")
                    print(f"    Missing: {cand['missing_critical_skills']}")
                break
            
            time.sleep(2)
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    run_test()
