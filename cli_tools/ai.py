import sys
import requests
import json

if len(sys.argv) < 2:
    print("Usage: ai \"your request here\"")
    sys.exit(1)

prompt = sys.argv[1]
try:
    r = requests.post(
        "http://localhost:8000/generate-code",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"prompt": prompt})
    )
    r.raise_for_status()
    response_json = r.json()
    if "code" in response_json:
        print(response_json["code"])
    else:
        print("No 'code' in response:", response_json)
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
except json.JSONDecodeError:
    print("Failed to decode JSON response")
