"""Train PPO with a live grid and save sampled full-resolution frames for later replay."""
import argparse
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from environment import FireRedEnv


def make_env(core, rom, state, max_steps):
    def create():
        return Monitor(FireRedEnv(core, rom, state, max_steps=max_steps))
    return create


class RecordCallback(BaseCallback):
    def __init__(self, workers, record_every, show_every, save_every, output, recording, scale, jpeg_quality):
        super().__init__()
        self.workers, self.record_every, self.show_every = workers, record_every, show_every
        self.save_every, self.output, self.recording = save_every, output, recording
        self.scale, self.jpeg_quality = scale, jpeg_quality
        self.calls = 0
        self.last_save = 0
        self.capture_count = 0
        self.stop_requested = False
        self.pg = None
        self.archive = None

    def _on_training_start(self):
        import pygame
        self.pg = pygame
        pygame.init()
        cols = math.ceil(math.sqrt(self.workers * 1.5))
        self.cols, self.rows = cols, math.ceil(self.workers / cols)
        self.cell_w, self.cell_h = 240 * self.scale, 160 * self.scale
        self.screen = pygame.display.set_mode((self.cols * self.cell_w, self.rows * self.cell_h))
        pygame.display.set_caption('FireRed PPO - training + recording (Esc to save and stop)')
        self.archive = zipfile.ZipFile(self.recording, 'w', compression=zipfile.ZIP_STORED, allowZip64=True)
        self.archive.writestr('metadata.json', json.dumps({
            'format': 'firered-grid-replay-v1', 'agents': self.workers,
            'record_every': self.record_every, 'frames_per_action': 6,
            'note': 'Sampled training frames, not every emulator frame. Each column is one worker.'
        }))
        self.last_save = self.num_timesteps
        print(f'Recording sampled frames to {self.recording}')

    def _on_step(self):
        self.calls += 1
        for event in self.pg.event.get():
            if event.type == self.pg.QUIT or (event.type == self.pg.KEYDOWN and event.key == self.pg.K_ESCAPE):
                self.stop_requested = True
        should_record = self.calls % self.record_every == 0
        should_show = self.calls % self.show_every == 0
        if should_record or should_show:
            frames = self.training_env.env_method('render')
            if should_record:
                t = self.capture_count
                for i, frame in enumerate(frames):
                    buff = io.BytesIO()
                    Image.fromarray(np.asarray(frame, dtype=np.uint8), 'RGB').save(
                        buff, format='JPEG', quality=self.jpeg_quality, subsampling=0)
                    self.archive.writestr(f'frames/{t:07d}/{i:03d}.jpg', buff.getvalue())
                self.capture_count += 1
            if should_show:
                for i, frame in enumerate(frames):
                    rgb = np.ascontiguousarray(frame)
                    surf = self.pg.image.frombuffer(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]), 'RGB')
                    if self.scale != 1:
                        surf = self.pg.transform.scale(surf, (self.cell_w, self.cell_h))
                    self.screen.blit(surf, ((i % self.cols) * self.cell_w, (i // self.cols) * self.cell_h))
                self.pg.display.set_caption(f'FireRed PPO - {self.num_timesteps:,} steps - {self.capture_count} captures - Esc to stop')
                self.pg.display.flip()
        if self.num_timesteps - self.last_save >= self.save_every:
            self.model.save(self.output)
            self.last_save = self.num_timesteps
            print(f'Checkpoint saved: {self.output}.zip')
        return not self.stop_requested

    def _on_training_end(self):
        try:
            self.model.save(self.output)
            print(f'Model saved: {self.output}.zip')
        finally:
            if self.archive:
                self.archive.close()
                print(f'Recording saved: {self.recording} ({self.capture_count} snapshots per agent)')
            if self.pg:
                self.pg.quit()


def main():
    p = argparse.ArgumentParser(description='Live PPO training with replay recording')
    p.add_argument('--core', required=True)
    p.add_argument('--rom', required=True)
    p.add_argument('--state', default='firered_ingame.state')
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--steps', type=int, default=8192)
    p.add_argument('--max-episode-steps', type=int, default=4096)
    p.add_argument('--device', default='cpu')
    p.add_argument('--resume', default=None)
    p.add_argument('--output', default='firered_recorded')
    p.add_argument('--recording', default='firered_replay.zip')
    p.add_argument('--record-every', type=int, default=8, help='Save a screenshot per agent every N AI steps')
    p.add_argument('--show-every', type=int, default=8)
    p.add_argument('--save-every', type=int, default=10000)
    p.add_argument('--scale', type=int, default=2)
    p.add_argument('--jpeg-quality', type=int, default=85)
    a = p.parse_args()
    if min(a.workers, a.steps, a.max_episode_steps, a.record_every, a.show_every, a.save_every, a.scale) < 1:
        p.error('All counts must be positive')
    if not 1 <= a.jpeg_quality <= 100:
        p.error('--jpeg-quality must be 1..100')
    for path in [a.core, a.rom, a.state]:
        if not Path(path).is_file():
            p.error(f'File not found: {path}')
    if a.resume and not Path(a.resume).is_file():
        p.error(f'Resume model not found: {a.resume}')
    if Path(a.recording).resolve() == Path(a.output + '.zip').resolve():
        p.error('Recording and model output must be different files')
    env_fns = [make_env(str(Path(a.core).resolve()), str(Path(a.rom).resolve()),
                        str(Path(a.state).resolve()), a.max_episode_steps) for _ in range(a.workers)]
    env = SubprocVecEnv(env_fns, start_method='spawn') if a.workers > 1 else DummyVecEnv(env_fns)
    try:
        if a.resume:
            model = PPO.load(a.resume, env=env, device=a.device, tensorboard_log='logs')
            print(f'Resuming {a.resume}')
        else:
            model = PPO('CnnPolicy', env, verbose=1, device=a.device, n_steps=256,
                        batch_size=64, n_epochs=4, tensorboard_log='logs')
        callback = RecordCallback(a.workers, a.record_every, a.show_every, a.save_every,
                                  a.output, a.recording, a.scale, a.jpeg_quality)
        model.learn(total_timesteps=a.steps, callback=callback, progress_bar=True,
                    reset_num_timesteps=not bool(a.resume))
    finally:
        env.close()


if __name__ == '__main__':
    main()
