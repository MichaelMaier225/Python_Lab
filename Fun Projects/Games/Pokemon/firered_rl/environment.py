"""Gymnasium environment for FireRed. Rewards exploration and screen novelty.

This is a baseline, NOT a completed-game agent. It deliberately avoids unverified
FireRed RAM offsets. Improve rewards using verified offsets for your ROM revision.
"""
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

    def _observe(self):
        # Integer downsample to 80x72 from 240x160, crop to 144 high.
        frame = self.emu.frame
        if frame.shape[0] < 144 or frame.shape[1] < 240:
            raise RuntimeError(f'Unexpected video resolution: {frame.shape}')
        return frame[8:152:2, ::3, :].copy()

    def _fingerprint(self, obs):
        # Low-resolution quantized signature. Novelty is imperfect, but cheap.
        import hashlib
        small = (obs[::8, ::8, :] // 32).tobytes()
        return hashlib.blake2b(small, digest_size=8).digest()

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.emu.load_state(self.initial_state)
        self.steps = 0
        self.seen.clear()
        self.last_obs = self._observe()
        self.seen.add(self._fingerprint(self.last_obs))
        return self.last_obs, {}

    def step(self, action):
        self.emu.step(ACTIONS[int(action)], self.frames_per_step)
        self.steps += 1
        obs = self._observe()
        fp = self._fingerprint(obs)
        novel = fp not in self.seen
        self.seen.add(fp)
        reward = (0.1 if novel else 0.0) - 0.001
        truncated = self.steps >= self.max_steps
        self.last_obs = obs
        return obs, reward, False, truncated, {'unique_screens': len(self.seen)}

    def render(self):
        return self.emu.frame.copy()

    def close(self):
        self.emu.close()
