"""Gymnasium environment for FireRed with conservative visual exploration rewards.

Visual novelty is a proxy, not verified tile/map/town exploration. Real tile and
map bonuses require verified player coordinates and map IDs from the emulator.
"""
import hashlib

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from emulator import Emulator

ACTIONS = ['up', 'down', 'left', 'right', 'a', 'b', 'start', None]


class FireRedEnv(gym.Env):
    metadata = {'render_modes': ['rgb_array']}

    def __init__(self, core, rom, state_file, max_steps=4096, frames_per_step=6):
        super().__init__()
        self.emu = Emulator(core, rom)
        self.max_steps = max_steps
        self.frames_per_step = frames_per_step
        self.action_space = spaces.Discrete(len(ACTIONS))
        self.observation_space = spaces.Box(0, 255, (72, 80, 3), dtype=np.uint8)
        with open(state_file, 'rb') as f:
            self.initial_state = f.read()
        self.seen = set()
        self.steps = 0
        self.last_obs = None
        self.still_steps = 0

    def _observe(self):
        frame = self.emu.frame
        if frame.shape[0] < 144 or frame.shape[1] < 240:
            raise RuntimeError(f'Unexpected video resolution: {frame.shape}')
        return frame[8:152:2, ::3, :].copy()

    def _fingerprint(self, obs):
        # Quantization and coarse sampling reduce sensitivity to tiny animations.
        small = (obs[::8, ::8, :] // 32).tobytes()
        return hashlib.blake2b(small, digest_size=8).digest()

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.emu.load_state(self.initial_state)
        self.steps = 0
        self.still_steps = 0
        self.seen.clear()
        self.last_obs = self._observe()
        self.seen.add(self._fingerprint(self.last_obs))
        return self.last_obs, {}

    def step(self, action):
        action = int(action)
        self.emu.step(ACTIONS[action], self.frames_per_step)
        self.steps += 1
        obs = self._observe()
        fp = self._fingerprint(obs)
        novel = fp not in self.seen
        self.seen.add(fp)

        # Compare sampled pixels, ignoring small frame-to-frame visual changes.
        old = self.last_obs[::4, ::4, :].astype(np.int16)
        new = obs[::4, ::4, :].astype(np.int16)
        change_fraction = float(np.mean(np.max(np.abs(new - old), axis=2) > 40))
        changed = change_fraction >= 0.08
        moving = action < 4

        if moving and not changed:
            self.still_steps += 1
        else:
            self.still_steps = 0

        # Reward distinct visual states only after directional input and a
        # meaningful image change. This does not prove the player moved a tile.
        reward = -0.001
        if novel and moving and changed:
            reward += 0.25
        if self.still_steps >= 5:
            reward -= 0.01

        self.last_obs = obs
        truncated = self.steps >= self.max_steps
        return obs, reward, False, truncated, {
            'unique_screens': len(self.seen),
            'visual_change_fraction': change_fraction,
            'still_steps': self.still_steps,
        }

    def render(self):
        return self.emu.frame.copy()

    def close(self):
        self.emu.close()
