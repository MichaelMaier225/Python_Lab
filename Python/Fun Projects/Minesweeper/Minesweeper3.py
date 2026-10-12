import pyautogui
import time
import keyboard
import numpy as np
from PIL import ImageGrab
import random
import json
import os

# ====== CONFIG ======
min_x, min_y = 606, 401
tile_size = 16
rows, cols = 9, 9

restart_x, restart_y = 737, 345
restart_color = (27, 23, 2)
loss_color = (238, 102, 102)
unopened_color = (76, 84, 92)
mine_color = (186, 186, 186)
flag_correct_color = (159, 80, 84)
flag_wrong_color = (255, 131, 131)

clicked_memory = set()
fail_threshold = 3

color_to_number = {
    (124, 199, 255): 1, (102, 194, 102): 2, (255, 119, 136): 3,
    (238, 136, 255): 4, (128, 0, 0): 5, (0, 128, 128): 6,
    (0, 0, 0): 7, (128, 128, 128): 8,
    unopened_color: -1
}

tile_coords = [[(min_x + col * tile_size + tile_size // 2,
                 min_y + row * tile_size + tile_size // 2)
                for col in range(cols)] for row in range(rows)]

memory_file = "fail_memory.json"
if os.path.exists(memory_file):
    with open(memory_file, "r") as f:
        data = json.load(f)
        fail_memory = {str(tuple(item)): 1 for item in data} if isinstance(data, list) else data
else:
    fail_memory = {}

def save_fail_memory():
    with open(memory_file, "w") as f:
        json.dump(fail_memory, f)

def get_board_state():
    board = []
    screenshot = ImageGrab.grab().convert("RGB")
    img = np.array(screenshot)
    for row in range(rows):
        board_row = []
        for col in range(cols):
            x, y = tile_coords[row][col]
            color = tuple(img[y, x])
            board_row.append(color_to_number.get(color, -99))
        board.append(board_row)
    return board

def click_tile(row, col):
    if (row, col) in clicked_memory:
        return
    clicked_memory.add((row, col))
    x, y = tile_coords[row][col]
    pyautogui.click(x, y)

def flag_tile(row, col):
    x, y = tile_coords[row][col]
    pyautogui.rightClick(x, y)

def get_neighbors(row, col):
    neighbors = []
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            nr, nc = row + dr, col + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                neighbors.append((nr, nc))
    return neighbors

def extract_pattern(row, col, board):
    pattern = []
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                pattern.append(board[nr][nc])
            else:
                pattern.append(None)
    return tuple(pattern)

def solve_board(board):
    actions = []
    for row in range(rows):
        for col in range(cols):
            val = board[row][col]
            if 1 <= val <= 8:
                neighbors = get_neighbors(row, col)
                unopened = [(r, c) for r, c in neighbors if board[r][c] == -1 and (r, c) not in clicked_memory]
                flagged = [(r, c) for r, c in neighbors if board[r][c] == 99]

                if len(unopened) > 0 and len(unopened) + len(flagged) == val:
                    for r, c in unopened:
                        actions.append(("flag", r, c))
                elif len(flagged) == val:
                    for r, c in unopened:
                        actions.append(("click", r, c))
    return actions

def is_loss_detected():
    img = np.array(ImageGrab.grab().convert("RGB"))
    return np.any(np.all(img == loss_color, axis=-1))

def learn_from_loss(board):
    img = np.array(ImageGrab.grab().convert("RGB"))
    for row in range(rows):
        for col in range(cols):
            x, y = tile_coords[row][col]
            pixel = tuple(img[y, x])
            pattern = extract_pattern(row, col, board)
            pattern_key = str(pattern)
            if pixel == mine_color:
                fail_memory[pattern_key] = fail_memory.get(pattern_key, 0) + 1
            elif pixel == flag_wrong_color:
                fail_memory[pattern_key] = fail_memory.get(pattern_key, 0) + 3
            elif pixel == flag_correct_color:
                fail_memory[pattern_key] = max(fail_memory.get(pattern_key, 1) - 1, 0)
    save_fail_memory()

def restart_game():
    clicked_memory.clear()
    for _ in range(30):
        if pyautogui.pixel(restart_x, restart_y) == restart_color:
            pyautogui.moveTo(restart_x, restart_y)
            time.sleep(0.05)
            pyautogui.click()
            return
        time.sleep(0.03)
    pyautogui.click(restart_x, restart_y)

# ====== MAIN LOOP ======
print("Starting in 3 seconds...")
time.sleep(3)

while True:
    if keyboard.is_pressed("esc"):
        break

    board = get_board_state()
    moves = solve_board(board)

    if not moves:
        unopened = [(r, c) for r in range(rows) for c in range(cols)
                    if board[r][c] == -1 and (r, c) not in clicked_memory]

        filtered = []
        for r, c in unopened:
            pattern = extract_pattern(r, c, board)
            if fail_memory.get(str(pattern), 0) < fail_threshold:
                filtered.append((r, c))

        if filtered:
            r, c = random.choice(filtered)
            click_tile(r, c)
        elif unopened:
            r, c = random.choice(unopened)
            click_tile(r, c)
    else:
        for action, r, c in moves:
            if action == "click":
                click_tile(r, c)
            elif action == "flag":
                flag_tile(r, c)
        time.sleep(0.01)

    if is_loss_detected():
        learn_from_loss(board)
        restart_game()
        time.sleep(0.3)
