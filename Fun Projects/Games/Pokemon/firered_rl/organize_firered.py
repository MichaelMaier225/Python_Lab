"""
Safely organize the FireRed RL project folder.

Default behavior is a dry run: it prints what would move but changes nothing.
To actually move files, run:
    py organize_firered.py --apply

Folders created:
    models/       PPO checkpoints and saved models (*.zip, excluding replay archives)
    recordings/   replay archives (*_replay.zip)
    states/       emulator save states (*.state)
    diagnostics/  screenshots and diagnostic images (*.png)

Python scripts, ROMs, DLLs, requirements, README, and logs are left in place.
Existing destination files are never overwritten; a numbered name is used instead.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def destination_for(path: Path) -> Path | None:
    name = path.name.lower()

    if path.is_dir():
        return None

    if name.endswith("_replay.zip"):
        return ROOT / "recordings" / path.name

    if path.suffix.lower() == ".zip":
        return ROOT / "models" / path.name

    if path.suffix.lower() == ".state":
        return ROOT / "states" / path.name

    if path.suffix.lower() == ".png":
        return ROOT / "diagnostics" / path.name

    return None

def non_overwriting_path(destination: Path) -> Path:
    if not destination.exists():
        return destination

    stem, suffix = destination.stem, destination.suffix
    index = 2
    while True:
        candidate = destination.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1

def main() -> int:
    parser = argparse.ArgumentParser(description="Organize FireRed RL files safely.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually move files. Without this flag, only preview the changes.",
    )
    args = parser.parse_args()

    moves: list[tuple[Path, Path]] = []
    for item in sorted(ROOT.iterdir(), key=lambda p: p.name.lower()):
        destination = destination_for(item)
        if destination is None:
            continue
        destination.parent.mkdir(parents=True, exist_ok=True) if args.apply else None
        moves.append((item, non_overwriting_path(destination)))

    if not moves:
        print("No files in the project root need organizing.")
        return 0

    print("DRY RUN — no files will be moved." if not args.apply else "APPLY MODE — moving files.")
    for source, destination in moves:
        print(f"{source.name}  ->  {destination.relative_to(ROOT)}")

    if not args.apply:
        print("\nIf this plan looks right, run:")
        print('  "C:\\Users\\Micha\\.venv\\Scripts\\python.exe" ".\\organize_firered.py" --apply')
        return 0

    for source, destination in moves:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination = non_overwriting_path(destination)
        shutil.move(str(source), str(destination))

    print(f"\nMoved {len(moves)} file(s). Nothing was deleted or overwritten.")
    print("Note: future --resume paths should use .\\models\\<checkpoint>.zip")
    print("      future --recording paths should use .\\recordings\\<name>_replay.zip")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
