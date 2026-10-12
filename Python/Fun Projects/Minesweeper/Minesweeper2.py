import pyautogui
import time
import keyboard
import numpy as np
from PIL import ImageGrab
import random

# ====== CONFIG ======
min_x, min_y = 606, 401
max_x, max_y = 864, 654
tile_size = 16

target_color = (76, 84, 92)        # unopened tile
loss_color = (238, 102, 102)       # red explosion tile
restart_x, restart_y = 737, 345
restart_color = (27, 23, 2)

# ====== FUNCTIONS ======
def get_clickable_tiles():
    screenshot = ImageGrab.grab(bbox=(min_x, min_y, max_x, max_y)).convert("RGB")
    img = np.array(screenshot)

    clickable = []
    rows = (max_y - min_y) // tile_size
    cols = (max_x - min_x) // tile_size

    for row in range(rows):
        for col in range(cols):
            x = col * tile_size + tile_size // 2
            y = row * tile_size + tile_size // 2
            pixel = tuple(img[y, x])
            if pixel == target_color:
                screen_x = min_x + x
                screen_y = min_y + y
                clickable.append((screen_x, screen_y))
    return clickable

def is_loss():
    img = np.array(ImageGrab.grab(bbox=(min_x, min_y, max_x, max_y)).convert("RGB"))
    return np.any(np.all(img == loss_color, axis=-1))

def restart_game():
    for _ in range(30):
        if pyautogui.pixel(restart_x, restart_y) == restart_color:
            pyautogui.click(restart_x, restart_y)
            return
    pyautogui.click(restart_x, restart_y)

# ====== MAIN LOOP ======
time.sleep(1)  # Short countdown to let you switch windows

while True:
    if keyboard.is_pressed("esc"):
        break

    if is_loss():
        restart_game()
        continue

    clickable = get_clickable_tiles()
    if clickable:
        x, y = random.choice(clickable)
        pyautogui.click(x, y)
