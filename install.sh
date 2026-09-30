#!/bin/sh
# Install Scriptorium: a Python environment for its tools, and the `scriptorium` command (alias `scrip`).
set -e
cd "$(dirname "$0")"
HERE="$(pwd)"

echo "Setting up Python tools…"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r kit/requirements.txt
.venv/bin/playwright install chromium >/dev/null 2>&1 || echo "  (couldn't install the PDF browser — PDFs won't work until: .venv/bin/playwright install chromium)"

BIN="$HOME/.local/bin"
mkdir -p "$BIN"
chmod +x scriptorium
ln -sf "$HERE/scriptorium" "$BIN/scriptorium"
ln -sf "$HERE/scriptorium" "$BIN/scrip"
echo "Installed the command: $BIN/scriptorium (and scrip)"
case ":$PATH:" in
  *":$BIN:"*) ;;
  *) echo "  Add it to your PATH:  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && exec zsh" ;;
esac
echo
"$HERE/scriptorium" doctor
