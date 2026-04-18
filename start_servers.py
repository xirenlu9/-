import subprocess, sys, time, os

base = r"C:\Users\20473\WorkBuddy\20260417102921"

# Start FastAPI (port 8000)
fastapi_proc = subprocess.Popen(
    [sys.executable, os.path.join(base, "backend", "main.py")],
    cwd=os.path.join(base, "backend"),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
)

# Start HTTP server (port 8765)
http_proc = subprocess.Popen(
    [sys.executable, "-m", "http.server", "8765"],
    cwd=base,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
)

print(f"FastAPI PID: {fastapi_proc.pid}")
print(f"HTTP PID: {http_proc.pid}")
print("Both services started.")
