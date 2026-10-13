
import time
import threading

import pydirectinput
from pynput import mouse, keyboard

running = False
exit_program = False

# Faster starting settings
DELAY = 0.005
KEY_HOLD = 0.01

MIN_DELAY = 0.001
MAX_DELAY = 0.20
SPEED_STEP = 0.005

pydirectinput.PAUSE = 0


def exercise():
    global running

    while not exit_program:
        if running:
            pydirectinput.keyDown("q")
            time.sleep(KEY_HOLD)
            pydirectinput.keyUp("q")
            time.sleep(DELAY)

            if running and not exit_program:
                pydirectinput.keyDown("e")
                time.sleep(KEY_HOLD)
                pydirectinput.keyUp("e")
                time.sleep(DELAY)
        else:
            time.sleep(0.01)


def on_mouse_click(x, y, button, pressed):
    global running

    if not pressed:
        return

    if button == mouse.Button.x1:
        running = not running
        print("Exercising:", "ON" if running else "PAUSED")

    elif button == mouse.Button.x2:
        running = False
        print("Exercising: STOPPED")


def on_key_press(key):
    global running, exit_program, DELAY

    if key == keyboard.Key.f6:
        DELAY = max(MIN_DELAY, DELAY - SPEED_STEP)
        print(f"Faster: {DELAY:.3f}s delay")

    elif key == keyboard.Key.f7:
        DELAY = min(MAX_DELAY, DELAY + SPEED_STEP)
        print(f"Slower: {DELAY:.3f}s delay")

    elif key == keyboard.Key.f8:
        running = False
        exit_program = True
        print("Exiting...")
        return False


print("Escapists Auto Exercise")
print("Mouse 4 = Start/Pause")
print("Mouse 5 = Stop")
print("F6 = Faster")
print("F7 = Slower")
print("F8 = Exit")
print(f"Starting delay: {DELAY}s")

exercise_thread = threading.Thread(
    target=exercise,
    daemon=True
)
exercise_thread.start()

mouse_listener = mouse.Listener(on_click=on_mouse_click)
mouse_listener.start()

with keyboard.Listener(on_press=on_key_press) as listener:
    listener.join()

mouse_listener.stop()
