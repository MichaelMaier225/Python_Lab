"""Train PPO with a live grid and save sampled frames for later replay.

Project files are organized automatically:
  models/      PPO checkpoints
  recordings/  replay ZIP archives
  states/      emulator save states

Relative paths are resolved from this script's directory, not the shell's
current working directory. Existing model/replay files are not moved or deleted.
"""
from __future__ import annotations

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


ROOT = Path(__file__).resolve().parent


def _is_absolute_or_has_parent(path: str | Path) -> bool:
    p = Path(path)
    return p.is_absolute() or len(p.parts) > 1


def resolve_input_path(value: str | Path, preferred_folder: str | None = None) -> Path:
    """Resolve an input path, supporting files moved into organized folders."""
    p = Path(value).expanduser()
    if p.is_absolute():
        return p.resolve()

    direct = (ROOT / p).resolve()
    if direct.is_file():
        return direct

    # If a previously-root-level file was organized, transparently find it.
    if preferred_folder and not _is_absolute_or_has_parent(p):
        organized = (ROOT / preferred_folder / p.name).resolve()
        if organized.is_file():
            return organized

    # Also support a path such as .\firered_outside.state after it was moved.
    if preferred_folder and p.suffix.lower() == ".state":
        organized = (ROOT / preferred_folder / p.name).resolve()
        if organized.is_file():
            return organized

    return direct


def resolve_output_path(value: str | Path, default_folder: str) -> Path:
    """Resolve an output path and place bare filenames in their standard folder."""
    p = Path(value).expanduser()
    if p.is_absolute():
        result = p
    elif len(p.parts) == 1:
        result = ROOT / default_folder / p
    else:
        result = ROOT / p
    result = result.resolve()
    result.parent.mkdir(parents=True, exist_ok=True)
    return result


