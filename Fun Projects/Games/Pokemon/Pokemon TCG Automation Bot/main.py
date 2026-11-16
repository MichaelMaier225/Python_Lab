"""Record manual mouse interactions inside a calibrated Samsung Phone Link game area."""
from __future__ import annotations

import json
import queue
import threading
import time
from datetime import datetime
from pathlib import Path

import pygetwindow as gw
from PIL import ImageGrab
from pynput import keyboard, mouse

ROOT = Path(__file__).resolve().parent
RECORDINGS = ROOT / "recordings"
SCREENSHOT_INTERVAL = 2.0
WINDOW_KEYWORDS = ("phone screen", "phone link", "link to windows")


def find_window():
    matches = [w for w in gw.getAllWindows() if w.title and any(
        term in w.title.lower() for term in WINDOW_KEYWORDS)]
    if not matches:
        raise RuntimeError("No Phone Link window found. Open the mirrored phone screen first.")
    for i, window in enumerate(matches, 1):
        print(f"{i}. {window.title} ({window.left},{window.top}, {window.width}x{window.height})")
    if len(matches) == 1:
        return matches[0]
    return matches[int(input("Choose window number: ")) - 1]


def calibrate(window):
    print("Calibrate the GAME DISPLAY (not the title bar).")
    print("Move your mouse to the TOP-LEFT game pixel, then press Enter.")
    input()
    p1 = mouse.Controller().position
    print("Move your mouse to the BOTTOM-RIGHT game pixel, then press Enter.")
    input()
    p2 = mouse.Controller().position
    left, right = sorted((int(p1[0]), int(p2[0])))
    top, bottom = sorted((int(p1[1]), int(p2[1])))
    if right - left < 100 or bottom - top < 100:
        raise ValueError("Game area is too small. Recalibrate.")
    # Keep offsets from window origin, allowing the window to move.
    return (left - window.left, top - window.top, right - window.left, bottom - window.top)


