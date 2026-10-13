"""Minimal Windows mGBA Libretro frontend, without custom compilation."""
import ctypes as C
from pathlib import Path
import numpy as np

ENV_SET_PIXEL_FORMAT = 10
ENV_GET_CAN_DUPE = 3
ENV_GET_SYSTEM_DIRECTORY = 9
ENV_GET_SAVE_DIRECTORY = 31
ENV_SET_SUPPORT_NO_GAME = 18
DEVICE_JOYPAD = 1
MEMORY_SYSTEM_RAM = 2
ENV_SET_MEMORY_MAPS = 36
EWRAM_START = 0x02000000
EWRAM_SIZE = 0x40000

class GameInfo(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p), ('size', C.c_size_t), ('meta', C.c_char_p)]

class SystemInfo(C.Structure):
    _fields_ = [('library_name', C.c_char_p), ('library_version', C.c_char_p), ('valid_extensions', C.c_char_p), ('need_fullpath', C.c_bool), ('block_extract', C.c_bool)]

class MemoryDescriptor(C.Structure):
    _fields_ = [
        ('flags', C.c_uint64), ('ptr', C.c_void_p),
        ('offset', C.c_size_t), ('start', C.c_size_t),
        ('select', C.c_size_t), ('disconnect', C.c_size_t),
        ('len', C.c_size_t), ('addrspace', C.c_char_p),
    ]

class MemoryMap(C.Structure):
    _fields_ = [('descriptors', C.POINTER(MemoryDescriptor)),
                ('num_descriptors', C.c_uint)]

ENV_CB = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO_CB = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO_CB = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
AUDIO_BATCH_CB = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
INPUT_POLL_CB = C.CFUNCTYPE(None)
INPUT_STATE_CB = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)

# Libretro joypad IDs
BUTTONS = {'b': 0, 'y': 1, 'select': 2, 'start': 3, 'up': 4, 'down': 5,
           'left': 6, 'right': 7, 'a': 8, 'x': 9, 'l': 10, 'r': 11}

