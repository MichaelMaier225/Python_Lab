# Pokémon TCG Pocket — Manual Gameplay Recorder (V1)

Records mouse clicks, drag paths, timing, and screenshots of the mirrored Samsung Galaxy game screen in Windows Phone Link. **This version does not replay gameplay, create accounts, or reset game data.**

## Quick start

1. Install Python 3.11 or newer on Windows.
2. Open Phone Link and display the Pokémon TCG Pocket phone screen.
3. Double-click `start.bat` or run `python -m pip install -r requirements.txt` then `python main.py`.
4. If more than one matching window appears, select the correct one.
5. Calibrate by placing the mouse at the top-left game-display pixel and pressing Enter, then repeat for the bottom-right pixel.
6. Focus the mirrored game and press **F5** to record.
7. **F6** pauses/resumes; **F8** saves a checkpoint; **F7** stops and saves.

Each run is saved in `recordings/session_.../`. Recordings are excluded from Git.

## Limitations and safety

- This is an initial implementation, **not yet verified on your particular Phone Link configuration**.
- Calibration uses a fixed game-display offset within the window. Resizing the window invalidates calibration; stop and recalibrate.
- Moving the window is supported when its offsets remain unchanged.
- Screenshots are periodic (every 2 seconds) and around actions; they do not capture every rendered frame.
- Focus loss pauses recording. Press F6 to resume after focusing Phone Link.
- F7 saves a completed session; crashes can leave `events.jsonl` for manual recovery.
- Do not record login, account recovery, or payment screens. Pause before entering sensitive data. Screenshots may include account identifiers.
- Some Windows Phone Link windows may have titles or focus behavior that require adjustments.
- This records Windows mouse interactions, not native Android touch events.
- Recording and future automated gameplay may conflict with the game's terms.

## First test

Record 30 seconds with one click, one swipe, and an F8 checkpoint. Stop with F7. Confirm `actions.json`, `events.jsonl`, and PNG screenshots exist before attempting a full tutorial run.