class Recorder:
    def __init__(self, window, offsets):
        self.window = window
        self.offsets = offsets
        self.state = "READY"
        self.started = None
        self.session = None
        self.journal = None
        self.events = []
        self.screenshots = 0
        self.checkpoints = []
        self.pressed = None
        self.lock = threading.RLock()
        self.shots = queue.Queue(maxsize=100)
        self.writer = threading.Thread(target=self.write_screenshots, daemon=True)
        self.writer.start()
        self.next_periodic = 0.0

    def bounds(self):
        l, t, r, b = self.offsets
        return (self.window.left + l, self.window.top + t,
                self.window.left + r, self.window.top + b)

    def active(self):
        try:
            return gw.getActiveWindow()._hWnd == self.window._hWnd
        except Exception:
            return False

    def elapsed(self):
        return round(time.monotonic() - self.started, 4) if self.started else 0.0

    def record(self, kind, **details):
        with self.lock:
            if self.journal is None:
                return
            item = {"t": self.elapsed(), "type": kind, **details}
            self.events.append(item)
            self.journal.write(json.dumps(item) + "\n")
            self.journal.flush()

    def point(self, x, y):
        l, t, r, b = self.bounds()
        if not (l <= x <= r and t <= y <= b):
            return None
        return {"x": int(x), "y": int(y),
                "relative_x": round((x - l) / (r - l), 6),
                "relative_y": round((y - t) / (b - t), 6)}

    def screenshot(self, reason):
        if self.state != "RECORDING" or not self.active():
            return
        timestamp = self.elapsed()
        filename = f"{timestamp:010.3f}_{reason}_{self.screenshots:05d}.png"
        try:
            image = ImageGrab.grab(bbox=self.bounds())
            self.shots.put_nowait((image, filename))
            self.screenshots += 1
            self.record("screenshot", filename=filename, reason=reason)
        except (OSError, queue.Full) as exc:
            self.record("screenshot_error", error=str(exc))

    def write_screenshots(self):
        while True:
            job = self.shots.get()
            try:
                if job is None:
                    return
                image, filename = job
                image.save(self.session / "screenshots" / filename)
            except Exception as exc:
                print("Screenshot save failed:", exc)
            finally:
                self.shots.task_done()

    def start(self):
        if self.state != "READY":
            return
        if not self.active():
            print("Focus the Phone Link game window before starting.")
            return
        RECORDINGS.mkdir(parents=True, exist_ok=True)
        self.session = RECORDINGS / datetime.now().strftime("session_%Y%m%d_%H%M%S_%f")
        (self.session / "screenshots").mkdir(parents=True)
        self.journal = (self.session / "events.jsonl").open("a", encoding="utf-8", buffering=1)
        self.started = time.monotonic()
        self.state = "RECORDING"
        self.record("start", window_title=self.window.title, offsets=self.offsets)
        self.screenshot("start")
        self.next_periodic = time.monotonic() + SCREENSHOT_INTERVAL
        print("RECORDING — F6 pause, F7 stop, F8 checkpoint")

    def pause(self, reason="manual"):
        if self.state == "RECORDING":
            self.record("pause", reason=reason)
            self.state = "PAUSED"
            self.pressed = None
            print("PAUSED:", reason)

    def resume(self):
        if self.state == "PAUSED":
            if not self.active():
                print("Focus Phone Link before resuming.")
                return
            self.state = "RECORDING"
            self.record("resume")
            self.screenshot("resume")
            print("RECORDING")

    def stop(self):
        if self.state not in ("RECORDING", "PAUSED"):
            return
        if self.state == "RECORDING":
            self.screenshot("stop")
        self.record("stop")
        self.state = "SAVING"
        self.shots.join()
        self.journal.close()
        self.journal = None
        (self.session / "actions.json").write_text(
            json.dumps(self.events, indent=2), encoding="utf-8")
        (self.session / "checkpoints.json").write_text(
            json.dumps(self.checkpoints, indent=2), encoding="utf-8")
        (self.session / "session_info.json").write_text(
            json.dumps({"window": self.window.title, "offsets": self.offsets,
                        "duration_seconds": self.elapsed(),
                        "events": len(self.events),
                        "screenshots": self.screenshots}, indent=2), encoding="utf-8")
        self.state = "COMPLETE"
        print(f"COMPLETE — {len(self.events)} events, {self.screenshots} screenshots")
        print("Saved:", self.session)

    def on_click(self, x, y, button, pressed):
        with self.lock:
            if self.state != "RECORDING":
                return
            if not self.active():
                self.pause("window lost focus")
                return
            p = self.point(x, y)
            if pressed and p:
                self.screenshot("before_input")
                self.pressed = {"button": str(button), "start": self.elapsed(),
                                "point": p, "path": [{"t": self.elapsed(), **p}]}
            elif not pressed and self.pressed:
                action = self.pressed
                self.pressed = None
                action["path"].append({"t": self.elapsed(), **(p or action["point"])})
                duration = self.elapsed() - action["start"]
                self.record("swipe" if len(action["path"]) > 2 else "click",
                            button=action["button"], duration=round(duration, 4),
                            start=action["point"], end=p, path=action["path"])
                self.screenshot("after_input")

    def on_move(self, x, y):
        with self.lock:
            if self.state == "RECORDING" and self.pressed:
                p = self.point(x, y)
                if p:
                    path = self.pressed["path"]
                    now = self.elapsed()
                    if now - path[-1]["t"] >= 0.03:
                        path.append({"t": now, **p})

    def on_key(self, key):
        if key == keyboard.Key.f5:
            self.start()
        elif key == keyboard.Key.f6:
            self.pause() if self.state == "RECORDING" else self.resume()
        elif key == keyboard.Key.f7:
            self.stop()
            return False
        elif key == keyboard.Key.f8 and self.state == "RECORDING":
            self.screenshot("checkpoint")
            self.checkpoints.append({"t": self.elapsed(), "name": "Checkpoint"})

    def run(self):
        print("READY — F5 start | F6 pause/resume | F7 save/exit | F8 checkpoint")
        with mouse.Listener(on_click=self.on_click, on_move=self.on_move) as ml:
            with keyboard.Listener(on_press=self.on_key) as kl:
                while kl.running and self.state != "COMPLETE":
                    time.sleep(0.1)
                    if self.state == "RECORDING":
                        if not self.active():
                            self.pause("window lost focus")
                        elif time.monotonic() >= self.next_periodic:
                            self.screenshot("periodic")
                            self.next_periodic = time.monotonic() + SCREENSHOT_INTERVAL
            ml.stop()


if __name__ == "__main__":
    try:
        window = find_window()
        offsets = calibrate(window)
        Recorder(window, offsets).run()
    except (KeyboardInterrupt, Exception) as exc:
        print("Recorder exited:", exc)
        raise
