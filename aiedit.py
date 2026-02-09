#!/usr/bin/env python3
"""
aiedit — Surgical line-based file editing with auto-backup.

Usage:
    aiedit <file> replace <line> -c "new content"              Replace single line
    aiedit <file> replace <start> <end> -c "new content"       Replace line range
    aiedit <file> insert <line> -c "content"                    Insert BEFORE line N
    aiedit <file> append <line> -c "content"                    Insert AFTER line N
    aiedit <file> delete <line>                                 Delete single line
    aiedit <file> delete <start> <end>                          Delete line range

For multiline content, use --stdin to read from stdin:
    echo -e "line1\\nline2" | aiedit file.py insert 5 --stdin

Use --force to bypass large-delete safety check.
Use --no-backup to skip auto-backup for this edit.

Newlines in content: Use literal \\n in -c strings, or use --stdin.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aiconfig import cfg
from aiencoding import read_lines_with_encoding, write_lines_with_encoding


def read_file(path):
    if not os.path.isfile(path):
        if cfg("edit.create_if_missing", False):
            return [], "utf-8"
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        return read_lines_with_encoding(path)
    except Exception as e:
        print(f"ERROR: cannot read file: {e}", file=sys.stderr)
        sys.exit(1)


def write_file(path, lines, encoding="utf-8"):
    try:
        write_lines_with_encoding(path, lines, encoding)
    except Exception as e:
        print(f"ERROR: cannot write file: {e}", file=sys.stderr)
        sys.exit(1)


def do_backup(filepath):
    """Auto-backup if enabled in config. Returns backup path or None."""
    if not cfg("backup.enabled", True):
        return None
    try:
        from aibackup import save_backup
        return save_backup(filepath)
    except Exception as e:
        print(f"WARNING: backup failed: {e}", file=sys.stderr)
        return None


def ensure_newline(text):
    """Ensure text ends with newline."""
    if not text.endswith("\n"):
        return text + "\n"
    return text


def parse_content(content_str, use_stdin):
    """Parse content from argument or stdin. Returns list of lines."""
    if use_stdin:
        raw = sys.stdin.read()
    else:
        if content_str is None:
            print("ERROR: no content provided (use positional arg or --stdin)", file=sys.stderr)
            sys.exit(1)
        # expand literal \n to actual newlines
        raw = content_str.replace("\\n", "\n")

    # split into lines, each ending with \n
    result = []
    for line in raw.split("\n"):
        result.append(line + "\n")

    # if the input ended with \n, we'll have an extra empty line — remove it
    if raw.endswith("\n") and len(result) > 1 and result[-1] == "\n":
        result.pop()

    return result


def validate_line(line_num, total, label="line"):
    if line_num < 1:
        print(f"ERROR: {label} must be >= 1 (got {line_num})", file=sys.stderr)
        sys.exit(1)
    if line_num > total:
        print(f"ERROR: {label} {line_num} out of range (file has {total} lines)", file=sys.stderr)
        sys.exit(1)


def cmd_replace(filepath, lines, args, encoding):
    total = len(lines)
    start = args.line_start
    end = args.line_end if args.line_end else args.line_start

    validate_line(start, total, "start line")
    validate_line(end, total, "end line")
    if start > end:
        print(f"ERROR: start ({start}) > end ({end})", file=sys.stderr)
        sys.exit(1)

    new_content = parse_content(args.content, args.stdin)

    if not args.no_backup:
        backup = do_backup(filepath)

    lines[start - 1:end] = new_content
    write_file(filepath, lines, encoding)

    if start == end:
        msg = f"OK: replaced line {start} in {filepath}"
    else:
        msg = f"OK: replaced lines {start}-{end} with {len(new_content)} line(s) in {filepath}"

    if not args.no_backup and cfg("backup.enabled", True):
        msg += f" (backup saved)"
    print(msg)


def cmd_insert(filepath, lines, args, encoding):
    total = len(lines)
    line_num = args.line_start

    if line_num < 1 or line_num > total + 1:
        print(f"ERROR: line {line_num} out of range (valid: 1-{total + 1})", file=sys.stderr)
        sys.exit(1)

    new_content = parse_content(args.content, args.stdin)

    if not args.no_backup:
        do_backup(filepath)

    insert_idx = line_num - 1
    for i, new_line in enumerate(new_content):
        lines.insert(insert_idx + i, new_line)

    write_file(filepath, lines, encoding)
    print(f"OK: inserted {len(new_content)} line(s) before line {line_num} in {filepath}")


def cmd_append(filepath, lines, args, encoding):
    total = len(lines)
    line_num = args.line_start

    validate_line(line_num, total)

    new_content = parse_content(args.content, args.stdin)

    if not args.no_backup:
        do_backup(filepath)

    insert_idx = line_num
    for i, new_line in enumerate(new_content):
        lines.insert(insert_idx + i, new_line)

    write_file(filepath, lines, encoding)
    print(f"OK: inserted {len(new_content)} line(s) after line {line_num} in {filepath}")


def cmd_delete(filepath, lines, args, encoding):
    total = len(lines)
    start = args.line_start
    end = args.line_end if args.line_end else args.line_start

    validate_line(start, total, "start line")
    validate_line(end, total, "end line")
    if start > end:
        print(f"ERROR: start ({start}) > end ({end})", file=sys.stderr)
        sys.exit(1)

    count = end - start + 1
    max_delete = cfg("edit.confirm_large_delete", 50)
    if count > max_delete and not args.force:
        print(f"ERROR: refusing to delete {count} lines (max {max_delete}). Use --force to override.", file=sys.stderr)
        sys.exit(1)

    if not args.no_backup:
        do_backup(filepath)

    del lines[start - 1:end]
    write_file(filepath, lines, encoding)

    if start == end:
        print(f"OK: deleted line {start} from {filepath}")
    else:
        print(f"OK: deleted lines {start}-{end} ({count} lines) from {filepath}")


def main():
    parser = argparse.ArgumentParser(
        prog="aiedit",
        description="Surgical line-based file editing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               '  aiedit main.py replace 10 -c "new line content"\n'
               '  aiedit main.py replace 10 15 -c "replacement block"\n'
               '  aiedit main.py insert 5 -c "inserted before line 5"\n'
               '  aiedit main.py append 5 -c "inserted after line 5"\n'
               "  aiedit main.py delete 10\n"
               "  aiedit main.py delete 10 20\n"
               '  echo "multi\\nline" | aiedit main.py insert 5 --stdin',
    )
    parser.add_argument("file", help="File to edit")
    parser.add_argument("action", choices=["replace", "insert", "append", "delete"],
                        help="Edit action")
    parser.add_argument("line_start", type=int, help="Line number (or start of range)")
    parser.add_argument("line_end", type=int, nargs="?", default=None,
                        help="End of line range (for replace/delete range)")
    parser.add_argument("-c", "--content", default=None,
                        help="New content (use \\\\n for newlines). Required for replace/insert/append.")
    parser.add_argument("--stdin", action="store_true",
                        help="Read content from stdin instead of -c")
    parser.add_argument("--force", action="store_true",
                        help="Bypass large-delete safety check")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip auto-backup for this edit")

    args = parser.parse_args()

    lines, encoding = read_file(args.file)

    if args.action == "replace":
        cmd_replace(args.file, lines, args, encoding)
    elif args.action == "insert":
        cmd_insert(args.file, lines, args, encoding)
    elif args.action == "append":
        cmd_append(args.file, lines, args, encoding)
    elif args.action == "delete":
        cmd_delete(args.file, lines, args, encoding)


if __name__ == "__main__":
    main()