"""FE-06 — install and run in an independent project with stock django.contrib.admin."""
import subprocess
import sys
from pathlib import Path


def test_standalone_project():
    script = Path(__file__).parent / "standalone" / "run_checks.py"
    res = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "STANDALONE OK" in res.stdout
