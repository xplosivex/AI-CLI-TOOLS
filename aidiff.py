#!/usr/bin/env python3
"""
aidiff — Compare files or file states.

Usage:
    aidiff <file1> <file2>          Compare two files
    aidiff <file> --backup           Compare current file vs last backup
    aidiff <file> --backup --tag X   Compare current vs specific tagged backup

Output format (unified diff with line numbers):
    --- backup: main.py.20250209_143000
    +++ current: main.py
    @@ -10,3 +10,4 @@
      10 | unchanged line
    - 11 | old line
    + 11 | new line
    + 12 | added line
"""

import argparse
import difflib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aiconfig import cfg
from aiencoding import read_lines_with_encoding


def read_lines(path):
    if not os.path.isfile(path):
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        lines, _ = read_lines_with_encoding(path)
        return lines
    except Exception as e:
        print(f"ERROR: cannot read file: {e}", file=sys.stderr)
        sys.exit(1)


def find_backup(filepath, tag=None):
    """Find backup file. Returns path or exits with error."""
    try:
        from aibackup import list_backups
    except ImportError:
        print("ERROR: aibackup.py not found (needed for --backup)", file=sys.stderr)
        sys.exit(1)

    backups = list_backups(filepath)
    if not backups:
        print(f"ERROR: no backups found for {filepath}", file=sys.stderr)
        sys.exit(1)

    if tag:
        safe_tag = "".join(c if c.isalnum() or c in "-_" else "_" for c in tag)
        for full, name in reversed(backups):
            if safe_tag in name:
                return full
        print(f"ERROR: no backup with tag '{tag}' found", file=sys.stderr)
        sys.exit(1)

    return backups[-1][0]  # most recent


def do_diff(path_a, path_b, label_a=None, label_b=None):
    """Perform and print diff between two files."""
    lines_a = read_lines(path_a)
    lines_b = read_lines(path_b)

    if label_a is None:
        label_a = path_a
    if label_b is None:
        label_b = path_b

    diff = list(difflib.unified_diff(
        lines_a, lines_b,
        fromfile=label_a,
        tofile=label_b,
        lineterm=""
    ))

    if not diff:
        print("No differences found.")
        return

    for line in diff:
        # strip trailing newlines for clean output
        print(line.rstrip("\n\r"))


def main():
    parser = argparse.ArgumentParser(
        prog="aidiff",
        description="Compare files or file states.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  aidiff old.py new.py           # compare two files\n"
               "  aidiff main.py --backup        # compare vs last backup\n"
               "  aidiff main.py --backup --tag before-refactor",
    )
    parser.add_argument("file1", help="First file (or current file if --backup)")
    parser.add_argument("file2", nargs="?", default=None, help="Second file")
    parser.add_argument("--backup", action="store_true",
                        help="Compare file1 against its last backup")
    parser.add_argument("--tag", metavar="NAME",
                        help="Compare against specific tagged backup")

    args = parser.parse_args()

    if args.backup or args.tag:
        backup_path = find_backup(args.file1, args.tag)
        do_diff(
            backup_path, args.file1,
            label_a=f"backup: {os.path.basename(backup_path)}",
            label_b=f"current: {args.file1}"
        )
    elif args.file2:
        do_diff(args.file1, args.file2)
    else:
        print("ERROR: provide two files or use --backup", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()