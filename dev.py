#!/usr/bin/env python3
from __future__ import annotations
"""
D0mmy Dev Bootstrapper
Starts the process launcher and the dashboard in parallel.
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    print("\x1b[34m" + "="*50)
    print(" D0MMY DEV BOOTSTRAPPER")
    print("="*50 + "\x1b[0m")

    # 1. Start the launcher
    print("\x1b[32m[1/2] Starting process launcher...\x1b[0m")
    launcher_proc = subprocess.Popen(
        [sys.executable, "scripts/launcher.py"],
        cwd=str(ROOT),
        preexec_fn=None if sys.platform == "win32" else os.setsid
    )

    # Give it a second to bind to port 8001
    time.sleep(2)

    # 2. Start the backend via launcher
    print("\x1b[32m[2/3] Booting backend...\x1b[0m")
    import urllib.request
    try:
        # Retry a few times to give launcher time to start
        for i in range(5):
            try:
                with urllib.request.urlopen("http://127.0.0.1:8001/start") as r:
                    if r.status == 200:
                        print("\x1b[32m[✓] Backend started.\x1b[0m")
                        break
            except Exception:
                time.sleep(1)
    except Exception as e:
        print(f"\x1b[31m[!] Failed to auto-start backend: {e}\x1b[0m")

    # 3. Start the dashboard
    print("\x1b[32m[3/3] Starting dashboard (Vite)...\x1b[0m")
    dashboard_dir = ROOT / "dashboard"
    
    # Check if node_modules exists
    if not (dashboard_dir / "node_modules").exists():
        print("\x1b[33m[!] node_modules missing. Running npm install...\x1b[0m")
        subprocess.run(["npm", "install"], cwd=str(dashboard_dir))

    dashboard_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(dashboard_dir),
        preexec_fn=None if sys.platform == "win32" else os.setsid
    )

    print("\x1b[36m" + "-"*50)
    print(" SYSTEM READY")
    print(" Backend:    http://localhost:8000")
    print(" Launcher:   http://localhost:8001")
    print(" Dashboard:  http://localhost:5173")
    print("-"*50 + "\x1b[0m")
    print("Press Ctrl+C to stop both processes.\n")

    try:
        # Keep alive and monitor
        while True:
            if launcher_proc.poll() is not None:
                print("\x1b[31m[!] Launcher died. Exiting.\x1b[0m")
                break
            if dashboard_proc.poll() is not None:
                print("\x1b[31m[!] Dashboard died. Exiting.\x1b[0m")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\x1b[33mShutting down processes...\x1b[0m")
    finally:
        print("\x1b[33mCleaning up processes...\x1b[0m")
        for proc, name in [(launcher_proc, "Launcher"), (dashboard_proc, "Dashboard")]:
            if proc.poll() is None:
                try:
                    if sys.platform != "win32":
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    else:
                        proc.terminate()
                except Exception:
                    proc.kill()
        print("\x1b[32mClean exit accomplished.\x1b[0m")

if __name__ == "__main__":
    main()
