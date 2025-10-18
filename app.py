import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONT = ROOT / "front-end"
BACK = ROOT / "back-end"

IS_WIN = os.name == "nt"
NPM = "npm.cmd" if IS_WIN else "npm"


def run(cmd, cwd=None, check=True):
    if cmd and cmd[0] == "npm" and IS_WIN:
        cmd[0] = NPM
    pretty = " ".join(cmd)
    here = str(cwd or ROOT)
    print(f"$ {pretty}  (cwd={here})")
    return subprocess.run(cmd, cwd=cwd or ROOT, check=check)


def ensure_node_deps():
    # Only install deps inside front-end
    if not (FRONT / "node_modules").exists():
        run([NPM, "install"], cwd=FRONT)


def main():
    if not (BACK / "run.py").exists():
        print("Error: back-end/run.py not found.", file=sys.stderr)
        sys.exit(1)
    if not (FRONT / "package.json").exists():
        print("Error: front-end/package.json not found.", file=sys.stderr)
        sys.exit(1)

    # Verify npm available
    if shutil.which(NPM) is None:
        hint = (
            "npm not found. Install Node in your conda env:\n"
            "  conda install -c conda-forge nodejs=20\n"
            "or install Node LTS system-wide and reopen your shell."
        )
        print(hint, file=sys.stderr)
        sys.exit(1)

    # Install deps if missing
    ensure_node_deps()

    # Start backend + frontend
    print("\nStarting servers… (Ctrl+C to stop)")
    back = subprocess.Popen([sys.executable, "run.py"], cwd=BACK)
    front = subprocess.Popen([NPM, "start"], cwd=FRONT)

    try:
        while True:
            rb = back.poll()
            rf = front.poll()
            if rb is not None or rf is not None:
                code = rb if rb is not None else rf
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
