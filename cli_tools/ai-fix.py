#!/usr/bin/env python3
import sys
import requests
import json

# Matches your backend endpoint exactly
URL = "http://localhost:8000/fix-code"

def main():
    if len(sys.argv) < 3:
        print("❌ Usage: ai-fix \"<your_code>\" \"<instructions>\"")
        sys.exit(1)

    payload = {
        "file_code": sys.argv[1],       # matches FixRequest.file_code in backend
        "instructions": sys.argv[2]     # matches FixRequest.instructions in backend
    }

    try:
        # Increased timeout to 90 sec to prevent Request timed out errors
        r = requests.post(URL, json=payload, timeout=200)
    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Unable to connect to backend. Make sure Codemaster-AI is running.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out. Backend may be busy or processing a large model output.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Unexpected request error: {e}")
        sys.exit(1)

    if not r.ok:
        print(f"❌ ERROR: Backend returned HTTP {r.status_code}")
        print("Details:", r.text.strip())
        sys.exit(1)

    try:
        resp = r.json()
    except json.JSONDecodeError:
        print("❌ ERROR: Backend did not return valid JSON.")
        print("Raw Response:", r.text.strip())
        sys.exit(1)

    if resp.get("code"):
        print("✅ Fixed Code:\n")
        print(resp["code"])
    elif resp.get("detail"):
        print(f"❌ Backend reported: {resp['detail']}")
    elif resp.get("error"):
        print(f"❌ Backend error: {resp['error']}")
        if "details" in resp:
            print("Details:", resp["details"])
    else:
        print("⚠️ Unexpected Response from backend:")
        print(json.dumps(resp, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
