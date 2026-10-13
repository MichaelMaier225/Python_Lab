"""Self-contained tabular Q-learning in a simplified Center Perks-like grid.
This does not interface with the Steam game. No third-party packages required.
"""
import argparse
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / 'rl_model.json'
# # = wall, S = spawn, K = tool, F = fence, E = exit
MAP = [
    '#############',
    '#S....#.....#',
    '#.##..#..##.#',
    '#......K....#',
    '#..##...##..#',
    '#...........#',
    '#.###...###.#',
    '#.......F.E.#',
    '#############',
]
ACTIONS = ('up', 'down', 'left', 'right', 'use')
DIRECTIONS = ((0,-1),(0,1),(-1,0),(1,0),(0,0))
SPAWN = (1,1)
TOOL = (7,3)
FENCE = (8,7)
EXIT = (10,7)
MAX_STEPS = 180

def reset():
    return (*SPAWN, 0, 0)

def step(state, action):
    x,y,tool,cut = state
    dx,dy = DIRECTIONS[action]
    reward = -0.03
    if action == 4:
        if (x,y) == FENCE and tool and not cut:
            cut = 1
            reward = 6
        else:
            reward = -0.15
    else:
        nx,ny = x+dx,y+dy
        tile = MAP[ny][nx] if 0 <= ny < len(MAP) and 0 <= nx < len(MAP[0]) else '#'
        if tile == '#':
            reward = -0.2
        else:
            x,y = nx,ny
            if (x,y) == TOOL and not tool:
                tool = 1
                reward = 3
    won = (x,y) == EXIT and bool(cut)
    if won:
        reward = 25
    return (x,y,tool,cut), reward, won

def key(s):
    return ','.join(map(str,s))

def best_action(q, state):
    values = q.get(key(state), [0.0]*len(ACTIONS))
    top = max(values)
    return random.choice([i for i,v in enumerate(values) if v == top])

def run_episode(q, learn, epsilon=0.0, alpha=0.22, gamma=0.97):
    state = reset()
    for t in range(1, MAX_STEPS+1):
        action = random.randrange(len(ACTIONS)) if learn and random.random() < epsilon else best_action(q,state)
        new_state, reward, won = step(state, action)
        if learn:
            current = q.setdefault(key(state), [0.0]*len(ACTIONS))
            future = max(q.get(key(new_state), [0.0]*len(ACTIONS)))
            current[action] += alpha * (reward + (0 if won else gamma*future) - current[action])
        state = new_state
        if won:
            return True,t
    return False,MAX_STEPS

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--episodes',type=int,default=30000)
    parser.add_argument('--evaluate',type=int,default=200)
    parser.add_argument('--seed',type=int,default=42)
    args = parser.parse_args()
    random.seed(args.seed)
    q = {}
    wins = 0
    print('Training Q-learning agent in a simplified prison grid (NOT Steam gameplay).',flush=True)
    for ep in range(1,args.episodes+1):
        epsilon = max(0.03, 0.95*(1-ep/args.episodes)**1.7)
        won,_ = run_episode(q, True, epsilon)
        wins += int(won)
        if ep % max(1,args.episodes//10) == 0:
            print(f'Episode {ep:,}/{args.episodes:,} | recent training wins: {wins}/{max(1,args.episodes//10)} | epsilon={epsilon:.3f}',flush=True)
            wins = 0
    results = [run_episode(q,False) for _ in range(args.evaluate)]
    victories = [steps for win,steps in results if win]
    payload = {'algorithm':'tabular Q-learning','environment':'simplified simulated grid, NOT Steam game','map':MAP,'actions':ACTIONS,'episodes':args.episodes,'q_table':q}
    MODEL.write_text(json.dumps(payload),encoding='utf-8')
    print(f'\nEvaluation: {len(victories)}/{args.evaluate} escapes ({len(victories)/args.evaluate:.1%})')
    print(f'Average winning steps: {sum(victories)/len(victories):.1f}' if victories else 'No successful evaluations')
    print(f'Model saved: {MODEL}')
    print('IMPORTANT: This model cannot control the actual Steam game.')

if __name__ == '__main__':
    main()
