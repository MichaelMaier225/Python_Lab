"""Use the artifact's original sklearn version without changing the SVM environment."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def python_path():
    default = ROOT / '.venv-rf' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    return Path(os.getenv('PRODUCTMATCH_RF_PYTHON', default))


def run(entry, path, checksum, pairs=None):
    executable = python_path()
    if not executable.is_file():
        raise ValueError('RF runtime is missing. Run python -m scripts.setup_rf_runtime.')
    request = {'entry': entry, 'path': str(path), 'checksum': checksum, 'pairs': pairs}
    result = subprocess.run([str(executable), '-m', 'models.RF.worker'],
                            input=json.dumps(request), text=True, capture_output=True,
                            cwd=ROOT, timeout=120)
    if result.returncode:
        raise ValueError('RF could not load or score. Verify its checksum and scikit-learn 1.9.1 runtime.')
    return json.loads(result.stdout)
