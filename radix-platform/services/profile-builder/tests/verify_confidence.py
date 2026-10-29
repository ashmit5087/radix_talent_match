import urllib.request
import json

base = 'http://localhost:8000/api/v1/profiles'

# Test 1: float confidence
p1 = {
    'personal_info': {'full_name': 'Confidence Float Test', 'email': 'cfloat@example.com'},
    'skills': [{'skill_name': 'Python', 'category_code': 'COD', 'evidence': 'FastAPI work', 'confidence': 0.95}]
}
req = urllib.request.Request(base, data=json.dumps(p1).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as resp:
    data1 = json.loads(resp.read().decode('utf-8'))
    s1 = data1['skills'][0]
    print(f"Request: confidence=0.95 (float) -> Response: {s1['confidence']} ({type(s1['confidence']).__name__})")

# Test 2: string categorical confidence "high"
p2 = {
    'personal_info': {'full_name': 'Confidence String Test', 'email': 'cstring@example.com'},
    'skills': [{'skill_name': 'Python', 'category_code': 'COD', 'evidence': 'FastAPI work', 'confidence': 'high'}]
}
req = urllib.request.Request(base, data=json.dumps(p2).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as resp:
    data2 = json.loads(resp.read().decode('utf-8'))
    s2 = data2['skills'][0]
    print(f"Request: confidence='high' (str) -> Response: {s2['confidence']} ({type(s2['confidence']).__name__})")

# Test 3: numeric string "0.85"
p3 = {
    'personal_info': {'full_name': 'Confidence NumStr Test', 'email': 'cnumstr@example.com'},
    'skills': [{'skill_name': 'Python', 'category_code': 'COD', 'evidence': 'FastAPI work', 'confidence': '0.85'}]
}
req = urllib.request.Request(base, data=json.dumps(p3).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as resp:
    data3 = json.loads(resp.read().decode('utf-8'))
    s3 = data3['skills'][0]
    print(f"Request: confidence='0.85' (str) -> Response: {s3['confidence']} ({type(s3['confidence']).__name__})")
