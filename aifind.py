#!/usr/bin/env python3
"""
aifind — Search for text patterns across files.

Usage:
    aifind "pattern" <path>                 Recursive search
    aifind "pattern" <path> -ext .py .js    Filter by extension
    aifind "pattern" <file>                 Single file search
    aifind "pattern" <path> -i              Case-insensitive (default)
    aifind "pattern" <path> -s              Case-sensitive

Output format:
    src/main.py:42 | matched line content here
    src/utils.py:7 | another match
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aiconfig import cfg
from aiencoding import read_lines_with_encoding


def should_ignore(dirpath, ignore_dirs):
    parts = dirpath.replace("\\", "/").split("/")
    for part in parts:
        if part in ignore_dirs:
            return True
    return False


def search_file(filepath, regex, max_results, results_so_far):
    results = []
    try:
        lines, _ = read_lines_with_encoding(filepath)
        for i, line in enumerate(lines, 1):
            if results_so_far + len(results) >= max_results:
                return results, True
            if regex.search(line):
                results.append((filepath, i, line.rstrip("\n\r")))
    except (OSError, PermissionError):
        pass
    return results, False


def search_recursive(path, regex, extensions, ignore_dirs, max_results):
    """Walk directory tree searching files."""
    all_results = []
    hit_limit = False

    for root, dirs, files in os.walk(path):
        # prune ignored directories
        rel_root = os.path.relpath(root, path)
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        if should_ignore(rel_root, ignore_dirs):
            continue

        for fname in sorted(files):
            if extensions:
                _, ext = os.path.splitext(fname)
                if ext.lower() not in extensions:
                    continue

            filepath = os.path.join(root, fname)
            results, limit_hit = search_file(filepath, regex, max_results, len(all_results))
            all_results.extend(results)
            if limit_hit:
                hit_limit = True
                break

        if hit_limit:
            break

    return all_results, hit_limit


def main():
    parser = argparse.ArgumentParser(
        prog="aifind",
        description="Search for text patterns across files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               '  aifind "TODO" src/\n'
               '  aifind "def main" . -ext .py\n'
               '  aifind "error" logfile.txt\n'
               '  aifind "className" src/ -s      # case-sensitive',
    )
    parser.add_argument("pattern", help="Search pattern (regex)")
    parser.add_argument("path", help="File or directory to search")
    parser.add_argument("-ext", nargs="+", metavar="EXT",
                        help="Filter by file extension(s), e.g. .py .js")
    parser.add_argument("-s", "--case-sensitive", action="store_true",
                        help="Case-sensitive search (default: case-insensitive)")
    parser.add_argument("-i", "--case-insensitive", action="store_true", default=True,
                        help="Case-insensitive search (default)")
    parser.add_argument("--max", type=int, default=None, metavar="N",
                        help="Max results (default from config)")

    args = parser.parse_args()
    max_results = args.max or cfg("find.max_results", 100)
    ignore_dirs = cfg("find.ignore_dirs", [".git", "node_modules", "__pycache__", ".aibackup"])

    # compile pattern
    flags = 0 if args.case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(args.pattern, flags)
    except re.error as e:
        print(f"ERROR: invalid pattern: {e}", file=sys.stderr)
        sys.exit(1)

    # normalize extensions
    extensions = None
    if args.ext:
        extensions = set()
        for ext in args.ext:
            if not ext.startswith("."):
                ext = "." + ext
            extensions.add(ext.lower())

    path = args.path

    if not os.path.exists(path):
        print(f"ERROR: path not found: {path}", file=sys.stderr)
        sys.exit(1)

    # single file
    if os.path.isfile(path):
        results, _ = search_file(path, regex, max_results, 0)
        hit_limit = len(results) >= max_results
    else:
        results, hit_limit = search_recursive(path, regex, extensions, ignore_dirs, max_results)

    if not results:
        print(f"No matches for '{args.pattern}'", file=sys.stderr)
        sys.exit(1)

    # determine path display width for alignment
    for filepath, line_num, text in results:
        rel = os.path.relpath(filepath)
        print(f"{rel}:{line_num} | {text}")

    count_msg = f"\n{len(results)} match(es)"
    if hit_limit:
        count_msg += f" (limit: {max_results}, use --max to increase)"
    print(count_msg, file=sys.stderr)


if __name__ == "__main__":
    main()