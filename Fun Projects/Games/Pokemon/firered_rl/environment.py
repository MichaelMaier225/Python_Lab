"""FireRed visual exploration without menu/save reward exploits.

Visual novelty is only an approximation; actual story milestones require RAM access.
"""
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from emulator import Emulator

# Preserve the existing PPO action and observation spaces for checkpoint compatibility.
ACTIONS = ['up', 'down', 'left', 'right', 'a', 'b', None, None]  # Start disabled; preserve 8 actions


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
        self.steps = 0
        self.scene_changes = 0
        self.last_obs = None
        self.last_action = None
        self.repeat_steps = 0
        self.still_steps = 0
        self.no_novelty_steps = 0
        self.seen_views = []
        self.scene_anchor = None
        self.scene_cooldown = 0
        self.dialogue_was_open = False
        self.interacted_views = []
        self.interactions = 0
        self.movement_streak = 0
        self.rewarded_milestones = set()
        self.verified_events = 0
        self.stuck_penalties = 0
        self.recent_views = []
        self.loop_penalties = 0
        self.last_loop_penalty_step = -10_000

    def _observe(self):
        frame = self.emu.frame
        if frame.shape[0] < 144 or frame.shape[1] < 240:
            raise RuntimeError(f'Unexpected video resolution: {frame.shape}')
        return frame[8:152:2, ::3, :].copy()

    @staticmethod
    def _difference(a, b):
        x = a[::4, ::4, :].astype(np.int16)
        y = b[::4, ::4, :].astype(np.int16)
        return float(np.mean(np.max(np.abs(x - y), axis=2) > 40))

    @staticmethod
    def _view_signature(obs):
        # Downsample to a coarse scene representation; blur over sprite animations.
        # Retain a grid of 9x10 average RGB blocks (72x80 input).
        x = obs.astype(np.uint16).reshape(9, 8, 10, 8, 3)
        return (x.mean(axis=(1, 3)) // 32).astype(np.uint8)

    @staticmethod
    def _view_distance(a, b):
        # Fraction of coarse blocks whose colors differ meaningfully.
        return float(np.mean(np.max(np.abs(a.astype(np.int16) - b.astype(np.int16)), axis=2) >= 2))

    @staticmethod
    def _dialogue_visible(frame):
        """Heuristic for FireRed's wide, bright bottom dialogue box.

        Requires a light interior across most of the bottom screen and a
        darker band immediately above. This is not a story-state detector.
        """
        if frame.shape[0] < 160 or frame.shape[1] < 240:
            return False
        interior = frame[133:149, 20:218, :].astype(np.int16)
        bright = np.mean(np.min(interior, axis=2) > 175)
        # The dialogue panel usually covers most of the lower screen.
        return bool(bright > 0.56)

    def _verified_progress_reward(self):
        """Reward ONLY confirmed game events supplied by a memory-backed detector.

        Current emulator has no pop_progress_events method, so this safely
        returns zero until a reliable battle/party detector is implemented.
        """
        get_events = getattr(self.emu, 'pop_progress_events', None)
        if get_events is None:
            return 0.0
        weights = {
            'wild_pokemon_defeated': 0.5,
            'trainer_pokemon_defeated': 2.0,
            'trainer_battle_won': 10.0,
            'battle_lost': -1.0,
            'new_species_obtained': 10.0,
            'duplicate_species_captured': -0.01,
            'starter_obtained': 25.0,
            'gym_leader_defeated': 100.0,
            'badge_earned': 150.0,
            'story_milestone': 50.0,
            'champion': 1000.0,
        }
        once = {'trainer_battle_won', 'new_species_obtained',
                'starter_obtained', 'gym_leader_defeated',
                'badge_earned', 'story_milestone', 'champion'}
        total = 0.0
        for event in get_events() or ():
            if not isinstance(event, dict):
                continue
            kind = event.get('type')
            if kind not in weights:
                continue
            if kind in once:
                key = event.get('id')
                if not isinstance(key, (str, int)) or key == '':
                    continue
                token = (kind, key)
                if token in self.rewarded_milestones:
                    continue
                self.rewarded_milestones.add(token)
            total += weights[kind]
            self.verified_events += 1
        return total

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self.emu.load_state(self.initial_state)
        self.steps = self.scene_changes = self.repeat_steps = 0
        self.still_steps = self.no_novelty_steps = self.scene_cooldown = 0
        self.last_action = None
        self.last_obs = self._observe()
        self.scene_anchor = self.last_obs.copy()
        self.seen_views = [self._view_signature(self.last_obs)]
        self.dialogue_was_open = self._dialogue_visible(self.emu.frame)
        self.interacted_views = []
        self.interactions = 0
        self.movement_streak = 0
        self.rewarded_milestones.clear()
        self.verified_events = 0
        self.stuck_penalties = 0
        self.recent_views = [self._view_signature(self.last_obs)]
        self.loop_penalties = 0
        self.last_loop_penalty_step = -10_000
        return self.last_obs, {}

    def step(self, action):
        action = int(action)
        self.emu.step(ACTIONS[action], self.frames_per_step)
        self.steps += 1
        self.movement_streak = self.movement_streak + 1 if action < 4 else 0
        obs = self._observe()
        change = self._difference(self.last_obs, obs)
        reward = -0.003

        self.repeat_steps = self.repeat_steps + 1 if action == self.last_action else 1
        # A screen that doesn't change while pressing a direction suggests a wall.
        self.still_steps = self.still_steps + 1 if action < 4 and change < 0.018 else 0
        # Penalize repeatedly walking into a wall, without punishing
        # legitimate pauses for dialogue, menus, or animations.
        if action < 4 and self.still_steps >= 5 and not self._dialogue_visible(self.emu.frame):
            reward -= 0.01
            self.stuck_penalties += 1
        if (action < 4 and self.repeat_steps >= 16 and change < 0.03
                and not self._dialogue_visible(self.emu.frame)):
            reward -= 0.01
            self.stuck_penalties += 1

        # Only reward distinct views caused by movement, not opening menus/dialogue.
        novel = False
        if (action < 4 and self.movement_streak >= 3 and change >= 0.04
                and not self._dialogue_visible(self.emu.frame)
                and self.steps % 3 == 0):
            sig = self._view_signature(obs)
            if all(self._view_distance(sig, old) >= 0.18 for old in self.seen_views):
                self.seen_views.append(sig)
                if len(self.seen_views) > 512:
                    self.seen_views.pop(1)  # Keep initial view as an anchor.
                reward += 0.035
                novel = True
        self.no_novelty_steps = 0 if novel else self.no_novelty_steps + 1

        # Penalize repeatedly revisiting near-identical views while moving.
        # This visual proxy is imperfect, so it ignores very recent frames and
        # limits the penalty to once every 8 decisions.
        sig = self._view_signature(obs)
        loop_match = False
        if action < 4 and change >= 0.018 and not self._dialogue_visible(self.emu.frame):
            for age, old_sig in enumerate(reversed(self.recent_views[1:]), start=1):
                if age < 6:
                    continue
                if self._view_distance(sig, old_sig) < 0.08:
                    loop_match = True
                    break

        if loop_match and (self.steps - self.last_loop_penalty_step) >= 8:
            reward -= 0.02
            self.loop_penalties += 1
            self.last_loop_penalty_step = self.steps

        self.recent_views.append(sig)
        if len(self.recent_views) > 80:
            self.recent_views.pop(1)  # Preserve the initial view as a reference.

        if self.scene_cooldown:
            self.scene_cooldown -= 1
        if (action < 4 and self.movement_streak >= 3 and self.scene_cooldown == 0
                and not self._dialogue_visible(self.emu.frame)
                and self._difference(self.scene_anchor, obs) > 0.65
                and change > 0.35):
            # Large visual transition, not verified as a map change.
            self.scene_anchor = obs.copy()
            self.scene_cooldown = 128
            self.scene_changes += 1
            reward += 1.5

        # No dialogue/menu reward: text boxes, Save, and menus are easy to farm.
        # A still works for NPC conversations and story interactions.
        self.dialogue_was_open = self._dialogue_visible(self.emu.frame)

        reward += self._verified_progress_reward()
        self.last_obs = obs
        self.last_action = action
        # Low novelty alone must not reset an episode: the agent may be stuck
        # navigating indoors or handling a story interaction.
        truncated = self.steps >= self.max_steps
        return obs, float(reward), False, truncated, {
            'scene_changes': self.scene_changes,
            'unique_views': len(self.seen_views),
            'new_interactions': self.interactions,
            'visual_change_fraction': change,
            'still_steps': self.still_steps,
            'stuck_penalties': self.stuck_penalties,
            'loop_penalties': self.loop_penalties,
            'no_novelty_steps': self.no_novelty_steps,
            'reward': float(reward),
            'verified_progress_events': self.verified_events,
        }

    def render(self):
        return self.emu.frame.copy()

    def close(self):
        self.emu.close()
