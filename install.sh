#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_HOME="$HOME/.local/share/reverse-image-toolkit"
APP_DIR="$APP_HOME/app"
VENV="$APP_HOME/venv"

echo "======================================"
echo " Reverse Image Toolkit 1.1.0 Installer"
echo "======================================"

# Detect Termux or Linux.
if [ -n "${PREFIX:-}" ] && [ -d "$PREFIX/bin" ]; then
    PLATFORM="Termux"
    LAUNCHER_DIR="$PREFIX/bin"
    SHELL_PATH="$PREFIX/bin/sh"
    PYTHON="$(command -v python)"
else
    PLATFORM="Linux"
    LAUNCHER_DIR="$HOME/.local/bin"
    SHELL_PATH="/bin/sh"

    if command -v python3 >/dev/null 2>&1; then
        PYTHON="$(command -v python3)"
    else
        PYTHON="$(command -v python)"
    fi
fi

echo "[+] Platform: $PLATFORM"
echo "[+] Python: $PYTHON"

# Preserve existing launchers before replacing them.
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$HOME/.local/state/reverse-image-toolkit/launcher-backup-$STAMP"
BACKED_UP=0

for name in reverse-image reverse-image-html reverse-image-local reverse-image-server; do
    if [ -e "$LAUNCHER_DIR/$name" ]; then
        mkdir -p "$BACKUP_DIR"
        cp -p "$LAUNCHER_DIR/$name" "$BACKUP_DIR/"
        BACKED_UP=1
    fi
done

if [ "$BACKED_UP" -eq 1 ]; then
    echo "[+] Previous launchers backed up to: $BACKUP_DIR"
fi

# Create isolated application directories.
mkdir -p "$APP_DIR"
mkdir -p "$LAUNCHER_DIR"

# Record the previous launcher backup for safe uninstallation.
if [ "$BACKED_UP" -eq 1 ]; then
    printf '%s\n' "$BACKUP_DIR" > "$APP_HOME/launcher-backup-path"
else
    : > "$APP_HOME/launcher-backup-path"
fi

# Copy application files and package metadata.
cp "$ROOT"/reverse_image*.py "$APP_DIR/"
cp "$ROOT/pyproject.toml" "$APP_DIR/"
cp "$ROOT/requirements.txt" "$APP_DIR/"
cp "$ROOT/README.md" "$APP_DIR/"

# Create the isolated Python environment if necessary.
if [ ! -x "$VENV/bin/python" ]; then
    "$PYTHON" -m venv "$VENV"
fi

echo "[+] Installing toolkit and Python dependencies..."
"$VENV/bin/python" -m pip install "$APP_DIR"

# Create command launchers.
make_launcher() {
    NAME="$1"
    SCRIPT="$2"

    cat > "$LAUNCHER_DIR/$NAME" <<LAUNCHER
#!$SHELL_PATH
exec "$VENV/bin/python" "$APP_DIR/$SCRIPT" "\$@"
LAUNCHER

    chmod 755 "$LAUNCHER_DIR/$NAME"
    echo "[+] Installed command: $NAME"
}

make_launcher reverse-image reverse_image.py
make_launcher reverse-image-html reverse_image_html.py
make_launcher reverse-image-local reverse_image_local.py
make_launcher reverse-image-server reverse_image_server.py

echo
echo "[+] Installation completed."
echo "[+] Application directory: $APP_DIR"
echo "[+] Python environment: $VENV"
echo "[+] Launcher directory: $LAUNCHER_DIR"

if ! command -v php >/dev/null 2>&1; then
    echo "[!] PHP is not installed. Local web-server functionality requires PHP."
fi

echo "[+] Restart your terminal or refresh its command cache if necessary."
