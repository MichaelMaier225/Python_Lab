"""FireRed RAM inspector. Replaces the existing test_core.py; no game files changed.

Run with --core, --rom and --state. F6 records a baseline RAM snapshot.
Move to another tile, press F7 to compare RAM. F8 resets to the saved game.
Escape closes the viewer. Only compare while standing still (not in a menu).
"""
import argparse
import pygame
from emulator import Emulator

KEYS = {
    pygame.K_UP: "up", pygame.K_DOWN: "down",
    pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
    pygame.K_z: "a", pygame.K_x: "b",
    pygame.K_RETURN: "start", pygame.K_BACKSPACE: "select",
}

def changed_words(before, after):
    """Show little-endian 16-bit values that changed between samples."""
    rows = []
    for offset in range(0, min(len(before), len(after)) - 1, 2):
        old = int.from_bytes(before[offset:offset+2], "little")
        new = int.from_bytes(after[offset:offset+2], "little")
        if old != new:
            rows.append((offset, old, new, new-old))
    return rows

def main():
    parser = argparse.ArgumentParser(description="Inspect FireRed RAM while moving")
    parser.add_argument("--core", required=True)
    parser.add_argument("--rom", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--scale", type=int, default=3)
    args = parser.parse_args()
    with open(args.state, "rb") as f:
        initial_state = f.read()

    emu = Emulator(args.core, args.rom)
    pygame.init()
    screen = pygame.display.set_mode((240*args.scale, 160*args.scale))
    pygame.display.set_caption("FireRed RAM inspector | F6 sample | F7 compare | F8 reset")
    clock = pygame.time.Clock()
    baseline = None
    held = set()
    region = None
    print("F6: sample RAM at your current tile")
    print("Walk to another tile, STOP, then F7: show changed 16-bit values")
    print("Repeat with other movements to identify coordinate offsets.")
    print("F8: reset to initial state. Esc: quit.")
    try:
        emu.load_state(initial_state)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_F6:
                        ewram = emu.ewram()
                        region = "EWRAM" if ewram is not None else "system RAM (fallback)"
                        baseline = bytes(ewram if ewram is not None else emu.ram())
                        print(f"Baseline saved ({len(baseline)} bytes; {region}).")
                        if ewram is None:
                            print("Core did not expose EWRAM via Libretro memory maps.")
                            print("These values may not include the player's coordinates.")
                    elif event.key == pygame.K_F7:
                        if baseline is None:
                            print("Press F6 first.")
                        else:
                            current = bytes(emu.ewram() if region == "EWRAM" else emu.ram())
                            rows = changed_words(baseline, current)
                            print(f"Changed 16-bit words: {len(rows)}")
                            for offset, old, new, delta in rows[:100]:
                                print(f"  {region} + 0x{offset:05X}: {old:5d} -> {new:5d}  delta {delta:+d}")
                            if len(rows) > 100:
                                print(f"  ... {len(rows)-100} more changes (showing first 100)")
                            print("Compare several short movements; do not assume any offset is a coordinate yet.")
                    elif event.key == pygame.K_F8:
                        emu.load_state(initial_state)
                        baseline = None
                        region = None
                        held.clear()
                        print("Reset to saved state.")
                    elif event.key in KEYS:
                        held.add(event.key)
                elif event.type == pygame.KEYUP and event.key in KEYS:
                    held.discard(event.key)
            button = next((KEYS[k] for k in KEYS if k in held), None)
            emu.step(button, frames=1)
            frame = pygame.surfarray.make_surface(emu.frame.swapaxes(0, 1))
            if args.scale != 1:
                frame = pygame.transform.scale(frame, screen.get_size())
            screen.blit(frame, (0, 0))
            pygame.display.flip()
            clock.tick(60)
    finally:
        emu.close()
        pygame.quit()

if __name__ == "__main__":
    main()
