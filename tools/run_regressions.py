"""Run fast source checks and real Qt whiteboard smoke tests in separate processes."""
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run(label, arguments, env, timeout):
    print(f'\n=== {label} ===', flush=True)
    start = time.monotonic()
    try:
        result = subprocess.run([sys.executable, *arguments], cwd=ROOT, env=env,
                                timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        print(f'FAIL: {label} exceeded {timeout} seconds', flush=True)
        return False
    print(f'{"PASS" if result.returncode == 0 else "FAIL"}: {label} '
          f'({time.monotonic() - start:.1f}s)', flush=True)
    return result.returncode == 0


def main():
    env = os.environ.copy()
    env.setdefault('MONTASPACE_STUDIO_DECODER', 'software')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    # Offscreen supports deterministic QGraphicsScene tests without opening dialogs.
    # Only test code uses this flag; real Studio still uses the normal Windows UI.
    env.setdefault('QT_QPA_PLATFORM', 'offscreen')
    # Never report success if the actual PySide6 GUI suite cannot run.
    if not run('PySide6 prerequisite', ['-c', 'import PySide6; from PySide6.QtMultimedia import QMediaPlayer'], env, 20):
        print('FAIL — PySide6 unavailable. Use the project Windows .venv.', flush=True)
        return 2
    tests = [
        ('Fast source/logic regression', ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], 90),
        ('Real Qt whiteboard regression', ['-m', 'unittest', 'tests.test_gui_regression', '-v'], 120),
    ]
    passed = [run(label, arguments, env, timeout) for label, arguments, timeout in tests]
    print('\n=== OVERALL ===', flush=True)
    if all(passed):
        print('PASS — source tests and Qt whiteboard smoke tests completed.', flush=True)
        return 0
    print('FAIL — at least one suite failed. Do not commit this update.', flush=True)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
