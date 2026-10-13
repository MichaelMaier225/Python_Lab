"""Watch a trained Stable-Baselines3 PPO agent play Pokemon FireRed.

Requires the existing emulator.py, environment.py, mgba_libretro.dll,
FireRed ROM, saved starting state, and firered_ppo.zip.
"""
import argparse
from pathlib import Path

import numpy as np
import pygame
from stable_baselines3 import PPO
from environment import ACTIONS, FireRedEnv


def main():
    parser = argparse.ArgumentParser(description='Watch the trained FireRed PPO agent')
    parser.add_argument('--core', required=True, help='Path to mgba_libretro.dll')
    parser.add_argument('--rom', required=True, help='Path to the FireRed .gba ROM')
    parser.add_argument('--state', default='firered_start.state')
    parser.add_argument('--model', default='firered_ppo.zip')
    parser.add_argument('--scale', type=int, default=3)
    parser.add_argument('--fps', type=int, default=10, help='AI actions per second (each action runs 24 game frames)')
    parser.add_argument('--max-episode-steps', type=int, default=512)
    args = parser.parse_args()

    for path in (args.core, args.rom, args.state, args.model):
        if not Path(path).is_file():
            parser.error(f'File not found: {path}')

    model = PPO.load(args.model, device='cpu')
    env = FireRedEnv(args.core, args.rom, args.state, max_steps=args.max_episode_steps)
    pygame.init()
    scale = max(1, args.scale)
    window = pygame.display.set_mode((240 * scale, 160 * scale + 36))
    pygame.display.set_caption('FireRed PPO — AI Playback (ESC to quit)')
    font = pygame.font.SysFont(None, 22)
    clock = pygame.time.Clock()
    obs, _ = env.reset()
    reward_total = 0.0
    episode = 1
    running = True

    try:
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
            if not running:
                break

            # VecTransposeImage used during training changes HWC observations to CHW.
            expected = tuple(model.observation_space.shape)
            if expected == tuple(obs.shape):
                model_obs = obs
            elif expected == (3, obs.shape[0], obs.shape[1]):
                model_obs = np.transpose(obs, (2, 0, 1)).copy()
            else:
                raise RuntimeError(f'Model expects {expected}, but environment returns {obs.shape}')

            action, _ = model.predict(model_obs, deterministic=True)
            action_id = int(np.asarray(action).item())
            obs, reward, terminated, truncated, info = env.step(action_id)
            reward_total += float(reward)

            # pygame.surfarray.make_surface expects (width, height, channels).
            frame = env.render()
            surface = pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))
            surface = pygame.transform.scale(surface, (240 * scale, 160 * scale))
            window.blit(surface, (0, 0))
            pygame.draw.rect(window, (20, 20, 20), (0, 160 * scale, 240 * scale, 36))
            button = ACTIONS[action_id] or 'none'
            status = f'Ep {episode} | Step {env.steps} | {button} | Reward {reward_total:.2f}'
            window.blit(font.render(status, True, (255, 255, 255)), (8, 160 * scale + 9))
            pygame.display.flip()

            if terminated or truncated:
                episode += 1
                obs, _ = env.reset()
                reward_total = 0.0
            clock.tick(max(1, args.fps))
    finally:
        env.close()
        pygame.quit()


if __name__ == '__main__':
    main()
