import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote


REPORT_DIR = Path.home() / "reports" / "reverse-image"
DOWNLOAD_DIR = Path.home() / "storage" / "shared" / "Download"


def paint(text, colour):
    return f"\033[{colour}m{text}\033[0m"


def report_artifacts(report):
    report = Path(report).expanduser().resolve()
    if report.parent != REPORT_DIR.resolve():
        return []
    html_file = report.with_name(report.stem + "_local.html")
    image_folder = report.with_name(report.stem + "_local_images")

    return [
        report,
        html_file,
        image_folder,
        DOWNLOAD_DIR / html_file.name,
        DOWNLOAD_DIR / image_folder.name,
    ]


def measure_targets(targets):
    files = 0
    folders = 0
    total_size = 0

    for path in targets:
        if path.is_symlink():
            files += 1
            total_size += path.lstat().st_size
        elif path.is_file():
            files += 1
            total_size += path.stat().st_size
        elif path.is_dir():
            folders += 1
            for item in path.rglob("*"):
                if item.is_symlink() or item.is_file():
                    try:
                        files += 1
                        total_size += item.lstat().st_size
                    except OSError:
                        pass

    return files, folders, total_size


def format_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.2f} {unit}"
        size /= 1024


def confirm_delete(targets, description):
    existing = list(dict.fromkeys(
        Path(p) for p in targets if Path(p).exists() or Path(p).is_symlink()
    ))

    if not existing:
        print("\n[-] No matching files or folders found.")
        return False

    files, folders, size = measure_targets(existing)

    print(f"\n===== {description} =====")
    print(f"[!] Files to delete: {files}")
    print(f"[!] Folders to delete: {folders}")
    print(f"[!] Estimated storage to free: {format_size(size)}")

    for path in existing:
        print(f"    {path}")

    answer = input("\nType DELETE to confirm: ").strip()

    if answer != "DELETE":
        print("[-] Deletion cancelled. Nothing was deleted.")
        return False

    deleted = 0

    for path in existing:
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            deleted += 1
        except OSError as error:
            print(f"[!] Could not delete {path}: {error}")

    print(f"[+] Deleted {deleted} of {len(existing)} listed items.")

    if deleted == len(existing):
        return True

    print("[!] Some items could not be deleted. The operation was incomplete.")
    return False


def create_local_report(report):
    script = Path(__file__).with_name("reverse_image_local.py")

    if not script.is_file():
        print(f"[!] HTML generator not found: {script}")
        return False

    result = subprocess.run(
        [sys.executable, str(script), str(report)],
        check=False
    )

    return result.returncode == 0


def open_report(report):
    report = Path(report)

    if not report.is_file():
        print("[-] The current JSON report no longer exists.")
        return

    html_name = report.stem + "_local.html"
    published_html = DOWNLOAD_DIR / html_name

    if not published_html.is_file():
        print("[!] Published HTML report is missing.")
        print("[+] Attempting to regenerate and publish it...")
        if not create_local_report(report):
            return

    server_script = Path(__file__).with_name("reverse_image_server.py")

    result = subprocess.run(
        [sys.executable, str(server_script), "start"],
        check=False
    )

    if result.returncode != 0:
        print("[!] Could not start the local server.")
        return

    url = f"http://127.0.0.1:8765/{quote(html_name)}"
    print(f"[+] Report address: {url}")

    if shutil.which("am"):
        subprocess.run(
            ["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
            check=False
        )
    else:
        print("[!] Android browser launcher unavailable. Open the URL manually.")


def all_report_artifacts(current_report=None):
    targets = []

    if not REPORT_DIR.is_dir():
        return targets

    # Only JSON reports in the toolkit's own report directory
    # are allowed to determine which published files are deleted.
    for report in REPORT_DIR.glob("report_*.json"):
        targets.extend(report_artifacts(report))

    if current_report:
        targets.extend(report_artifacts(current_report))

    return list(dict.fromkeys(targets))


def interactive_menu(current_report, image_path, selected, limit, timeout):
    while True:
        width = 48

        print("\n" + paint("=" * width, "96"))
        print(paint("SEARCH COMPLETED".center(width), "1;93"))
        print(paint("* REVERSE IMAGE TOOLKIT - MENU *".center(width), "1;96"))
        print(paint("=" * width, "96"))

        print(paint("1. Perform another image search", "92"))
        print(paint("2. Open the generated report again", "96"))
        print(paint("3. Delete current report and all its files", "91"))
        print(paint("4. Delete all previous reports and downloaded images", "93"))
        print(paint("5. Exit", "95"))

        print(paint("=" * width, "96"))

        choice = input(
            paint("Select an option [1-5]: ", "1;96")
        ).strip()

        if choice == "1":
            new_image = input("Enter image path (or press Enter to cancel): ").strip()

            if not new_image:
                continue

            new_image = Path(new_image).expanduser()

            if not new_image.is_file():
                print(f"[!] Image not found: {new_image}")
                continue

            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            new_report = REPORT_DIR / (
                "report_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".json"
            )

            search_script = Path(__file__).with_name("reverse_image.py")
            command = [
                sys.executable, str(search_script), str(new_image),
                "--engine", ",".join(selected),
                "--limit", str(limit),
                "--timeout", str(timeout),
                "--output", str(new_report),
                "--menu-child",
            ]

            result = subprocess.run(command, check=False)

            if (result.returncode == 0 and new_report.is_file()
                    and create_local_report(new_report)):
                current_report = new_report
                image_path = new_image
                print("[+] New search and report completed.")
            else:
                print("[!] The new search did not complete successfully.")

        elif choice == "2":
            if current_report:
                open_report(current_report)
            else:
                print("[-] There is no current report to open.")

        elif choice == "3":
            if current_report:
                if confirm_delete(
                    report_artifacts(current_report),
                    "DELETE CURRENT SEARCH REPORT"
                ):
                    current_report = None
            else:
                print("[-] There is no current report to delete.")

        elif choice == "4":
            if confirm_delete(
                all_report_artifacts(current_report),
                "DELETE ALL TOOLKIT REPORTS AND DOWNLOADED IMAGES"
            ):
                current_report = None

        elif choice == "5":
            print("[+] Exiting Reverse Image Toolkit.")
            return

        else:
            print("[!] Invalid selection. Choose 1, 2, 3, 4, or 5.")
