from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from dataclasses import dataclass
from threading import Event
from typing import Callable, Optional


INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_RETURN = 0x0D
VK_TAB = 0x09

ULONG_PTR = wintypes.WPARAM


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


user32 = ctypes.WinDLL("user32", use_last_error=True)

SendInput = user32.SendInput
SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
SendInput.restype = wintypes.UINT


@dataclass(frozen=True)
class TypingConfig:
    chars_per_second: float = 20.0
    start_delay: int = 3


class KeyboardInputError(RuntimeError):
    pass


def _make_key_input(vk: int = 0, scan: int = 0, flags: int = 0) -> INPUT:
    obj = INPUT()
    obj.type = INPUT_KEYBOARD
    obj.union.ki = KEYBDINPUT(
        wVk=vk,
        wScan=scan,
        dwFlags=flags,
        time=0,
        dwExtraInfo=0,
    )
    return obj


def _send_input(input_obj: INPUT) -> None:
    sent = SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(INPUT))
    if sent != 1:
        error_code = ctypes.get_last_error()
        raise KeyboardInputError(f"SendInput failed, Windows error code: {error_code}")


def press_vk(vk_code: int) -> None:
    down = _make_key_input(vk=vk_code, scan=0, flags=0)
    up = _make_key_input(vk=vk_code, scan=0, flags=KEYEVENTF_KEYUP)
    _send_input(down)
    _send_input(up)


def type_unicode_char(char: str) -> None:
    code_point = ord(char)

    if code_point <= 0xFFFF:
        down = _make_key_input(vk=0, scan=code_point, flags=KEYEVENTF_UNICODE)
        up = _make_key_input(vk=0, scan=code_point, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
        _send_input(down)
        _send_input(up)
        return

    # Unicode supplementary-plane characters, such as some emoji.
    utf16_units = char.encode("utf-16-le")
    for i in range(0, len(utf16_units), 2):
        unit = int.from_bytes(utf16_units[i:i + 2], "little")
        down = _make_key_input(vk=0, scan=unit, flags=KEYEVENTF_UNICODE)
        up = _make_key_input(vk=0, scan=unit, flags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP)
        _send_input(down)
        _send_input(up)


def type_text(
    text: str,
    config: TypingConfig,
    stop_event: Optional[Event] = None,
    pause_event: Optional[Event] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    status_callback: Optional[Callable[[str], None]] = None,
) -> None:
    if not text:
        raise ValueError("输入文本为空。")
    if config.chars_per_second <= 0:
        raise ValueError("输入速度必须大于 0。")

    stop_event = stop_event or Event()
    pause_event = pause_event or Event()
    delay = 1.0 / config.chars_per_second
    total = len(text)

    for remaining in range(config.start_delay, 0, -1):
        if stop_event.is_set():
            if status_callback:
                status_callback("已停止。")
            return
        if status_callback:
            status_callback(f"{remaining} 秒后开始，请切换到目标输入窗口。")
        time.sleep(1)

    if status_callback:
        status_callback("正在录入……")

    for index, char in enumerate(text, start=1):
        if stop_event.is_set():
            if status_callback:
                status_callback("已停止。")
            return

        while pause_event.is_set():
            if stop_event.is_set():
                if status_callback:
                    status_callback("已停止。")
                return
            time.sleep(0.05)

        if char == "\n":
            press_vk(VK_RETURN)
        elif char == "\t":
            press_vk(VK_TAB)
        else:
            type_unicode_char(char)

        if progress_callback:
            progress_callback(index, total)

        time.sleep(delay)

    if status_callback:
        status_callback("录入完成。")
