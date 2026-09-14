"""Explicitly remove only the current user's fitroute:// registry key."""

from __future__ import annotations

import os


def unregister_protocol() -> None:
    if os.name != "nt":
        raise RuntimeError("Protocol removal is supported only on Windows.")

    import winreg

    root = winreg.HKEY_CURRENT_USER
    base_path = r"Software\Classes\fitroute"
    for suffix in (r"shell\open\command", r"shell\open", "shell", "DefaultIcon", ""):
        path = base_path + (f"\\{suffix}" if suffix else "")
        try:
            winreg.DeleteKey(root, path)
        except FileNotFoundError:
            continue
    print("fitroute:// was removed for the current user.")


if __name__ == "__main__":
    unregister_protocol()
