"""Explicitly register fitroute:// for the current Windows user."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def default_launcher_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not available.")
    return Path(local_app_data) / "FitRoute" / "FitRouteLauncher.exe"


def protocol_command(launcher_path: Path) -> str:
    return f'"{launcher_path.resolve()}" "%1"'


def register_protocol(launcher_path: Path) -> None:
    if os.name != "nt":
        raise RuntimeError("Protocol registration is supported only on Windows.")
    if not launcher_path.is_file():
        raise FileNotFoundError(f"Launcher not found: {launcher_path}")

    import winreg

    root_path = r"Software\Classes\fitroute"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, root_path) as key:
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, "URL:FitRoute Protocol")
        winreg.SetValueEx(key, "URL Protocol", 0, winreg.REG_SZ, "")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, root_path + r"\DefaultIcon") as key:
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, str(launcher_path.resolve()))
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, root_path + r"\shell\open\command") as key:
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, protocol_command(launcher_path))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launcher", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()
    launcher_path = (arguments.launcher or default_launcher_path()).resolve()
    if arguments.dry_run:
        print(protocol_command(launcher_path))
        return
    register_protocol(launcher_path)
    print("fitroute:// was registered for the current user.")


if __name__ == "__main__":
    main()
