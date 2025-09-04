import requests
r = requests.post("http://localhost:8000/deactivate")
print(r.json())