class Emulator:
    def __init__(self, core_path, rom_path, system_dir=None):
        core_path, rom_path = Path(core_path).resolve(), Path(rom_path).resolve()
        if not core_path.is_file() or not rom_path.is_file():
            raise FileNotFoundError(f'Missing core or ROM: {core_path}, {rom_path}')
        self.core = C.CDLL(str(core_path))
        self.pressed = set()
        self._memory_regions = []
        self.frame = np.zeros((160, 240, 3), dtype=np.uint8)
        self._rom_path = str(rom_path).encode('utf-8')
        self._system_dir = str(Path(system_dir or rom_path.parent).resolve()).encode('utf-8')
        self._sysdir_ptr = C.c_char_p(self._system_dir)
        self._callbacks = [ENV_CB(self._environment), VIDEO_CB(self._video),
                           AUDIO_CB(lambda l, r: None), AUDIO_BATCH_CB(lambda data, n: n),
                           INPUT_POLL_CB(lambda: None), INPUT_STATE_CB(self._input)]
        c = self.core
        for name, args, ret in [
            ('retro_set_environment', [ENV_CB], None),
            ('retro_set_video_refresh', [VIDEO_CB], None),
            ('retro_set_audio_sample', [AUDIO_CB], None),
            ('retro_set_audio_sample_batch', [AUDIO_BATCH_CB], None),
            ('retro_set_input_poll', [INPUT_POLL_CB], None),
            ('retro_set_input_state', [INPUT_STATE_CB], None),
            ('retro_init', [], None), ('retro_deinit', [], None),
            ('retro_load_game', [C.POINTER(GameInfo)], C.c_bool),
            ('retro_unload_game', [], None), ('retro_run', [], None),
            ('retro_reset', [], None), ('retro_serialize_size', [], C.c_size_t),
            ('retro_serialize', [C.c_void_p, C.c_size_t], C.c_bool),
            ('retro_unserialize', [C.c_void_p, C.c_size_t], C.c_bool),
            ('retro_get_memory_data', [C.c_uint], C.c_void_p),
            ('retro_get_memory_size', [C.c_uint], C.c_size_t),
            ('retro_get_system_info', [C.POINTER(SystemInfo)], None),
        ]:
            f = getattr(c, name)
            f.argtypes, f.restype = args, ret
        c.retro_set_environment(self._callbacks[0])
        c.retro_set_video_refresh(self._callbacks[1])
        c.retro_set_audio_sample(self._callbacks[2])
        c.retro_set_audio_sample_batch(self._callbacks[3])
        c.retro_set_input_poll(self._callbacks[4])
        c.retro_set_input_state(self._callbacks[5])
        c.retro_init()
        info = SystemInfo()
        c.retro_get_system_info(C.byref(info))
        self._rom_data = None
        if info.need_fullpath:
            game = GameInfo(self._rom_path, None, 0, None)
        else:
            self._rom_data = C.create_string_buffer(rom_path.read_bytes())
            game = GameInfo(self._rom_path, C.cast(self._rom_data, C.c_void_p), len(self._rom_data)-1, None)
        if not c.retro_load_game(C.byref(game)):
            c.retro_deinit()
            raise RuntimeError('Libretro core could not load the ROM')
        self._closed = False

    def _environment(self, command, data):
        if command == ENV_SET_MEMORY_MAPS:
            # Core-advertised pointers; no guessed memory offsets or unsafe scanning.
            if not data:
                return False
            maps = C.cast(data, C.POINTER(MemoryMap)).contents
            self._memory_regions = []
            for i in range(min(int(maps.num_descriptors), 256)):
                d = maps.descriptors[i]
                if d.ptr and d.len:
                    self._memory_regions.append((
                        int(d.start), int(d.len), int(d.ptr),
                        int(d.offset), int(d.select), int(d.disconnect)
                    ))
            return True
        if command == ENV_SET_PIXEL_FORMAT:
            # 0 = 0RGB1555, 1 = XRGB8888, 2 = RGB565
            fmt = C.cast(data, C.POINTER(C.c_int))[0]
            if fmt in (0, 1, 2):
                self.pixel_format = fmt
                return True
            return False
        if command in (ENV_GET_SYSTEM_DIRECTORY, ENV_GET_SAVE_DIRECTORY):
            C.cast(data, C.POINTER(C.c_char_p))[0] = self._sysdir_ptr
            return True
        if command == ENV_GET_CAN_DUPE:
            C.cast(data, C.POINTER(C.c_bool))[0] = True
            return True
        if command == ENV_SET_SUPPORT_NO_GAME:
            return True
        return False

    def _video(self, ptr, width, height, pitch):
        if not ptr or width == 0 or height == 0:
            return
        width, height = int(width), int(height)
        fmt = getattr(self, 'pixel_format', 0)
        bpp = 4 if fmt == 1 else 2
        buf = C.string_at(ptr, int(pitch)*height)
        if fmt == 1:
            raw = np.ndarray((height, width), dtype='<u4', buffer=buf, strides=(int(pitch), 4))
            rgb = np.stack(((raw >> 16) & 255, (raw >> 8) & 255, raw & 255), axis=-1).astype(np.uint8)
        else:
            raw = np.ndarray((height, width), dtype='<u2', buffer=buf, strides=(int(pitch), 2))
            if fmt == 2:
                r, g, b = (raw >> 11) & 31, (raw >> 5) & 63, raw & 31
                rgb = np.stack((r*255//31, g*255//63, b*255//31), axis=-1).astype(np.uint8)
            else:
                r, g, b = (raw >> 10) & 31, (raw >> 5) & 31, raw & 31
                rgb = np.stack((r*255//31, g*255//31, b*255//31), axis=-1).astype(np.uint8)
        self.frame = rgb

    def _input(self, port, device, index, button_id):
        return int(port == 0 and device == DEVICE_JOYPAD and button_id in self.pressed)

    def step(self, button=None, frames=24):
        self.pressed = {BUTTONS[button]} if button else set()
        for _ in range(frames):
            self.core.retro_run()
        self.pressed.clear()
        return self.frame.copy()

    def save_state(self):
        size = self.core.retro_serialize_size()
        if not size:
            raise RuntimeError('Core does not support save states')
        buf = C.create_string_buffer(size)
        if not self.core.retro_serialize(buf, size):
            raise RuntimeError('Could not serialize game state')
        return buf.raw

    def load_state(self, state):
        buf = C.create_string_buffer(state, len(state))
        if not self.core.retro_unserialize(buf, len(state)):
            raise RuntimeError('Could not restore game state')
        self.step(frames=1)

    def ram(self):
        size = self.core.retro_get_memory_size(MEMORY_SYSTEM_RAM)
        ptr = self.core.retro_get_memory_data(MEMORY_SYSTEM_RAM)
        return C.string_at(ptr, size) if ptr and size else b''

    def ewram(self):
        """Read GBA EWRAM if the Libretro core advertises a direct memory map.

        Returns None when no safe mapping is exposed by this core.
        """
        for start, length, ptr, offset, select, disconnect in self._memory_regions:
            # Require a direct contiguous mapping covering the entire EWRAM range.
            # Do not dereference uncertain mirrors or bank-switched mappings.
            if disconnect != 0:
                continue
            if start <= EWRAM_START and EWRAM_START + EWRAM_SIZE <= start + length:
                relative = EWRAM_START - start
                if select and (EWRAM_START & select) != (start & select):
                    continue
                return C.string_at(ptr + offset + relative, EWRAM_SIZE)
        return None

    def close(self):
        if not self._closed:
            self.core.retro_unload_game()
            self.core.retro_deinit()
            self._closed = True
