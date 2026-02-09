#!/usr/bin/env python3
"""
install.py — Make AI tools available as commands system-wide.

Usage:
    python install.py              Install (auto-detects platform)
    python install.py --uninstall  Remove installed commands
    python install.py --check      Verify installation

Linux/macOS:
    - Creates wrapper scripts in ~/.local/bin/ (or custom --bin-dir)
    - Adds ~/.local/bin to PATH in shell rc file if needed

Windows:
    - Creates .bat wrappers in %USERPROFILE%\\.aitools\\bin\\
    - Adds that directory to user PATH via registry
    - Also creates PowerShell function file for PS users

No admin/sudo required on either platform.
"""

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys

TOOLS = ["aiview", "aiedit", "aibackup", "aidiff", "aifind"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

_python_override = None


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def find_python():
    """Return the best python3 command available."""
    # user-specified path takes priority
    if _python_override:
        return _python_override

    # prefer the python running this script
    current = sys.executable
    if current:
        return current

    for name in ("python3", "python"):
        path = shutil.which(name)
        if path:
            return path

    print_err("Could not find python. Use --python to specify the path.")
    print_err("  Example: python install.py --python C:\\Python312\\python.exe")
    sys.exit(1)


def is_windows():
    return platform.system() == "Windows"


def print_ok(msg):
    print(f"  ✓ {msg}")


def print_warn(msg):
    print(f"  ⚠ {msg}")


def print_err(msg):
    print(f"  ✗ {msg}")


# ---------------------------------------------------------------------------
# Linux / macOS
# ---------------------------------------------------------------------------

def get_linux_bin_dir(custom=None):
    if custom:
        return os.path.expanduser(custom)
    return os.path.expanduser("~/.local/bin")


def install_linux(bin_dir):
    os.makedirs(bin_dir, exist_ok=True)
    python = find_python()

    for tool in TOOLS:
        tool_src = os.path.join(SCRIPT_DIR, f"{tool}.py")
        if not os.path.isfile(tool_src):
            print_err(f"{tool}.py not found in {SCRIPT_DIR}")
            continue

        wrapper_path = os.path.join(bin_dir, tool)
        wrapper_content = f"""#!/bin/sh
exec "{python}" "{tool_src}" "$@"
"""
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)

        # make executable
        st = os.stat(wrapper_path)
        os.chmod(wrapper_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        print_ok(f"Created {wrapper_path}")

    # check if bin_dir is in PATH
    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    if bin_dir not in path_dirs and os.path.abspath(bin_dir) not in [os.path.abspath(p) for p in path_dirs]:
        _add_to_path_linux(bin_dir)
    else:
        print_ok(f"{bin_dir} already in PATH")


def _add_to_path_linux(bin_dir):
    """Add bin_dir to PATH via shell rc file."""
    shell = os.environ.get("SHELL", "")
    home = os.path.expanduser("~")

    # determine rc file
    if "zsh" in shell:
        rc_file = os.path.join(home, ".zshrc")
    elif "fish" in shell:
        rc_file = os.path.join(home, ".config", "fish", "config.fish")
    else:
        rc_file = os.path.join(home, ".bashrc")

    export_line_bash = f'\nexport PATH="{bin_dir}:$PATH"  # aitools\n'
    export_line_fish = f'\nset -gx PATH "{bin_dir}" $PATH  # aitools\n'

    if "fish" in shell:
        export_line = export_line_fish
    else:
        export_line = export_line_bash

    # check if already present
    marker = "# aitools"
    if os.path.isfile(rc_file):
        with open(rc_file, "r") as f:
            if marker in f.read():
                print_ok(f"PATH entry already in {rc_file}")
                return

    with open(rc_file, "a") as f:
        f.write(export_line)

    print_ok(f"Added {bin_dir} to PATH in {rc_file}")
    print_warn(f"Run: source {rc_file}  (or open a new terminal)")


def uninstall_linux(bin_dir):
    for tool in TOOLS:
        wrapper = os.path.join(bin_dir, tool)
        if os.path.isfile(wrapper):
            os.remove(wrapper)
            print_ok(f"Removed {wrapper}")
        else:
            print_warn(f"{wrapper} not found, skipping")

    print_warn("PATH entry in shell rc file left in place — remove manually if desired")


# ---------------------------------------------------------------------------
# Windows
# ---------------------------------------------------------------------------

def get_windows_bin_dir(custom=None):
    if custom:
        return os.path.expanduser(custom)
    return os.path.join(os.path.expanduser("~"), ".aitools", "bin")


def install_windows(bin_dir):
    os.makedirs(bin_dir, exist_ok=True)
    python = find_python()

    for tool in TOOLS:
        tool_src = os.path.join(SCRIPT_DIR, f"{tool}.py")
        if not os.path.isfile(tool_src):
            print_err(f"{tool}.py not found in {SCRIPT_DIR}")
            continue

        # .bat wrapper for cmd.exe
        bat_path = os.path.join(bin_dir, f"{tool}.bat")
        bat_content = f'@echo off\r\n"{python}" "{tool_src}" %*\r\n'
        with open(bat_path, "w") as f:
            f.write(bat_content)
        print_ok(f"Created {bat_path}")

    # create PowerShell profile helper
    ps_profile_path = os.path.join(bin_dir, "aitools_ps_profile.ps1")
    ps_lines = []
    for tool in TOOLS:
        tool_src = os.path.join(SCRIPT_DIR, f"{tool}.py")
        ps_lines.append(f'function {tool} {{ & "{python}" "{tool_src}" @args }}')
    ps_content = "# AI Tools — source this in your PowerShell $PROFILE\n"
    ps_content += "# Add this line to your $PROFILE:\n"
    ps_content += f'# . "{ps_profile_path}"\n\n'
    ps_content += "\n".join(ps_lines) + "\n"
    with open(ps_profile_path, "w") as f:
        f.write(ps_content)
    print_ok(f"Created PowerShell profile: {ps_profile_path}")

    # add to user PATH via registry
    _add_to_path_windows(bin_dir)


def _add_to_path_windows(bin_dir):
    """Add bin_dir to user PATH via Windows registry."""
    try:
        import winreg
    except ImportError:
        print_warn(f"Cannot modify registry (not on Windows?). Add manually to PATH: {bin_dir}")
        return

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE
        )
    except OSError:
        print_warn(f"Cannot open registry. Add manually to PATH: {bin_dir}")
        return

    try:
        current_path, _ = winreg.QueryValueEx(key, "Path")
    except FileNotFoundError:
        current_path = ""

    # check if already there
    path_dirs = [p.strip().rstrip("\\") for p in current_path.split(";") if p.strip()]
    bin_dir_clean = bin_dir.rstrip("\\")

    if bin_dir_clean.lower() in [p.lower() for p in path_dirs]:
        print_ok(f"{bin_dir} already in user PATH")
        winreg.CloseKey(key)
        return

    new_path = current_path.rstrip(";") + ";" + bin_dir
    winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
    winreg.CloseKey(key)

    # broadcast environment change
    try:
        import ctypes
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x1A
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", 0x0002, 5000, None
        )
    except Exception:
        pass

    print_ok(f"Added {bin_dir} to user PATH (registry)")
    print_warn("Open a NEW terminal for PATH changes to take effect")


