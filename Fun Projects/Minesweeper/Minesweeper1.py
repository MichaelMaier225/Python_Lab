import pyautogui
import random
import time

# Wait 3 seconds so you can switch to the Minesweeper window
time.sleep(3)

# Board coordinates
min_x, min_y = 737, 345
max_x, max_y = 737, 345

clicks = 10  # Number of clicks

for _ in range(clicks):
    x = random.randint(min_x, max_x)
    y = random.randint(min_y, max_y)
    pyautogui.click(x, y)
    # Fastest possible — remove or reduce delay as needed
    # time.sleep(0.01)  # optional tiny delay
