#!/usr/bin/env python3
"""
aibackup — Backup and restore files.

Usage:
    aibackup save <file>                          Snapshot current state
    aibackup save <file> --tag "before-refactor"  Named snapshot
    aibackup list <file>                          List all snapshots
    aibackup restore <file>                       Restore most recent
    aibackup restore <file> --tag "name"          Restore named snapshot
    aibackup diff <file>                          Diff current vs last backup

Also used internally by aiedit for auto-backups.
"""

import argparse
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aiconfig import cfg
from aiencoding import read_lines_with_encoding


def get_backup_dir(filepath):
    """Get backup directory for a given file. Creates it if needed."""
    backup_dirname = cfg("backup.dir", ".aibackup")
    filedir = os.path.dirname(os.path.abspath(filepath))
    backup_dir = os.path.join(filedir, backup_dirname)
    return backup_dir


def ensure_backup_dir(filepath):
    d = get_backup_dir(filepath)
    os.makedirs(d, exist_ok=True)
    return d


def backup_filename(filepath, tag=None):
    """Generate backup filename: originalname.YYYYMMDD_HHMMSS[.tag]"""
    base = os.path.basename(filepath)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if tag:
        # sanitize tag
        safe_tag = "".join(c if c.isalnum() or c in "-_" else "_" for c in tag)
        return f"{base}.{timestamp}.{safe_tag}"
    return f"{base}.{timestamp}"


def list_backups(filepath):
    """Return sorted list of (full_path, basename) for backups of this file."""
    backup_dir = get_backup_dir(filepath)
    if not os.path.isdir(backup_dir):
        return []

    base = os.path.basename(filepath)
    backups = []
    for f in os.listdir(backup_dir):
        # backups start with "originalname."
        if f.startswith(base + "."):
            full = os.path.join(backup_dir, f)
            backups.append((full, f))

    backups.sort(key=lambda x: x[1])
    return backups


def prune_backups(filepath):
    """Remove oldest backups if we exceed max_backups."""
    max_b = cfg("backup.max_backups", 20)
    backups = list_backups(filepath)
    while len(backups) > max_b:
        oldest = backups.pop(0)
        try:
            os.remove(oldest[0])
        except Exception:
            pass


def save_backup(filepath, tag=None):
    """Create a backup of filepath. Returns backup path."""
    if not os.path.isfile(filepath):
        print(f"ERROR: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    backup_dir = ensure_backup_dir(filepath)
    bname = backup_filename(filepath, tag)
    dest = os.path.join(backup_dir, bname)

    shutil.copy2(filepath, dest)
    prune_backups(filepath)
    return dest


def cmd_save(args):
    dest = save_backup(args.file, args.tag)
    rel = os.path.relpath(dest)
    print(f"OK: saved backup {rel}")


def cmd_list(args):
    backups = list_backups(args.file)
    if not backups:
        print(f"No backups found for {args.file}")
        return

    base = os.path.basename(args.file)
    print(f"Backups for {args.file} ({len(backups)}):\n")
    for i, (full, name) in enumerate(backups, 1):
        size = os.path.getsize(full)
        if size < 1024:
            size_str = f"{size}B"
        else:
            size_str = f"{size / 1024:.1f}KB"

        # extract timestamp and tag from name
        suffix = name[len(base) + 1:]  # after "filename."
        print(f"  {i:>3}. {suffix}  ({size_str})")


def cmd_restore(args):
    backups = list_backups(args.file)
    if not backups:
        print(f"ERROR: no backups found for {args.file}", file=sys.stderr)
        sys.exit(1)

    target = None
    if args.tag:
        safe_tag = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.tag)
        for full, name in reversed(backups):
            if safe_tag in name:
                target = full
                break
        if not target:
            print(f"ERROR: no backup with tag '{args.tag}' found", file=sys.stderr)
            sys.exit(1)
    else:
        target = backups[-1][0]  # most recent

    # backup current state before restoring (safety net)
    if os.path.isfile(args.file):
        save_backup(args.file, tag="pre-restore")

    shutil.copy2(target, args.file)
    rel = os.path.relpath(target)
    print(f"OK: restored {args.file} from {rel}")


def cmd_diff(args):
    backups = list_backups(args.file)
    if not backups:
        print(f"ERROR: no backups found for {args.file}", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(args.file):
        print(f"ERROR: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    import difflib

    backup_path = backups[-1][0]

    old_lines, _ = read_lines_with_encoding(backup_path)
    new_lines, _ = read_lines_with_encoding(args.file)

    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"backup: {os.path.basename(backup_path)}",
        tofile=f"current: {args.file}",
        lineterm=""
    )

    output = list(diff)
    if not output:
        print("No differences (file matches last backup)")
    else:
        for line in output:
            print(line)


def main():
    parser = argparse.ArgumentParser(
        prog="aibackup",
        description="Backup and restore files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  aibackup save main.py\n"
               "  aibackup save main.py --tag before-refactor\n"
               "  aibackup list main.py\n"
               "  aibackup restore main.py\n"
               "  aibackup restore main.py --tag before-refactor\n"
               "  aibackup diff main.py",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # save
    p_save = sub.add_parser("save", help="Create a backup snapshot")
    p_save.add_argument("file", help="File to backup")
    p_save.add_argument("--tag", metavar="NAME", help="Named tag for this snapshot")

    # list
    p_list = sub.add_parser("list", help="List all backups for a file")
    p_list.add_argument("file", help="File to list backups for")

    # restore
    p_restore = sub.add_parser("restore", help="Restore from backup")
    p_restore.add_argument("file", help="File to restore")
    p_restore.add_argument("--tag", metavar="NAME", help="Restore specific tagged backup")

    # diff
    p_diff = sub.add_parser("diff", help="Diff current file vs last backup")
    p_diff.add_argument("file", help="File to diff")

    args = parser.parse_args()

    if args.command == "save":
        cmd_save(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "restore":
        cmd_restore(args)
    elif args.command == "diff":
        cmd_diff(args)


if __name__ == "__main__":
    main()