from __future__ import annotations

import ctypes
import os
import subprocess
import sys


def is_windows() -> bool:
    return os.name == "nt"


def is_admin() -> bool:
    if not is_windows():
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def relaunch_as_admin() -> bool:
    if not is_windows():
        return False

    if getattr(sys, "frozen", False):
        executable = sys.executable
        arguments = subprocess.list2cmdline(sys.argv[1:])
    else:
        executable = sys.executable
        arguments = subprocess.list2cmdline([os.path.abspath(sys.argv[0]), *sys.argv[1:]])

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        arguments,
        os.getcwd(),
        1,
    )
    return result > 32


def show_native_error(message: str) -> None:
    if is_windows():
        ctypes.windll.user32.MessageBoxW(None, message, "RoutePilot", 0x10)

