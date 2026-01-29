import httpx
import time
import sys

API_URL = "http://localhost:8000"

JD_TEXT = """
Job Title: Senior Python Developer
Location: Remote
Requirements:
- Must have 5+ years of Python experience.
- Experience with FastAPI and Asyncio.
- Nice to have: Docker and Kubernetes.
"""

RESUME_TEXT = """
Jane Doe
Software Engineer
Email: jane@example.com

Experience:
Senior Python Engineer at Tech Corp (2018 - Present)
- Built high-performance APIs using FastAPI and Python.
- Optimized database queries and deployed services using Docker.
- Led a team of 3 engineers.

Skills: Python, FastAPI, Docker, SQL, Git
"""

def run_smoke_test():
    print("🚀 Starting Batch Processing Smoke Test...")
    
    with httpx.Client(base_url=API_URL, timeout=60.0) as client:
        # 1. Submit Batch
        # Note: 'files' param for httpx takes (filename, content, content_type)
        files = {
            'files': ('resume_1.txt', RESUME_TEXT, 'text/plain')
        }
        data = {
            'jd': JD_TEXT
        }
        
        print("📤 Submitting Batch Job...")
        try:
            resp = client.post("/batch/upload", data=data, files=files)
            if resp.status_code != 200:
                print(f"❌ Submit Failed: {resp.status_code} - {resp.text}")
                return
                
            result = resp.json()
            batch_id = result['batch_id']
            print(f"✅ Batch Submitted! ID: {batch_id}")
            print(f"🔗 Poll URL: {result['poll_url']}")
            
        except httpx.ConnectError:
            print("❌ Connection Refused. Is the backend server running?")
            return

        # 2. Poll Status
        print("⏳ Polling for completion...")
        for i in range(20): # Try for 40 seconds
            time.sleep(2)
            resp = client.get(f"/batch/{batch_id}")
            if resp.status_code != 200:
                print(f"⚠️ Poll Failed: {resp.status_code}")
                continue
                
            status_data = resp.json()
            state = status_data['status']['status']
            processed = status_data['status']['processed_count']
            total = status_data['status']['total_files']
            
            print(f"   [{i*2}s] Status: {state} ({processed}/{total})")
            
            if state == 'completed':
                print("✅ Job Completed!")
                # Print Results
                candidates = status_data.get('candidates', [])
                if not candidates:
                    print("⚠️ No candidates found in result?")
                else:
                    print(f"\n📊 Results ({len(candidates)} candidates):")
                    for c in candidates:
                        print(f"   - {c['name']}: {c['total_score']} (Tribunal: {c['tribunal_status']})")
                        print(f"     Missing: {c['missing_critical_skills']}")
                break
            
            if state == 'failed':
                print("❌ Job Failed!")
                break
        else:
            print("❌ Timeout waiting for job completion.")

if __name__ == "__main__":
    run_smoke_test()
