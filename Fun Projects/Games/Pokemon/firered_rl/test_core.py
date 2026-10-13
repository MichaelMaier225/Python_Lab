"""Smoke test: load FireRed, run frames, inspect screenshot and save state."""
import argparse
from pathlib import Path
from PIL import Image
from emulator import Emulator
p = argparse.ArgumentParser()
p.add_argument('--core', required=True)
p.add_argument('--rom', required=True)
a = p.parse_args()
e = Emulator(a.core, a.rom)
try:
    e.step(frames=120)
    print('Frame shape:', e.frame.shape)
    print('System RAM bytes:', len(e.ram()))
    Image.fromarray(e.frame).save('smoke_test.png')
    state = e.save_state()
    e.step('a', frames=24)
    e.load_state(state)
    print('Core, frame stepping, RAM access, and save-state roundtrip succeeded.')
finally:
    e.close()
