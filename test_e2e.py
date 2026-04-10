import os
import requests
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_ingest():
    print("Testing GET /ingest (rbi)...")
    resp = requests.get(f"{BASE_URL}/ingest?source=rbi")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Ingestion success: found {len(data['pdf_links'])} links.")
    else:
        print(f"❌ Ingestion failed: {resp.text}")
        
def test_upload_and_run():
    print("\nTesting POST /upload and /run...")
    # Get the sample PDFs in data/demo/
    old_pdf = Path("data/demo/rbi_circular_2024_old.pdf")
    new_pdf = Path("data/demo/rbi_circular_2025_new.pdf")
    
    with open(old_pdf, "rb") as f_old, open(new_pdf, "rb") as f_new:
        files = {
            "old_pdf": (old_pdf.name, f_old, "application/pdf"),
            "new_pdf": (new_pdf.name, f_new, "application/pdf")
        }
        resp = requests.post(f"{BASE_URL}/upload", files=files)
        
    assert resp.status_code == 200, f"Upload failed: {resp.text}"
    session_id = resp.json()["session_id"]
    print(f"✅ Upload success. Session ID: {session_id}")
    
    print("\nCalling POST /run (this will take 10-20 seconds to run the 8 LangGraph agents)...")
    t0 = time.time()
    resp_run = requests.post(f"{BASE_URL}/run", data={"session_id": session_id})
    duration = time.time() - t0
    
    assert resp_run.status_code == 200, f"Run failed: {resp_run.text}"
    print(f"✅ Pipeline complete in {duration:.1f} seconds!")
    
    data = resp_run.json()
    print("Report Stats:", data.get("stats"))
    print("Extracted Deadlines:", json_to_str(data.get("all_deadlines")))
    
    return session_id, data

def test_risk_score():
    print("\nTesting POST /risk-score...")
    change = {
        "type": "MODIFIED",
        "section": "LCR Computation",
        "old": "LCR buffer should be maintained at 100%.",
        "new": "LCR buffer must be raised to 110% effective immediately to avoid non-compliance penalties.",
        "summary": "Increased buffer requirement"
    }
    resp = requests.post(f"{BASE_URL}/risk-score", json=change)
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Risk Score: {data['risk_level']} ({data['risk_score']})")
    else:
        print(f"❌ Risk Score failed: {resp.text}")

def test_summary():
    print("\nTesting POST /summary...")
    change = {
        "type": "MODIFIED",
        "section": "LCR Computation",
        "old": "LCR buffer should be maintained at 100%.",
        "new": "LCR buffer must be raised to 110% effective immediately to avoid non-compliance penalties.",
        "risk": "HIGH",
        "summary": "Increased buffer requirement"
    }
    resp = requests.post(f"{BASE_URL}/summary", json=change)
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Summary Generated:\n   {data['summary'][:150]}...")
    else:
        print(f"❌ Summary Generation failed: {resp.text}")

def json_to_str(obj):
    import json
    return json.dumps(obj)

if __name__ == "__main__":
    try:
        requests.get(f"{BASE_URL}/health")
    except requests.exceptions.ConnectionError:
        print("Backend server is not running on port 8000. Start it first.")
        exit(1)
        
    test_ingest()
    session_id, run_data = test_upload_and_run()
    test_risk_score()
    test_summary()
    print("\nAll End-to-End API tests completed successfully! 🎉")
