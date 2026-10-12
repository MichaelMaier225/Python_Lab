import pyautogui
import time

# Set the interval between clicks in seconds
interval = 2

print("Auto clicker starting in 3 seconds. Move your mouse to the target location.")
time.sleep(3)

try:
    while True:
        # Perform a left click at the current mouse position
        pyautogui.click(button='left')
        print(f"Clicked at {pyautogui.position()}")
        # Wait for the specified interval before the next click
        time.sleep(interval)
except KeyboardInterrupt:
    # Stop the script by pressing Ctrl+C in the terminal
    print("Auto clicker stopped.")
