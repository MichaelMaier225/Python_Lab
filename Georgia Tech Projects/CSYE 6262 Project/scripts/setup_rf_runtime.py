"""Install the RF artifact's runtime beside the existing SVM environment."""
from pathlib import Path
import subprocess
import venv

from models.RF.runtime import ROOT, python_path


def main():
    executable = python_path()
    if not executable.is_file():
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(ROOT / '.venv-rf')
    subprocess.run([str(executable), '-m', 'pip', 'install', '-r',
                    str(Path(__file__).resolve().parents[1] / 'requirements-rf.txt')], check=True)
    print('RF runtime ready.')


if __name__ == '__main__':
    main()
