import urllib.request
import urllib.error
import json

base = 'http://localhost:8000/api/v1/profiles'
codes = ['COD', 'DSA', 'OOD', 'APTI', 'COMM', 'AI', 'CLOUD', 'SQL', 'SWE', 'SYSD', 'NETW', 'OS', 'OTHER']

accepted = []
for c in codes:
    payload = {
        'personal_info': {'full_name': f'Test {c}', 'email': f'test.{c.lower()}@example.com'},
        'skills': [{'skill_name': f'Skill {c}', 'category_code': c, 'evidence': 'test evidence', 'confidence': 0.8}]
    }
    req = urllib.request.Request(base, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 201:
                accepted.append(c)
    except Exception as e:
        print(f'Failed on {c}: {e}')

print('Accepted categories count:', len(accepted))
print('Accepted categories list:', accepted)
print('OTHER explicitly supported:', 'OTHER' in accepted)

# Test invalid code
bad_payload = {
    'personal_info': {'full_name': 'Bad Code', 'email': 'bad@example.com'},
    'skills': [{'skill_name': 'Bad Skill', 'category_code': 'INVALID_XXX', 'evidence': 'test', 'confidence': 0.8}]
}
req = urllib.request.Request(base, data=json.dumps(bad_payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
try:
    with urllib.request.urlopen(req) as resp:
        print('Unexpected success for INVALID_XXX')
except urllib.error.HTTPError as e:
    print('INVALID_XXX properly rejected with status:', e.code)
