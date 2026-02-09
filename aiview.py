#!/usr/bin/env python3
"""
aiview — View file contents with line numbers.

Usage:
    aiview <file>                       Show entire file (line-numbered)
    aiview <file> -l 50                 Show line 50 only
    aiview <file> -r 10 25              Show lines 10-25
    aiview <file> --head 20             First 20 lines
    aiview <file> --tail 20             Last 20 lines
    aiview <file> --grep "pattern"      Show matching lines with numbers
    aiview <file> --summary             File info: lines, size, encoding

Output format:
      10 | def main():
      11 |     parser = argparse.ArgumentParser()
"""

import argparse
import os
import sys

# allow running from any location
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aiconfig import cfg
from aiencoding import read_lines_with_encoding


def read_file(path):
    if not os.path.isfile(path):
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        lines, _ = read_lines_with_encoding(path)
        return lines
    except Exception as e:
        print(f"ERROR: cannot read file: {e}", file=sys.stderr)
        sys.exit(1)


def format_lines(lines, start_num, width=None):
    """Format lines with right-aligned line numbers."""
    if width is None:
        width = cfg("view.number_width", 5)
    for i, line in enumerate(lines):
        num = start_num + i
        text = line.rstrip("\n\r")
        print(f"{num:>{width}} | {text}")


def cmd_view_all(path, lines):
    max_lines = cfg("view.max_lines", 500)
    total = len(lines)
    if total > max_lines:
        print(f"WARNING: file has {total} lines, showing first {max_lines} (use -r for range)", file=sys.stderr)
        lines = lines[:max_lines]
    format_lines(lines, 1)
    if total > max_lines:
        print(f"\n... truncated ({total - max_lines} more lines)", file=sys.stderr)


def cmd_view_line(path, lines, line_num):
    if line_num < 1 or line_num > len(lines):
        print(f"ERROR: line {line_num} out of range (file has {len(lines)} lines)", file=sys.stderr)
        sys.exit(1)
    format_lines([lines[line_num - 1]], line_num)


def cmd_view_range(path, lines, start, end):
    total = len(lines)
    if start < 1:
        start = 1
    if end > total:
        end = total
    if start > total:
        print(f"ERROR: start line {start} out of range (file has {total} lines)", file=sys.stderr)
        sys.exit(1)
    if start > end:
        print(f"ERROR: start ({start}) > end ({end})", file=sys.stderr)
        sys.exit(1)
    format_lines(lines[start - 1:end], start)


def cmd_head(path, lines, count):
    count = min(count, len(lines))
    format_lines(lines[:count], 1)


def cmd_tail(path, lines, count):
    total = len(lines)
    count = min(count, total)
    start = total - count
    format_lines(lines[start:], start + 1)


def cmd_grep(path, lines, pattern):
    import re
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        print(f"ERROR: invalid pattern: {e}", file=sys.stderr)
        sys.exit(1)

    width = cfg("view.number_width", 5)
    found = 0
    for i, line in enumerate(lines):
        if regex.search(line):
            text = line.rstrip("\n\r")
            print(f"{i + 1:>{width}} | {text}")
            found += 1

    if found == 0:
        print(f"No matches for '{pattern}'", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n{found} match(es)", file=sys.stderr)


def cmd_summary(path):
    stat = os.stat(path)
    size = stat.st_size
    lines = read_file(path)
    total = len(lines)

    # size formatting
    if size < 1024:
        size_str = f"{size} B"
    elif size < 1024 * 1024:
        size_str = f"{size / 1024:.1f} KB"
    else:
        size_str = f"{size / (1024 * 1024):.1f} MB"

    print(f"File:  {os.path.abspath(path)}")
    print(f"Lines: {total}")
    print(f"Size:  {size_str}")

    # guess if binary
    try:
        with open(path, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                print("Type:  binary")
            else:
                print("Type:  text")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        prog="aiview",
        description="View file contents with line numbers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  aiview main.py              # whole file\n"
               "  aiview main.py -l 42        # line 42\n"
               "  aiview main.py -r 10 30     # lines 10-30\n"
               "  aiview main.py --grep TODO   # find TODOs\n"
               "  aiview main.py --summary    # file info",
    )
    parser.add_argument("file", help="File to view")
    parser.add_argument("-l", "--line", type=int, metavar="N", help="Show single line N")
    parser.add_argument("-r", "--range", type=int, nargs=2, metavar=("START", "END"), help="Show lines START to END")
    parser.add_argument("--head", type=int, metavar="N", help="Show first N lines")
    parser.add_argument("--tail", type=int, metavar="N", help="Show last N lines")
    parser.add_argument("--grep", metavar="PATTERN", help="Show lines matching pattern (regex)")
    parser.add_argument("--summary", action="store_true", help="Show file info (lines, size)")

    args = parser.parse_args()

    if args.summary:
        if not os.path.isfile(args.file):
            print(f"ERROR: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        cmd_summary(args.file)
        return

    lines = read_file(args.file)

    if args.line is not None:
        cmd_view_line(args.file, lines, args.line)
    elif args.range:
        cmd_view_range(args.file, lines, args.range[0], args.range[1])
    elif args.head is not None:
        cmd_head(args.file, lines, args.head)
    elif args.tail is not None:
        cmd_tail(args.file, lines, args.tail)
    elif args.grep:
        cmd_grep(args.file, lines, args.grep)
    else:
        cmd_view_all(args.file, lines)


if __name__ == "__main__":
    main()