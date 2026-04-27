#!/usr/bin/env python3
"""
Start all Assessly platform services in a single terminal with color-coded output.
Usage: python start-all.py
"""

import subprocess
import sys
import os
import threading
import time
import signal
import platform

# Color codes for terminal output
COLORS = {
    "AUTH": "\033[94m",      # Blue
    "GATEWAY": "\033[92m",   # Green
    "CANDIDATE": "\033[93m", # Yellow
    "ASSESSMENT": "\033[95m",# Magenta
    "EMPLOYER": "\033[96m",  # Cyan
    "WORKER": "\033[90m",    # Gray
    "RESET": "\033[0m",
}

# Use conda env Python (has all dependencies like email-validator)
PYTHON_EXE = r"C:\Users\vijay\anaconda3\envs\zetheta\python.exe"


def kill_orphans():
    """Kill any processes already listening on our target ports."""
    ports = [3000, 3001, 4000, 4001, 4002]
    if platform.system() == "Windows":
        for port in ports:
            try:
                subprocess.run(
                    ["powershell", "-Command",
                     f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"],
                    capture_output=True, text=True, timeout=10
                )
            except Exception:
                pass
    else:
        for port in ports:
            try:
                result = subprocess.run(
                    ["lsof", "-ti", f":{port}"],
                    capture_output=True, text=True, timeout=5
                )
                if result.stdout.strip():
                    pids = result.stdout.strip().split("\n")
                    for pid in pids:
                        subprocess.run(["kill", "-9", pid], capture_output=True, timeout=5)
            except Exception:
                pass


SERVICES = [
    {
        "name": "AUTH",
        "cmd": [PYTHON_EXE, "run_auth.py"],
        "cwd": os.path.dirname(os.path.abspath(__file__)),
        "port": 3001,
    },
    {
        "name": "GATEWAY",
        "cmd": [PYTHON_EXE, "run_gateway.py"],
        "cwd": os.path.dirname(os.path.abspath(__file__)),
        "port": 3000,
    },
    {
        "name": "CANDIDATE",
        "cmd": ["npm", "run", "dev"],
        "cwd": os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps", "candidate-portal"),
        "port": 4000,
    },
    {
        "name": "ASSESSMENT",
        "cmd": ["npm", "run", "dev"],
        "cwd": os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps", "assessment-engine"),
        "port": 4001,
    },
    {
        "name": "EMPLOYER",
        "cmd": ["npm", "run", "dev"],
        "cwd": os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps", "employer-dashboard"),
        "port": 4002,
    },
    {
        "name": "WORKER",
        "cmd": [PYTHON_EXE, "run_worker.py"],
        "cwd": os.path.dirname(os.path.abspath(__file__)),
        "port": None,
    },
]

processes = []


def prefix_stream(stream, prefix, color, name):
    """Read lines from a stream and print with a colored prefix."""
    for line in iter(stream.readline, b""):
        try:
            text = line.decode("utf-8", errors="replace").rstrip()
            if text:
                print(f"{color}[{name}]{COLORS['RESET']} {text}", flush=True)
        except Exception:
            pass
    stream.close()


def start_service(service):
    """Start a single service process."""
    name = service["name"]
    color = COLORS.get(name, "")
    if service["port"]:
        print(f"{color}[{name}]{COLORS['RESET']} Starting on port {service['port']}...", flush=True)
    else:
        print(f"{color}[{name}]{COLORS['RESET']} Starting...", flush=True)

    env = os.environ.copy()
    # Ensure PYTHONPATH is set for Python services
    if name in ("AUTH", "GATEWAY", "WORKER"):
        env["PYTHONPATH"] = "services"

    kwargs = {
        "cwd": service["cwd"],
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
    }

    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        # npm is a .cmd file on Windows -- needs shell=True
        if service["cmd"][0] == "npm":
            kwargs["shell"] = True

    proc = subprocess.Popen(service["cmd"], **kwargs)
    processes.append(proc)

    # Start threads to read stdout and stderr
    threading.Thread(
        target=prefix_stream,
        args=(proc.stdout, "OUT", color, name),
        daemon=True,
    ).start()
    threading.Thread(
        target=prefix_stream,
        args=(proc.stderr, "ERR", color, name),
        daemon=True,
    ).start()

    return proc


def shutdown(signum=None, frame=None):
    """Gracefully terminate all child processes."""
    print("\n\033[91m[MANAGER]\033[0m Shutting down all services...", flush=True)
    for proc in processes:
        if proc.poll() is None:
            if sys.platform == "win32":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                proc.terminate()
    # Give processes a moment to exit
    time.sleep(1)
    for proc in processes:
        if proc.poll() is None:
            proc.kill()
    sys.exit(0)


if __name__ == "__main__":
    if sys.platform == "win32":
        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)
    else:
        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

    print("[MANAGER] Cleaning up orphaned processes...")
    kill_orphans()
    time.sleep(1)

    print("=" * 60)
    print("  Assessly Platform - Starting all services")
    print("=" * 60)
    for svc in SERVICES:
        if svc["port"]:
            print(f"  * {svc['name']:12} -> http://localhost:{svc['port']}")
        else:
            print(f"  * {svc['name']:12} -> (background worker)")
    print("=" * 60)
    print("Press Ctrl+C to stop all services\n")

    for svc in SERVICES:
        start_service(svc)
        time.sleep(1.5)  # Stagger starts to reduce race conditions

    # Keep the main thread alive
    exited = set()
    try:
        while True:
            time.sleep(1)
            # Check if any process died unexpectedly
            for proc in processes:
                if proc.poll() is not None and proc.poll() != 0 and id(proc) not in exited:
                    exited.add(id(proc))
                    print(
                        "\033[91m[MANAGER]\033[0m Service exited with code {}. Press Ctrl+C to stop.".format(proc.poll()),
                        flush=True,
                    )
    except KeyboardInterrupt:
        shutdown()
