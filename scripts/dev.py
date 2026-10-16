"""Run both loopback development servers and stop only our own processes."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def stop(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def main() -> None:
    processes: list[subprocess.Popen[bytes]] = []
    try:
        for command in (
            [sys.executable, "apps/api/manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            ["npm", "run", "dev"],
        ):
            processes.append(subprocess.Popen(command, cwd=ROOT, start_new_session=True))
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        raise SystemExit("A development server exited. Check its output above.")
    except KeyboardInterrupt:
        pass
    finally:
        stop(processes)


if __name__ == "__main__":
    main()
