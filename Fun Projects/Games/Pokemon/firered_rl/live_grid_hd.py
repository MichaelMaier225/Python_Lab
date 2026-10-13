"""High-quality multi-agent FireRed PPO viewer (inference only, no training)."""
import argparse
import multiprocessing as mp
import time
import traceback
from pathlib import Path

import numpy as np


def worker(conn, core, rom, state, max_steps, frames_per_step):
    env = None
    try:
        from environment import FireRedEnv
        env = FireRedEnv(core, rom, state, max_steps=max_steps,
                         frames_per_step=frames_per_step)
        obs, _ = env.reset()
        conn.send(('ready', (obs, env.render())))
        while True:
            command, action = conn.recv()
            if command == 'close':
                break
            if command != 'step':
                raise ValueError(f'Unexpected command: {command}')
            obs, reward, terminated, truncated, _ = env.step(action)
            ended = terminated or truncated
            if ended:
                obs, _ = env.reset()
            conn.send(('step', (obs, env.render(), float(reward), ended)))
    except (EOFError, BrokenPipeError):
        pass
    except Exception:
        try:
            conn.send(('error', traceback.format_exc()))
        except Exception:
            pass
    finally:
        if env is not None:
            env.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Full-resolution live FireRed PPO grid')
    parser.add_argument('--core', required=True)
    parser.add_argument('--rom', required=True)
    parser.add_argument('--state', default='firered_ingame.state')
    parser.add_argument('--model', default='firered_ppo.zip')
    parser.add_argument('--agents', type=int, default=4)
    parser.add_argument('--columns', type=int, default=0, help='0 = automatic')
    parser.add_argument('--max-episode-steps', type=int, default=512)
    parser.add_argument('--frames-per-step', type=int, default=24)
    args = parser.parse_args()
    if not 1 <= args.agents <= 50:
        parser.error('--agents must be between 1 and 50')
    if args.columns < 0:
        parser.error('--columns must be nonnegative')
    for path in (args.core, args.rom, args.state, args.model):
        if not Path(path).is_file():
            parser.error(f'File not found: {path}')

    import pygame
    from stable_baselines3 import PPO
    pygame.init()
    display = pygame.display.Info()
    available_w = max(480, display.current_w - 90)
    available_h = max(320, display.current_h - 140)
    label_h = 22
    if args.columns:
        columns = min(args.columns, args.agents)
    else:
        candidates = []
        for cols in range(1, args.agents + 1):
            rows = (args.agents + cols - 1) // cols
            size = min(available_w // cols, (available_h // rows - label_h) * 3 // 2)
            candidates.append((size, -cols, cols))
        columns = max(candidates)[2]
    rows = (args.agents + columns - 1) // columns
    tile_w = max(80, min(available_w // columns, (available_h // rows - label_h) * 3 // 2))
    tile_h = max(54, tile_w * 2 // 3)
    if rows * (tile_h + label_h) > available_h:
        tile_h = max(54, available_h // rows - label_h)
        tile_w = tile_h * 3 // 2
    screen = pygame.display.set_mode((columns * tile_w, rows * (tile_h + label_h)))
    pygame.display.set_caption('FireRed PPO - full-resolution live grid (Esc to quit)')
    font = pygame.font.SysFont('consolas', 14)
    clock = pygame.time.Clock()
    model = PPO.load(args.model, device='cpu')
    ctx = mp.get_context('spawn')
    parents, processes = [], []
    observations = [None] * args.agents
    frames = [None] * args.agents
    rewards = [0.0] * args.agents
    episodes = [1] * args.agents
    try:
        print(f'Starting {args.agents} independent emulators...', flush=True)
        for _ in range(args.agents):
            parent, child = ctx.Pipe()
            process = ctx.Process(target=worker, args=(child, args.core, args.rom,
                                  args.state, args.max_episode_steps,
                                  args.frames_per_step), daemon=True)
            process.start()
            child.close()
            parents.append(parent)
            processes.append(process)
        for i, parent in enumerate(parents):
            if not parent.poll(120):
                raise RuntimeError(f'Agent {i + 1} did not initialize')
            kind, payload = parent.recv()
            if kind == 'error':
                raise RuntimeError(payload)
            observations[i], frames[i] = payload
        print('Live grid ready. Press Esc to quit.', flush=True)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
            if not running:
                break
            actions, _ = model.predict(np.stack(observations), deterministic=False)
            for parent, action in zip(parents, actions):
                parent.send(('step', int(action)))
            for i, parent in enumerate(parents):
                if not parent.poll(60):
                    raise RuntimeError(f'Agent {i + 1} timed out')
                kind, payload = parent.recv()
                if kind == 'error':
                    raise RuntimeError(payload)
                observations[i], frames[i], reward, ended = payload
                rewards[i] += reward
                if ended:
                    episodes[i] += 1
                    rewards[i] = 0.0
            screen.fill((18, 20, 24))
            for i, frame in enumerate(frames):
                x = (i % columns) * tile_w
                y = (i // columns) * (tile_h + label_h)
                surface = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
                if surface.get_size() != (tile_w, tile_h):
                    # Pixel-perfect enlargement when possible; high-quality reduction otherwise.
                    if tile_w >= 240 and tile_h >= 160:
                        surface = pygame.transform.scale(surface, (tile_w, tile_h))
                    else:
                        surface = pygame.transform.smoothscale(surface, (tile_w, tile_h))
                screen.blit(surface, (x, y))
                label = font.render(f'#{i+1}  E{episodes[i]}  R{rewards[i]:.1f}', True, (240, 240, 240))
                screen.blit(label, (x + 3, y + tile_h + 2))
            pygame.display.flip()
            clock.tick(30)
    finally:
        for parent in parents:
            try:
                parent.send(('close', None))
            except Exception:
                pass
            parent.close()
        for process in processes:
            process.join(timeout=2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
        pygame.quit()


if __name__ == '__main__':
    mp.freeze_support()
    main()
