#!/data/data/com.termux/files/usr/bin/python
import os
import sys
import time
import signal
import shutil
import subprocess
from pathlib import Path

PORT = 8765
HOST = "127.0.0.1"
ROOT = Path.home() / "storage/shared/Download"
LOG = Path.home() / "reports/reverse-image/php-server.log"
PIDFILE = Path.home() / ".reverse-image-server.pid"


def find_servers():
    found = []

    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue

        try:
            pid = int(entry)
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
            args = raw.decode(errors="replace").split("\0")

            if (
                len(args) >= 7
                and Path(args[0]).name == "php"
                and "-S" in args
                and f"{HOST}:{PORT}" in args
                and "-t" in args
                and str(ROOT) in args
            ):
                found.append(pid)

        except (OSError, ValueError):
            continue

    return found


def start():
    servers = find_servers()

    if servers:
        print(f"[+] Server is already running (PID {servers[0]})")
        print(f"[+] http://{HOST}:{PORT}/")
        return

    php = shutil.which("php")

    if not php:
        print("[!] PHP is not installed. Run: pkg install php")
        return

    ROOT.mkdir(parents=True, exist_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)

    command = [
        php,
        "-d", "opcache.enable=0",
        "-d", "opcache.enable_cli=0",
        "-S", f"{HOST}:{PORT}",
        "-t", str(ROOT)
    ]

    with open(LOG, "ab") as logfile:
        process = subprocess.Popen(
            command,
            stdout=logfile,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )

    time.sleep(0.5)

    if process.poll() is None and process.pid in find_servers():
        PIDFILE.write_text(str(process.pid))
        print(f"[+] Server started successfully (PID {process.pid})")
        print(f"[+] http://{HOST}:{PORT}/")
    else:
        print("[!] Server failed to start.")
        print(f"[!] Check log: {LOG}")


def status():
    servers = find_servers()

    if servers:
        print("[+] Reverse-image server is RUNNING")
        print(f"[+] PID: {servers[0]}")
        print(f"[+] Address: http://{HOST}:{PORT}/")
    else:
        print("[-] Reverse-image server is STOPPED")


def stop():
    servers = find_servers()

    if not servers:
        PIDFILE.unlink(missing_ok=True)
        print("[-] Server is not running.")
        return

    for pid in servers:
        try:
            os.kill(pid, signal.SIGTERM)

            for _ in range(30):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.2)
                except ProcessLookupError:
                    break
            else:
                os.kill(pid, signal.SIGKILL)

        except ProcessLookupError:
            pass

    PIDFILE.unlink(missing_ok=True)
    print("[+] Reverse-image server stopped.")


def main():
    commands = {
        "start": start,
        "stop": stop,
        "restart": lambda: (stop(), start()),
        "status": status
    }

    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print("Usage: reverse-image-server {start|stop|restart|status}")
        sys.exit(1)

    commands[sys.argv[1]]()


if __name__ == "__main__":
    main()
