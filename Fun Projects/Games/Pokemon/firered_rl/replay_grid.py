"""Replay the sampled game frames saved by train_record.py in a grid."""
import argparse
import io
import json
import math
import zipfile

import pygame


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--recording', default='firered_replay.zip')
    p.add_argument('--fps', type=float, default=12, help='Recorded snapshots per second')
    p.add_argument('--scale', type=int, default=2)
    p.add_argument('--loop', action='store_true')
    a = p.parse_args()
    if a.fps <= 0 or a.scale < 1:
        p.error('--fps and --scale must be positive')
    with zipfile.ZipFile(a.recording, 'r') as archive:
        meta = json.loads(archive.read('metadata.json'))
        if meta.get('format') != 'firered-grid-replay-v1':
            p.error('Unsupported recording format')
        agents = int(meta['agents'])
        ids = sorted({int(name.split('/')[1]) for name in archive.namelist()
                      if name.startswith('frames/') and name.endswith('.jpg')})
        if not ids:
            p.error('Recording contains no frames')
        cols = math.ceil(math.sqrt(agents * 1.5))
        rows = math.ceil(agents / cols)
        cell_w, cell_h = 240 * a.scale, 160 * a.scale
        pygame.init()
        screen = pygame.display.set_mode((cols * cell_w, rows * cell_h), pygame.RESIZABLE)
        clock = pygame.time.Clock()
        playing, index, running = True, 0, True
        try:
            while running:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_SPACE:
                            playing = not playing
                        elif event.key == pygame.K_RIGHT:
                            index = min(index + 1, len(ids) - 1)
                            playing = False
                        elif event.key == pygame.K_LEFT:
                            index = max(index - 1, 0)
                            playing = False
                        elif event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS):
                            a.fps = min(120, a.fps * 2)
                        elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                            a.fps = max(0.5, a.fps / 2)
                screen.fill((15, 15, 15))
                for agent in range(agents):
                    key = f'frames/{ids[index]:07d}/{agent:03d}.jpg'
                    try:
                        surf = pygame.image.load(io.BytesIO(archive.read(key)), 'frame.jpg')
                    except KeyError:
                        continue
                    surf = pygame.transform.scale(surf, (cell_w, cell_h))
                    screen.blit(surf, ((agent % cols) * cell_w, (agent // cols) * cell_h))
                pygame.display.set_caption(
                    f'FireRed replay - frame {index+1}/{len(ids)} - {a.fps:g} snapshots/s - '
                    'Space pause | arrows seek | +/- speed | Esc quit')
                pygame.display.flip()
                if playing:
                    if index + 1 < len(ids):
                        index += 1
                    elif a.loop:
                        index = 0
                    else:
                        playing = False
                clock.tick(a.fps if playing else 30)
        finally:
            pygame.quit()


if __name__ == '__main__':
    main()
