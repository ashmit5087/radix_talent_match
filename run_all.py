#!/usr/bin/env python3
"""
RADIX Platform — Unified Single-Terminal Runner
Runs all 5 backend microservices + frontend concurrently in ONE terminal window.
Press Ctrl+C at any time to cleanly stop all services.
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RADIX = ROOT / "radix-platform"

SERVICES = [
    {
        "name": "Role 1: JD",
        "tag": "\033[94m[Role 1 JD]\033[0m",
        "cwd": RADIX / "services" / "role-1-jd-analytics",
        "cmd": [
            str(RADIX / "services" / "role-1-jd-analytics" / ".venv" / "Scripts" / "python.exe"),
            "-m", "uvicorn", "app.main:app", "--port", "8001", "--host", "127.0.0.1"
        ],
        "port": 8001,
    },
    {
        "name": "Role 2: Resume",
        "tag": "\033[92m[Role 2 Resume]\033[0m",
        "cwd": RADIX / "services" / "role-2-resume-parsing",
        "cmd": [
            str(RADIX / "services" / "role-2-resume-parsing" / ".venv" / "Scripts" / "python.exe"),
            "-m", "uvicorn", "api_server:app", "--port", "8002", "--host", "127.0.0.1"
        ],
        "port": 8002,
    },
    {
        "name": "Role 3: Profile",
        "tag": "\033[93m[Role 3 Profile]\033[0m",
        "cwd": RADIX / "services" / "role-3-profile-builder",
        "cmd": [
            str(RADIX / "services" / "role-3-profile-builder" / ".venv" / "Scripts" / "python.exe"),
            "-m", "uvicorn", "main:app", "--port", "8003", "--host", "127.0.0.1"
        ],
        "port": 8003,
    },
    {
        "name": "Role 4: Talent",
        "tag": "\033[95m[Role 4 Talent]\033[0m",
        "cwd": RADIX / "services" / "role-4-talent-check",
        "cmd": [
            str(RADIX / "services" / "role-4-talent-check" / ".venv" / "Scripts" / "python.exe"),
            "-m", "uvicorn", "talent_check.backend.api:app", "--port", "8004", "--host", "127.0.0.1"
        ],
        "port": 8004,
    },
    {
        "name": "Role 5: Match",
        "tag": "\033[96m[Role 5 Match]\033[0m",
        "cwd": RADIX / "services" / "role-5-skill-matching",
        "cmd": [
            str(RADIX / "services" / "role-5-skill-matching" / ".venv" / "Scripts" / "python.exe"),
            "-m", "uvicorn", "skill_matching.api:app", "--port", "8005", "--host", "127.0.0.1"
        ],
        "port": 8005,
    },
    {
        "name": "Frontend",
        "tag": "\033[97m[Frontend]\033[0m",
        "cwd": RADIX / "frontend",
        "cmd": ["npm.cmd" if os.name == "nt" else "npm", "run", "dev"],
        "port": 8081,
    },
]

processes = []
running = True

def stream_output(pipe, tag):
    try:
        for line in iter(pipe.readline, ''):
            if not running:
                break
            if line.strip():
                print(f"{tag} {line.strip()}", flush=True)
    except Exception:
        pass
    finally:
        pipe.close()

def stop_all(sig=None, frame=None):
    global running
    if not running:
        return
    running = False
    print("\n\033[91m==> Stopping all RADIX platform services...\033[0m", flush=True)
    for p in processes:
        try:
            p.terminate()
        except Exception:
            pass
    time.sleep(1)
    for p in processes:
        try:
            p.kill()
        except Exception:
            pass
    print("\033[92mAll services stopped cleanly.\033[0m", flush=True)
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, stop_all)
    signal.signal(signal.SIGTERM, stop_all)

    print("\033[1;36m" + "=" * 60)
    print("  RADIX Platform — Unified Single-Terminal Server")
    print("=" * 60 + "\033[0m")
    print("Starting all 5 microservices + frontend in this single window...\n")

    for svc in SERVICES:
        if not svc["cwd"].exists():
            print(f"\033[93m[SKIP]\033[0m Directory not found: {svc['cwd']}")
            continue

        try:
            p = subprocess.Popen(
                svc["cmd"],
                cwd=str(svc["cwd"]),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            )
            processes.append(p)
            t = threading.Thread(target=stream_output, args=(p.stdout, svc["tag"]), daemon=True)
            t.start()
            print(f"  \033[92m✔\033[0m Started {svc['name']} (port {svc['port']})")
        except Exception as e:
            print(f"  \033[91m✖\033[0m Failed to start {svc['name']}: {e}")

    print("\n\033[1;32mAll services running!\033[0m")
    print("  Frontend:         http://localhost:8081")
    print("  Role 1 (JD):      http://localhost:8001/health")
    print("  Role 2 (Resume):  http://localhost:8002/health")
    print("  Role 3 (Profile): http://localhost:8003/health")
    print("  Role 4 (Talent):  http://localhost:8004/health")
    print("  Role 5 (Match):   http://localhost:8005/health")
    print("\nPress \033[1mCtrl+C\033[0m in this terminal to stop everything at once.\n")

    while running:
        time.sleep(1)

if __name__ == "__main__":
    main()
