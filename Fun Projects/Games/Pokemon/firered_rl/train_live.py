"""Train a shared PPO model with multiple FireRed instances and a live pixel-art grid.

Run from the firered_rl directory, alongside environment.py and emulator.py.
"""
import argparse
import math
from pathlib import Path

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from environment import FireRedEnv


def make_env(core, rom, state, max_steps):
    def create():
        return Monitor(FireRedEnv(core, rom, state, max_steps=max_steps))
    return create


class LiveGridCallback(BaseCallback):
    def __init__(self, workers, show_every=64, save_every=10000, output='firered_live', scale=2):
        super().__init__()
        self.workers = workers
        self.show_every = show_every
        self.save_every = save_every
        self.output = output
        self.scale = scale
        self.last_save = 0
        self.calls = 0
        self.pg = None
        self.screen = None

    def _on_training_start(self):
        import pygame
        self.pg = pygame
        pygame.init()
        self.cols = math.ceil(math.sqrt(self.workers))
        self.rows = math.ceil(self.workers / self.cols)
        self.cell_w, self.cell_h = 240 * self.scale, 160 * self.scale
        self.screen = pygame.display.set_mode((self.cols * self.cell_w, self.rows * self.cell_h))
        pygame.display.set_caption('FireRed PPO — LIVE TRAINING (Esc to stop and save)')
        self.screen.fill((15, 15, 15))
        pygame.display.flip()
        self.last_save = self.num_timesteps

    def _on_step(self):
        self.calls += 1
        for event in self.pg.event.get():
            if event.type == self.pg.QUIT or (event.type == self.pg.KEYDOWN and event.key == self.pg.K_ESCAPE):
                print('Stopping training; saving checkpoint...')
                return False

        if self.calls % self.show_every == 0:
            # Fetch actual 240x160 RGB frames, not the downsampled PPO observations.
            frames = self.training_env.env_method('render')
            for i, frame in enumerate(frames):
                rgb = np.ascontiguousarray(frame)
                surface = self.pg.image.frombuffer(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]), 'RGB')
                if self.scale != 1:
                    surface = self.pg.transform.scale(surface, (self.cell_w, self.cell_h))
                self.screen.blit(surface, ((i % self.cols) * self.cell_w, (i // self.cols) * self.cell_h))
            self.pg.display.set_caption(f'FireRed PPO — {self.num_timesteps:,} training steps — Esc saves and exits')
            self.pg.display.flip()

        if self.num_timesteps - self.last_save >= self.save_every:
            self.model.save(self.output)
            self.last_save = self.num_timesteps
            print(f'Saved checkpoint: {self.output}.zip at {self.num_timesteps:,} steps')
        return True

    def _on_training_end(self):
        self.model.save(self.output)
        print(f'Saved model: {self.output}.zip ({self.num_timesteps:,} total steps)')
        if self.pg:
            self.pg.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--core', required=True)
    parser.add_argument('--rom', required=True)
    parser.add_argument('--state', default='firered_ingame.state')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--steps', type=int, default=8192)
    parser.add_argument('--max-episode-steps', type=int, default=4096)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--resume', default=None, help='Existing PPO .zip model; omit to train a new model')
    parser.add_argument('--output', default='firered_live', help='Checkpoint basename, distinct from original firered_ppo')
    parser.add_argument('--show-every', type=int, default=64, help='Viewer update every N vector steps')
    parser.add_argument('--save-every', type=int, default=10000, help='Save checkpoint every N total steps')
    parser.add_argument('--scale', type=int, default=2)
    args = parser.parse_args()
    if args.workers < 1 or args.steps < 1 or args.show_every < 1 or args.scale < 1 or args.save_every < 1:
        parser.error('workers, steps, show-every, scale and save-every must all be positive')
    for path in [args.core, args.rom, args.state]:
        if not Path(path).is_file():
            parser.error(f'File not found: {path}')
    if args.resume and not Path(args.resume).is_file():
        parser.error(f'Resume model not found: {args.resume}')
    envs = [make_env(str(Path(args.core).resolve()), str(Path(args.rom).resolve()),
                     str(Path(args.state).resolve()), args.max_episode_steps)
            for _ in range(args.workers)]
    env = SubprocVecEnv(envs, start_method='spawn') if args.workers > 1 else DummyVecEnv(envs)
    try:
        if args.resume:
            model = PPO.load(args.resume, env=env, device=args.device, tensorboard_log='logs')
            print(f'Resuming from {args.resume}')
        else:
            model = PPO('CnnPolicy', env, verbose=1, device=args.device, n_steps=256,
                        batch_size=64, n_epochs=4, tensorboard_log='logs')
        callback = LiveGridCallback(args.workers, args.show_every, args.save_every, args.output, args.scale)
        model.learn(total_timesteps=args.steps, callback=callback, progress_bar=True,
                    reset_num_timesteps=not bool(args.resume))
    finally:
        env.close()


if __name__ == '__main__':
    main()
