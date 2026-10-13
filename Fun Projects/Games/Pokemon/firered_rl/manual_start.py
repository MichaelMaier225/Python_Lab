"""Play FireRed manually through the existing mGBA Libretro bridge and save an AI start state."""
import argparse
from pathlib import Path
import pygame
import numpy as np
from emulator import Emulator

KEYS = {
    pygame.K_UP: 'up', pygame.K_DOWN: 'down',
    pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right',
    pygame.K_z: 'a', pygame.K_x: 'b',
    pygame.K_RETURN: 'start', pygame.K_BACKSPACE: 'select',
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--core', required=True)
    parser.add_argument('--rom', required=True)
    parser.add_argument('--state', default='firered_start.state', help='Optional state to load at launch')
    parser.add_argument('--output', default='firered_ingame.state')
    args = parser.parse_args()

    pygame.init()
    screen = pygame.display.set_mode((720, 480))
    pygame.display.set_caption('FireRed Manual Control | F5 Save | ESC Quit')
    clock = pygame.time.Clock()
    emu = Emulator(args.core, args.rom)
    try:
        if args.state and Path(args.state).is_file():
            emu.load_state(Path(args.state).read_bytes())
            print(f'Loaded {args.state}', flush=True)
        else:
            emu.step(frames=1)
            print('No starting state found; booting ROM normally.', flush=True)
        print('Arrows = Move | Z = A | X = B | Enter = Start | Backspace = Select', flush=True)
        print('F5 = Save current position | ESC = Quit', flush=True)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_F5:
                        Path(args.output).write_bytes(emu.save_state())
                        pygame.display.set_caption(f'SAVED {args.output} | ESC Quit')
                        print(f'Saved {Path(args.output).resolve()}', flush=True)
            pressed = pygame.key.get_pressed()
            button = next((name for key, name in KEYS.items() if pressed[key]), None)
            frame = emu.step(button, frames=1)
            surface = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
            screen.blit(pygame.transform.scale(surface, (720, 480)), (0, 0))
            pygame.display.flip()
            clock.tick(60)
    finally:
        emu.close()
        pygame.quit()

if __name__ == '__main__':
    main()
