"""Create the initial save state from an existing FireRed .sav or fresh boot.

Best results: use a .sav from just after obtaining the starter Pokémon.
"""
import argparse
from pathlib import Path
from emulator import Emulator

p = argparse.ArgumentParser()
p.add_argument('--core', required=True)
p.add_argument('--rom', required=True)
p.add_argument('--output', default='start.state')
p.add_argument('--boot-frames', type=int, default=240)
a = p.parse_args()
e = Emulator(a.core, a.rom)
try:
    e.step(frames=a.boot_frames)
    Path(a.output).write_bytes(e.save_state())
    print(f'Created {a.output}. For meaningful training, use an in-game starting state.')
finally:
    e.close()
