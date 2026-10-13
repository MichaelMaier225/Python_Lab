"""Run parallel PPO training. Start with --workers 1 to verify the emulator."""
import argparse
from pathlib import Path
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from environment import FireRedEnv

def make_env(core, rom, state, max_steps):
    def init():
        return Monitor(FireRedEnv(core, rom, state, max_steps=max_steps))
    return init

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--core', required=True)
    p.add_argument('--rom', required=True)
    p.add_argument('--state', default='start.state')
    p.add_argument('--workers', type=int, default=1)
    p.add_argument('--steps', type=int, default=200_000)
    p.add_argument('--max-episode-steps', type=int, default=4096)
    p.add_argument('--device', default='auto')
    a = p.parse_args()
    if a.workers < 1:
        p.error('--workers must be >= 1')
    env_fns = [make_env(str(Path(a.core).resolve()), str(Path(a.rom).resolve()),
                        str(Path(a.state).resolve()), a.max_episode_steps) for _ in range(a.workers)]
    env = SubprocVecEnv(env_fns, start_method='spawn') if a.workers > 1 else DummyVecEnv(env_fns)
    try:
        model = PPO('CnnPolicy', env, verbose=1, device=a.device, n_steps=256,
                    batch_size=64, n_epochs=4, tensorboard_log='logs')
        model.learn(total_timesteps=a.steps, progress_bar=True)
        model.save('firered_ppo')
        print('Saved firered_ppo.zip')
    finally:
        env.close()