def unused_recording_path(path: Path) -> Path:
    """Avoid silently replacing an earlier replay recording."""
    if not path.exists():
        return path
    for index in range(2, 100000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find an unused recording filename for {path}")


def make_env(core: str, rom: str, state: str, max_steps: int):
    def create():
        return Monitor(FireRedEnv(core, rom, state, max_steps=max_steps))
    return create


class RecordCallback(BaseCallback):
    def __init__(self, workers, visible, record_every, show_every, save_every,
                 output, recording, scale, jpeg_quality):
        super().__init__()
        self.workers, self.visible = workers, min(visible, workers)
        self.record_every, self.show_every = record_every, show_every
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
        cols = math.ceil(math.sqrt(self.visible * 1.5))
        self.cols, self.rows = cols, math.ceil(self.visible / cols)
        self.cell_w, self.cell_h = 240 * self.scale, 160 * self.scale
        self.screen = pygame.display.set_mode((self.cols * self.cell_w, self.rows * self.cell_h))
        pygame.display.set_caption('FireRed PPO - training + recording (Esc to save and stop)')

        self.recording.parent.mkdir(parents=True, exist_ok=True)
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.archive = zipfile.ZipFile(self.recording, 'w', compression=zipfile.ZIP_STORED, allowZip64=True)
        self.archive.writestr('metadata.json', json.dumps({
            'format': 'firered-grid-replay-v1', 'agents': self.visible,
            'training_workers': self.workers, 'record_every': self.record_every,
            'frames_per_action': 6,
            'note': 'Sampled frames from the first visible workers; all workers contribute to PPO training.'
        }))
        self.last_save = self.num_timesteps
        print(f'Training {self.workers} agents; displaying and recording {self.visible}')
        print(f'Model checkpoints: {self.output}.zip')
        print(f'Recording sampled frames to {self.recording}')

    def _on_step(self):
        self.calls += 1
        for event in self.pg.event.get():
            if event.type == self.pg.QUIT or (
                event.type == self.pg.KEYDOWN and event.key == self.pg.K_ESCAPE
            ):
                self.stop_requested = True

        should_record = self.calls % self.record_every == 0
        should_show = self.calls % self.show_every == 0
        if should_record or should_show:
            frames = self.training_env.env_method('render', indices=list(range(self.visible)))
            if should_record:
                t = self.capture_count
                for i, frame in enumerate(frames):
                    buff = io.BytesIO()
                    Image.fromarray(np.asarray(frame, dtype=np.uint8), 'RGB').save(
                        buff, format='JPEG', quality=self.jpeg_quality, subsampling=0
                    )
                    self.archive.writestr(f'frames/{t:07d}/{i:03d}.jpg', buff.getvalue())
                self.capture_count += 1

            if should_show:
                for i, frame in enumerate(frames):
                    rgb = np.ascontiguousarray(frame)
                    surf = self.pg.image.frombuffer(rgb.tobytes(), (rgb.shape[1], rgb.shape[0]), 'RGB')
                    if self.scale != 1:
                        surf = self.pg.transform.scale(surf, (self.cell_w, self.cell_h))
                    self.screen.blit(surf, ((i % self.cols) * self.cell_w, (i // self.cols) * self.cell_h))
                self.pg.display.set_caption(
                    f'FireRed PPO - {self.num_timesteps:,} steps - {self.capture_count} captures - Esc to stop'
                )
                self.pg.display.flip()

        if self.num_timesteps - self.last_save >= self.save_every:
            self.model.save(str(self.output))
            self.last_save = self.num_timesteps
            print(f'Checkpoint saved: {self.output}.zip')
        return not self.stop_requested

    def _on_training_end(self):
        try:
            self.model.save(str(self.output))
            print(f'Model saved: {self.output}.zip')
        finally:
            if self.archive:
                self.archive.close()
                print(f'Recording saved: {self.recording} ({self.capture_count} snapshots per visible agent)')
            if self.pg:
                self.pg.quit()


def main():
    parser = argparse.ArgumentParser(description='Live PPO training with replay recording')
    parser.add_argument('--core', required=True)
    parser.add_argument('--rom', required=True)
    parser.add_argument('--state', default='firered_ingame.state')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--visible', type=int, default=2, help='How many workers to show and record (the first N)')
    parser.add_argument('--steps', type=int, default=8192)
    parser.add_argument('--max-episode-steps', type=int, default=4096)
    parser.add_argument('--device', default='cpu')
    parser.add_argument('--resume', default=None)
    parser.add_argument('--output', default='firered_recorded')
    parser.add_argument('--recording', default='firered_replay.zip')
    parser.add_argument('--record-every', type=int, default=64, help='Save a screenshot per visible agent every N AI steps; larger values use less storage')
    parser.add_argument('--show-every', type=int, default=16)
    parser.add_argument('--save-every', type=int, default=10000)
    parser.add_argument('--scale', type=int, default=1)
    parser.add_argument('--jpeg-quality', type=int, default=70)
    args = parser.parse_args()

    if min(args.workers, args.visible, args.steps, args.max_episode_steps,
           args.record_every, args.show_every, args.save_every, args.scale) < 1:
        parser.error('All counts must be positive')
    if args.visible > args.workers:
        print(f'Note: --visible {args.visible} exceeds --workers {args.workers}; showing all {args.workers} workers.')
    if not 1 <= args.jpeg_quality <= 100:
        parser.error('--jpeg-quality must be 1..100')

    core_path = resolve_input_path(args.core)
    rom_path = resolve_input_path(args.rom)
    state_path = resolve_input_path(args.state, 'states')
    resume_path = resolve_input_path(args.resume, 'models') if args.resume else None

    for label, path in [('core', core_path), ('ROM', rom_path), ('state', state_path)]:
        if not path.is_file():
            parser.error(f'{label} file not found: {path}')
    if resume_path and not resume_path.is_file():
        parser.error(f'Resume model not found: {resume_path}')

    output_path = resolve_output_path(args.output, 'models')
    recording_path = unused_recording_path(resolve_output_path(args.recording, 'recordings'))
    if recording_path == output_path or recording_path == Path(str(output_path) + '.zip'):
        parser.error('Recording and model output must be different files')

    print(f'Project folder: {ROOT}')
    print(f'Save state: {state_path}')
    print(f'Model output: {output_path}.zip')
    print(f'Recording output: {recording_path}')
    if resume_path:
        print(f'Resuming from: {resume_path}')

    env_fns = [make_env(str(core_path), str(rom_path), str(state_path), args.max_episode_steps)
               for _ in range(args.workers)]
    env = SubprocVecEnv(env_fns, start_method='spawn') if args.workers > 1 else DummyVecEnv(env_fns)
    try:
        if resume_path:
            model = PPO.load(str(resume_path), env=env, device=args.device, tensorboard_log=str(ROOT / 'logs'))
            print(f'Resuming {resume_path}')
        else:
            model = PPO('CnnPolicy', env, verbose=1, device=args.device, n_steps=256,
                        batch_size=64, n_epochs=4, tensorboard_log=str(ROOT / 'logs'))
        callback = RecordCallback(
            args.workers, args.visible, args.record_every, args.show_every, args.save_every,
            output_path, recording_path, args.scale, args.jpeg_quality
        )
        model.learn(total_timesteps=args.steps, callback=callback, progress_bar=True,
                    reset_num_timesteps=not bool(resume_path))
    finally:
        env.close()


if __name__ == '__main__':
    main()
