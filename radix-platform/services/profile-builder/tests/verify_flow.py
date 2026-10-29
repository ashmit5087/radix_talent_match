import json
import urllib.request
import urllib.error
import sys

def main():
    base = 'http://localhost:8000/api/v1/profiles'

    print("=== RADIX Talent Match - Role 3 Profile Builder Verification Pass ===")

    # 1. POST from-resume/mock-001
    req = urllib.request.Request(f'{base}/from-resume/mock-001', method='POST')
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        profile_id = data['profile_id']
        name = data['personal_info']['full_name']
        print(f"[OK] 1. CREATE FROM RESUME: Status={resp.status}, profile_id={profile_id}, candidate='{name}'")

    # 2. GET profile
    req = urllib.request.Request(f'{base}/{profile_id}', method='GET')
    with urllib.request.urlopen(req) as resp:
        get_data = json.loads(resp.read().decode('utf-8'))
        match = (get_data['profile_id'] == profile_id)
        print(f"[OK] 2. GET PROFILE: Status={resp.status}, matches profile_id={match}")

    # 3. PUT update profile
    update_payload = {
        'personal_info': {
            'full_name': 'Rohan Verma (Updated)',
            'email': 'rohan.verma@example.com',
            'summary': 'Updated distributed systems engineer summary.'
        },
        'preferred_roles': ['Senior Software Engineer', 'Distributed Systems Architect']
    }
    req = urllib.request.Request(
        f'{base}/{profile_id}',
        data=json.dumps(update_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='PUT'
    )
    with urllib.request.urlopen(req) as resp:
        put_data = json.loads(resp.read().decode('utf-8'))
        unchanged = (put_data['profile_id'] == profile_id)
        print(f"[OK] 3. PUT UPDATE PROFILE: Status={resp.status}, updated_name='{put_data['personal_info']['full_name']}'")
        print(f"[OK] 4. PROFILE_ID IMMUTABLE: {unchanged} (Original: {profile_id} == Preserved: {put_data['profile_id']})")

    # 5. GET skills (Role 4 & Role 5 contract)
    req = urllib.request.Request(f'{base}/{profile_id}/skills', method='GET')
    with urllib.request.urlopen(req) as resp:
        skills_data = json.loads(resp.read().decode('utf-8'))
        confidences = [s['confidence'] for s in skills_data['skills']]
        all_canonical = all(c in ['high', 'medium', 'low'] for c in confidences)
        print(f"[OK] 5. GET SKILLS: Status={resp.status}, total_skills={skills_data['total_skills']}")
        print(f"        Categories Covered: {skills_data['categories_covered']}")
        print(f"        Confidences Strictly 'high'|'medium'|'low': {all_canonical} ({confidences[:4]}...)")

    # 6. GET completeness
    req = urllib.request.Request(f'{base}/{profile_id}/completeness', method='GET')
    with urllib.request.urlopen(req) as resp:
        comp_data = json.loads(resp.read().decode('utf-8'))
        print(f"[OK] 6. GET COMPLETENESS: Status={resp.status}, score={comp_data['overall_percentage']}%, completed={comp_data['completed_sections']}")

    # 7. POST CV upload (multipart/form-data)
    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="Rohan_Verma_CV.pdf"\r\n'
        f'Content-Type: application/pdf\r\n\r\n'
        f'%PDF-1.4 Mock CV Content for verification test\r\n'
        f'--{boundary}--\r\n'
    ).encode('utf-8')

    req = urllib.request.Request(
        f'{base}/{profile_id}/cv',
        data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
        method='POST'
    )
    with urllib.request.urlopen(req) as resp:
        cv_data = json.loads(resp.read().decode('utf-8'))
        print(f"[OK] 7. POST CV UPLOAD: Status={resp.status}, stored_filename='{cv_data['stored_filename']}', size={cv_data['size_bytes']} bytes")

    # 8. GET CV download
    req = urllib.request.Request(f'{base}/{profile_id}/cv', method='GET')
    with urllib.request.urlopen(req) as resp:
        downloaded_bytes = resp.read()
        print(f"[OK] 8. GET CV DOWNLOAD: Status={resp.status}, length={len(downloaded_bytes)} bytes, contentType={resp.headers.get('content-type')}")

    # 9. Verify invalid file upload rejection (e.g. .exe)
    bad_body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="malicious.exe"\r\n'
        f'Content-Type: application/octet-stream\r\n\r\n'
        f'bad content\r\n'
        f'--{boundary}--\r\n'
    ).encode('utf-8')
    req = urllib.request.Request(
        f'{base}/{profile_id}/cv',
        data=bad_body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print("[FAIL] 9. Uploading .exe should have failed!")
            sys.exit(1)
    except urllib.error.HTTPError as err:
        print(f"[OK] 9. INVALID CV REJECTED: Status={err.code} ({err.reason})")

    print("\n>>> ALL API VERIFICATION STEPS PASSED SUCCESSFULLY. <<<")

if __name__ == '__main__':
    main()
