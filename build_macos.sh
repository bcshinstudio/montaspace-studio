#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: macOS build must run on a Mac." >&2
  exit 1
fi
if [[ ! -x .venv/bin/python ]]; then
  echo "ERROR: Create a Mac venv first: python3 -m venv .venv" >&2
  exit 1
fi
.venv/bin/python -c "import PySide6, PIL, pillow_heif"
.venv/bin/python -m pip install 'pyinstaller>=6,<7'
.venv/bin/python -m unittest discover -s tests -p 'test_macos_portability.py' -v
.venv/bin/python -m PyInstaller \
  --noconfirm --clean --onedir --windowed \
  --name 'MontaSpaceStudio' \
  --icon 'assets/MontaSpaceStudio.icns' \
  --add-data 'assets/MontaSpaceStudio.png:assets' \
  --collect-all pillow_heif \
  main.py
if [[ ! -d 'dist/MontaSpaceStudio.app' ]]; then
  echo 'ERROR: expected .app bundle not found' >&2
  exit 1
fi
echo 'macOS development app created: dist/MontaSpaceStudio.app'
echo 'NOT signed or notarized; test locally before distribution.'
