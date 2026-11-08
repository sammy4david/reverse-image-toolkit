#!/bin/sh
set -eu

APP_HOME="$HOME/.local/share/reverse-image-toolkit"
APP_DIR="$APP_HOME/app"
VENV="$APP_HOME/venv"

if [ -n "${PREFIX:-}" ] && [ -d "$PREFIX/bin" ]; then
    LAUNCHER_DIR="$PREFIX/bin"
else
    LAUNCHER_DIR="$HOME/.local/bin"
fi

BACKUP_DIR=""

if [ -f "$APP_HOME/launcher-backup-path" ]; then
    BACKUP_DIR="$(cat "$APP_HOME/launcher-backup-path" 2>/dev/null || true)"
fi

# Accept only backups created by this toolkit's installer.
case "$BACKUP_DIR" in
    "$HOME"/.local/state/reverse-image-toolkit/launcher-backup-*)
        ;;
    *)
        BACKUP_DIR=""
        ;;
esac

echo "======================================"
echo " Reverse Image Toolkit Uninstaller"
echo "======================================"

for name in reverse-image reverse-image-html reverse-image-local reverse-image-server; do
    TARGET="$LAUNCHER_DIR/$name"

    if [ -n "$BACKUP_DIR" ] && [ -f "$BACKUP_DIR/$name" ]; then
        cp -p "$BACKUP_DIR/$name" "$TARGET"
        echo "[+] Restored previous launcher: $name"
    elif [ -f "$TARGET" ] &&
         grep -Fq "$APP_DIR/" "$TARGET" &&
         grep -Fq "$VENV/bin/python" "$TARGET"; then
        rm -f "$TARGET"
        echo "[+] Removed toolkit launcher: $name"
    else
        echo "[=] Left untouched: $name"
    fi
done

if [ -d "$APP_HOME" ]; then
    rm -rf "$APP_HOME"
    echo "[+] Removed toolkit application directory."
fi

echo
echo "[+] Uninstallation completed."
echo "[+] Reports and downloaded images were not touched."