def uninstall_windows(bin_dir):
    for tool in TOOLS:
        bat = os.path.join(bin_dir, f"{tool}.bat")
        if os.path.isfile(bat):
            os.remove(bat)
            print_ok(f"Removed {bat}")

    ps_file = os.path.join(bin_dir, "aitools_ps_profile.ps1")
    if os.path.isfile(ps_file):
        os.remove(ps_file)
        print_ok(f"Removed {ps_file}")

    print_warn(f"PATH entry left in place — remove {bin_dir} from user PATH manually if desired")


# ---------------------------------------------------------------------------
# Check
# ---------------------------------------------------------------------------

def check_install():
    print("Checking AI tools installation:\n")
    all_good = True

    for tool in TOOLS:
        path = shutil.which(tool)
        if path:
            print_ok(f"{tool} → {path}")
        else:
            print_err(f"{tool} not found in PATH")
            all_good = False

    print()
    if all_good:
        print("All tools installed and available.")
    else:
        print("Some tools missing. Run: python install.py")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="install",
        description="Install AI file tools as system commands.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Defaults:\n"
               "  Linux/macOS: wrappers in ~/.local/bin/\n"
               "  Windows:     .bat files in %%USERPROFILE%%\\.aitools\\bin\\\n\n"
               "If python is not in PATH, specify it:\n"
               "  python install.py --python C:\\Python312\\python.exe\n\n"
               "No admin/sudo required.",
    )
    parser.add_argument("--uninstall", action="store_true", help="Remove installed commands")
    parser.add_argument("--check", action="store_true", help="Verify installation")
    parser.add_argument("--bin-dir", metavar="DIR",
                        help="Custom directory for command wrappers")
    parser.add_argument("--python", metavar="PATH",
                        help="Path to python executable (e.g. C:\\Python312\\python.exe)")

    args = parser.parse_args()

    # if user provided a python path, override the auto-detection
    if args.python:
        global _python_override
        _python_override = args.python

    if args.check:
        check_install()
        return

    if is_windows():
        bin_dir = get_windows_bin_dir(args.bin_dir)
        if args.uninstall:
            print(f"Uninstalling AI tools from {bin_dir}...\n")
            uninstall_windows(bin_dir)
        else:
            print(f"Installing AI tools to {bin_dir}...\n")
            print(f"Tool source: {SCRIPT_DIR}\n")
            install_windows(bin_dir)
    else:
        bin_dir = get_linux_bin_dir(args.bin_dir)
        if args.uninstall:
            print(f"Uninstalling AI tools from {bin_dir}...\n")
            uninstall_linux(bin_dir)
        else:
            print(f"Installing AI tools to {bin_dir}...\n")
            print(f"Tool source: {SCRIPT_DIR}\n")
            install_linux(bin_dir)

    print()
    if not args.uninstall:
        print("Done! Verify with: python install.py --check")
        if is_windows():
            print("\nFor PowerShell, add this to your $PROFILE:")
            ps_path = os.path.join(bin_dir, "aitools_ps_profile.ps1")
            print(f'  . "{ps_path}"')


if __name__ == "__main__":
    main()