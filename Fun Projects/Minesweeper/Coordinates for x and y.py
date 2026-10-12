import pyautogui
import time

print("Move your mouse to the top-left corner of the Minesweeper grid...")
time.sleep(5)
x1, y1 = pyautogui.position()
print(f"Top-left corner: x={x1}, y={y1}")

print("Now move your mouse to the bottom-right corner of the Minesweeper grid...")
time.sleep(5)
x2, y2 = pyautogui.position()
print(f"Bottom-right corner: x={x2}, y={y2}")
