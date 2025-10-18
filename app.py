import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONT = ROOT / "front-end"
BACK = ROOT / "back-end"

def run(cmd, cwd=None, check=True):
    print(f"$ {' '.join(cmd)}  (cwd={cwd or ROOT})")
    return subprocess.run(cmd, cwd=cwd or ROOT, check=check)

def ensure_node_deps():
    if not (ROOT / "node_modules").exists() or not (ROOT / "node_modules/.bin/concurrently").exists():
        run(["npm", "install"], cwd=ROOT)

    if not (FRONT / "node_modules").exists():
        run(["npm", "install"], cwd=FRONT)

def main():
    if not (BACK / "run.py").exists():
        print("Error: back-end/run.py not found.", file=sys.stderr)
        sys.exit(1)
    if not (FRONT / "package.json").exists():
        print("Error: front-end/package.json not found.", file=sys.stderr)
        sys.exit(1)

    if shutil.which("npm") is None:
        print("Error: npm not found. Ensure environment.yml includes nodejs and you activated the env.", file=sys.stderr)
        sys.exit(1)

    ensure_node_deps()

    # start backend and frontend
    print("\nStarting servers… (Ctrl+C to stop)")
    back = subprocess.Popen([sys.executable, "run.py"], cwd=BACK)
    front = subprocess.Popen(["npm", "start"], cwd=FRONT)

    try:
        while True:
            ret_b = back.poll()
            ret_f = front.poll()
            if ret_b is not None or ret_f is not None:
                code = ret_b if ret_b is not None else ret_f
                sys.exit(code or 0)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nShutting down…")
    finally:
        for p in (front, back):
            if p and p.poll() is None:
                p.terminate()
        time.sleep(1)
        for p in (front, back):
            if p and p.poll() is None:
                p.kill()

if __name__ == "__main__":
    main()