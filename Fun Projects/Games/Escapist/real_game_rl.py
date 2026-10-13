"""Experimental live-game Q-learning interface. Requires user reward feedback.

No claim of autonomous escaping, inventory detection, or reset handling.
"""
import json
import random
import threading
import time
from pathlib import Path

import cv2
import mss
import numpy as np
import pydirectinput
import pygetwindow as gw
from pynput import keyboard

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / 'real_game_q.json'
LOG = ROOT / 'real_game_log.jsonl'
ACTIONS = ('w', 's', 'a', 'd')
lock = threading.Lock()
stop = False
feedback = 0.0

def on_press(key):
    global stop, feedback
    with lock:
        if key == keyboard.Key.f8:
            stop = True
        elif key == keyboard.Key.f6:
            feedback += 2.0
        elif key == keyboard.Key.f7:
            feedback -= 2.0

def game_window():
    matches = [w for w in gw.getAllWindows() if 'escapists' in w.title.lower() and w.width > 300 and w.height > 250]
    return matches[0] if matches else None

def observe(sct, win):
    if win.isMinimized or not win.isActive:
        return None
    box = {'left': max(0, win.left), 'top': max(0, win.top), 'width': win.width, 'height': win.height}
    shot = np.asarray(sct.grab(box))[:, :, :3]
    # Compact, quantized visual context. Similar images may still hash differently.
    gray = cv2.cvtColor(shot, cv2.COLOR_BGR2GRAY)
    tiny = cv2.resize(gray, (12, 9), interpolation=cv2.INTER_AREA)
    # Relative contrast reduces some lighting variation.
    bits = (tiny > float(np.median(tiny))).astype(np.uint8)
    return np.packbits(bits.ravel()).tobytes().hex()

def save(q):
    MODEL.write_text(json.dumps({'environment':'live Steam screen; experimental; human feedback', 'actions':ACTIONS, 'q_table':q}, indent=2), encoding='utf-8')

def main():
    global feedback
    win = game_window()
    if not win:
        print('Open The Escapists in windowed mode first.'); return
    try:
        q = json.loads(MODEL.read_text(encoding='utf-8')).get('q_table', {}) if MODEL.exists() else {}
    except (ValueError, OSError):
        q = {}
    print('LIVE GAME RL EXPERIMENT - not an autonomous escape bot')
    print('F6 = reward progress | F7 = penalize bad action | F8 = STOP')
    print('Moves are short and bounded. NO automatic reset, inventory, or escape detection.')
    print('Do not use on an important save. Stay in an open area.')
    ans = input('Type START to allow movement (anything else cancels): ').strip()
    if ans != 'START': return
    print('Focus the game within 5 seconds. F8 stops at any time.')
    time.sleep(5)
    pydirectinput.FAILSAFE = True
    pydirectinput.PAUSE = 0
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    last_state = None
    last_action = None
    steps = 0
    try:
        with mss.MSS() as sct, LOG.open('a', encoding='utf-8') as log:
            while steps < 150:
                with lock:
                    if stop: break
                    reward = feedback
                    feedback = 0.0
                win = game_window()
                if not win or not win.isActive:
                    print('Game not focused; stopping safely.'); break
                state = observe(sct, win)
                if state is None: break
                if last_state is not None:
                    old = q.setdefault(last_state, [0.0] * 4)
                    future = max(q.get(state, [0.0] * 4))
                    old[last_action] += 0.2 * (reward - 0.02 + 0.9 * future - old[last_action])
                vals = q.setdefault(state, [0.0] * 4)
                action = random.randrange(4) if random.random() < 0.25 else random.choice([i for i, v in enumerate(vals) if v == max(vals)])
                with lock:
                    if stop: break
                key = ACTIONS[action]
                pydirectinput.keyDown(key)
                try:
                    time.sleep(0.08)
                finally:
                    pydirectinput.keyUp(key)
                steps += 1
                log.write(json.dumps({'step':steps,'state':state,'action':key,'feedback':reward,'time':time.time()})+'\n')
                log.flush()
                last_state, last_action = state, action
                if steps % 10 == 0:
                    print(f'{steps}/150 moves | learned visual states: {len(q)} | F6/F7 reward | F8 stop', flush=True)
                time.sleep(0.6)
    finally:
        save(q)
        listener.stop()
        print(f'Stopped. Saved {MODEL.name} ({steps} game actions).')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted.')
    except Exception as exc:
        print('Error:', exc)
