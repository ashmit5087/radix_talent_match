# ============================================================
# RADIX Platform — Start All Services
# Open 6 separate terminal windows, paste one command in each
# ============================================================

# TERMINAL 1 — Role 1: JD Analytics (port 8001)
cd "C:\Users\GAMER\Desktop\bootcamp hackathon\candidate-assessment-platform\radix-platform\services\role-1-jd-analytics"
.\.venv\Scripts\uvicorn.exe app.main:app --port 8001 --host 0.0.0.0 --reload

# ─────────────────────────────────────────────────────────────

# TERMINAL 2 — Role 2: Resume Parsing (port 8002)
cd "C:\Users\GAMER\Desktop\bootcamp hackathon\candidate-assessment-platform\radix-platform\services\role-2-resume-parsing"
.\.venv\Scripts\uvicorn.exe api_server:app --port 8002 --host 0.0.0.0 --reload

# ─────────────────────────────────────────────────────────────

# TERMINAL 3 — Role 3: Profile Builder (port 8003)
cd "C:\Users\GAMER\Desktop\bootcamp hackathon\candidate-assessment-platform\radix-platform\services\role-3-profile-builder"
.\.venv\Scripts\uvicorn.exe main:app --port 8003 --host 0.0.0.0 --reload

# ─────────────────────────────────────────────────────────────

# TERMINAL 4 — Role 4: Talent Check (port 8004)
cd "C:\Users\GAMER\Desktop\bootcamp hackathon\candidate-assessment-platform\radix-platform\services\role-4-talent-check"
.\.venv\Scripts\uvicorn.exe talent_check.backend.api:app --port 8004 --host 0.0.0.0 --reload

# ─────────────────────────────────────────────────────────────

# TERMINAL 5 — Role 5: Skill Matching (port 8005)
cd "C:\Users\GAMER\Desktop\bootcamp hackathon\candidate-assessment-platform\radix-platform\services\role-5-skill-matching"
.\.venv\Scripts\uvicorn.exe skill_matching.api:app --port 8005 --host 0.0.0.0 --reload

# ─────────────────────────────────────────────────────────────

# TERMINAL 6 — Frontend (port 5173)
cd "C:\Users\GAMER\Desktop\bootcamp hackathon\candidate-assessment-platform\radix-platform\frontend"
npm run dev

