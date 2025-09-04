import requests
r = requests.post("http://localhost:8000/activate")
print(r.json())
