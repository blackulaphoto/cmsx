from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_URL = "http://127.0.0.1:8100/health"
FRONTEND_URL = "http://127.0.0.1:5174/src/main.jsx"


def wait_for_url(url: str, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    last_error: str | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status < 500:
                    return
        except urllib.error.HTTPError as exc:
            if exc.code < 500:
                return
            last_error = str(exc)
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for {url}. Last error: {last_error}")


def kill_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if sys.platform.startswith("win"):
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            cwd=ROOT_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def kill_port_processes(*ports: int) -> None:
    if not sys.platform.startswith("win"):
        return
    for port in ports:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                (
                    f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue "
                    "| Select-Object -ExpandProperty OwningProcess -Unique"
                ),
            ],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        for raw_pid in result.stdout.splitlines():
            raw_pid = raw_pid.strip()
            if raw_pid.isdigit():
                subprocess.run(
                    ["taskkill", "/PID", raw_pid, "/T", "/F"],
                    cwd=ROOT_DIR,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )


def main() -> int:
    kill_port_processes(8100, 5174)
    backend = subprocess.Popen(
        [sys.executable, "scripts/start_ur_e2e_backend.py"],
        cwd=ROOT_DIR,
    )
    frontend = subprocess.Popen(
        [
            "npm.cmd" if sys.platform.startswith("win") else "npm",
            "--prefix",
            "frontend",
            "run",
            "dev",
            "--",
            "--host",
            "127.0.0.1",
            "--port",
            "5174",
            "--strictPort",
            "--mode",
            "e2e",
        ],
        cwd=ROOT_DIR,
    )

    try:
        wait_for_url(BACKEND_URL)
        wait_for_url(FRONTEND_URL)
        command = [
            "npx.cmd" if sys.platform.startswith("win") else "npx",
            "playwright",
            "test",
            "e2e/ur-ui.spec.js",
            "--config",
            "playwright.config.js",
            "--reporter",
            "line",
        ]
        return subprocess.run(command, cwd=ROOT_DIR, check=False).returncode
    finally:
        kill_process_tree(frontend)
        kill_process_tree(backend)


if __name__ == "__main__":
    raise SystemExit(main())
