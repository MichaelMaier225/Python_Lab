# FireRed RL — Python + prebuilt mGBA Libretro + PPO

**Experimental baseline, not a verified end-to-end Windows build.** No custom mGBA compilation.

## Files you provide

- A legally obtained Pokémon FireRed `.gba` ROM.
- The **Windows x64** `mgba_libretro.dll` core from a trusted Libretro/RetroArch distribution. Match Python's 64-bit architecture.
- Ideally, an in-game save (`.srm` or `.sav`) from after receiving your starter. The exact save filename and location used by the core can vary. The `prepare.py` script captures the currently loaded game state, not an interactive save editor.

## Install

From PowerShell, in this directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Verify before training

```powershell
.\.venv\Scripts\python.exe test_core.py --core "C:\path\mgba_libretro.dll" --rom "C:\path\FireRed.gba"
```

Inspect `smoke_test.png`. If this test fails, **do not start training**.

## Create a reset point

```powershell
.\.venv\Scripts\python.exe prepare.py --core "C:\path\mgba_libretro.dll" --rom "C:\path\FireRed.gba" --output start.state
```

**Important:** This captures the current state after 240 boot frames, which may be the title screen. For useful exploration, create a save with a starter Pokémon and load it in the core first, or modify `prepare.py` to send inputs until reaching the intended point. The default boot state is only a technical smoke-test baseline.

## Train

```powershell
.\.venv\Scripts\python.exe train.py --core "C:\path\mgba_libretro.dll" --rom "C:\path\FireRed.gba" --state start.state --workers 1 --steps 200000
```

Once one worker succeeds, try `--workers 4` or `--workers 8`. The emulator is run headless, with each worker owning its own core instance in a separate process.

## Important limitations

- Reward is **screen novelty only**. It can learn exploration but may get stuck exploiting animations, dialogs, or menus. This is not yet the sophisticated reward function used by Peter Whidden.
- FireRed-specific RAM addresses for player position, map ID, Pokémon levels, badges, etc. are **not hardcoded**, because they differ by ROM revision and must be verified. Add them before expecting game progression.
- Some Libretro cores depend on system files, options, or environment callbacks beyond the minimal frontend implemented here. The smoke test is mandatory.
- `retro_get_memory_data` provides only the memory regions the core exposes; it is not a guaranteed view of all GBA memory.
- The core may save SRAM on shutdown or use a specific file naming scheme. Verify the in-game save loads before generating your training state.
- No specific training speed or success rate is guaranteed; measure actual throughput on your machine.
