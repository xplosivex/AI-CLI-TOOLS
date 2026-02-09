# AI File Tools

Line-based file viewing and editing tools designed for AI assistants. Cross-platform, encoding-aware, with automatic backups.

## Overview

AI assistants often struggle with file editing because they can't reliably track line numbers after making changes. These tools enforce a **read-verify-edit-verify** workflow that prevents blind edits and provides automatic recovery.

**Key Principles:**
- Always show line numbers
- Edit by line number, not by guessing
- Backup before every change
- Preserve file encoding

## Features

- **Line-numbered output** — Always know exactly where you are
- **Surgical edits** — Replace, insert, append, or delete specific lines
- **Automatic backups** — Every edit creates a timestamped backup
- **Universal encoding** — UTF-8, UTF-16, UTF-32, CP1252, Latin-1 with BOM detection
- **Cross-platform** — Windows, Linux, macOS
- **Zero dependencies** — Pure Python 3 standard library only

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/aitools.git
cd aitools
python install.py
```

Verify installation:
```bash
python install.py --check
```

Uninstall:
```bash
python install.py --uninstall
```

### Platform Notes

**Linux/macOS:** Creates wrapper scripts in `~/.local/bin/` and updates shell PATH.

**Windows:** Creates `.bat` wrappers in `%USERPROFILE%\.aitools\bin\` and updates user PATH via registry. For PowerShell, add this to your `$PROFILE`:
```powershell
. "$HOME\.aitools\bin\aitools_ps_profile.ps1"
```

No admin/sudo required on any platform.

## Tools

### aiview — View files with line numbers

```bash
aiview <file>                    # Entire file
aiview <file> -l 50              # Single line
aiview <file> -r 10 25           # Line range
aiview <file> --head 20          # First 20 lines
aiview <file> --tail 20          # Last 20 lines
aiview <file> --grep "pattern"   # Search with line numbers
aiview <file> --summary          # File info
```

Output format:
```
   10 | def main():
   11 |     parser = argparse.ArgumentParser()
   12 |     args = parser.parse_args()
```

### aiedit — Edit files by line number

```bash
aiedit <file> replace <line> -c "content"           # Replace single line
aiedit <file> replace <start> <end> -c "content"    # Replace range
aiedit <file> insert <line> -c "content"            # Insert BEFORE line
aiedit <file> append <line> -c "content"            # Insert AFTER line
aiedit <file> delete <line>                         # Delete single line
aiedit <file> delete <start> <end>                  # Delete range
```

For multiline content, use `\n` in the string or pipe via stdin:
```bash
aiedit file.py replace 10 -c "line one\nline two\nline three"

echo -e "line one\nline two" | aiedit file.py insert 5 --stdin
```

Flags:
- `--no-backup` — Skip automatic backup for this edit
- `--force` — Allow deleting more than 50 lines at once

### aibackup — Backup and restore

```bash
aibackup save <file>                    # Create backup
aibackup save <file> --tag "name"       # Named backup
aibackup list <file>                    # List all backups
aibackup restore <file>                 # Restore most recent
aibackup restore <file> --tag "name"    # Restore specific backup
aibackup diff <file>                    # Diff current vs last backup
```

Backups are stored in `.aibackup/` next to the original file.

### aidiff — Compare files

```bash
aidiff <file1> <file2>              # Compare two files
aidiff <file> --backup              # Compare vs last backup
aidiff <file> --backup --tag "name" # Compare vs specific backup
```

### aifind — Search across files

```bash
aifind "pattern" <path>                  # Recursive search
aifind "pattern" <path> -ext .py .js     # Filter by extension
aifind "pattern" <file>                  # Single file
aifind "pattern" <path> -s               # Case-sensitive
aifind "pattern" <path> --max 50         # Limit results
```

Output format:
```
src/main.py:42 | matched line content here
src/utils.py:7 | another match

2 match(es)
```

## Recommended Workflow

1. **Read before editing** — Always `aiview` the target lines first
2. **Edit precisely** — Use exact line numbers from `aiview`
3. **Verify after editing** — `aiview` again to confirm changes
4. **Use backups** — If something goes wrong, `aibackup restore`

```bash
# Example workflow
aiview app.py -r 40 50          # See current state
aiedit app.py replace 45 -c "    return result"
aiview app.py -r 43 47          # Verify the change
```

### Working Bottom-to-Top

When making multiple edits, work from bottom to top to avoid line number shifts:

```bash
# WRONG — line 20 shifts after first insert
aiedit app.py insert 10 -c "import json"
aiedit app.py insert 20 -c "import yaml"   # This is now line 21!

# RIGHT — work bottom-up
aiedit app.py insert 20 -c "import yaml"
aiedit app.py insert 10 -c "import json"
```

Or re-read line numbers between edits:
```bash
aiedit app.py insert 10 -c "import json"
aiview app.py --grep "def process"         # Find new line number
aiedit app.py insert 21 -c "import yaml"   # Use updated number
```

## Configuration

Create `aitool.yml` in your project root or `~/.aitool.yml`:

```yaml
backup:
  enabled: true
  max_backups: 20
  dir: .aibackup

view:
  max_lines: 500
  number_width: 5

edit:
  confirm_large_delete: 50
  create_if_missing: false

find:
  max_results: 100
  ignore_dirs:
    - .git
    - node_modules
    - __pycache__
    - .aibackup
    - .venv
```

Configuration is searched upward from the current directory, then falls back to `~/.aitool.yml`.

## Encoding Support

These tools automatically detect and preserve file encoding:

- UTF-8 (with and without BOM)
- UTF-16 LE/BE (Windows PowerShell default)
- UTF-32 LE/BE
- CP1252 (Windows legacy)
- Latin-1 (fallback)

BOM markers are detected and handled transparently. Files are written back in their original encoding.

## File Structure

```
aitools/
├── aiview.py       # View tool
├── aiedit.py       # Edit tool
├── aibackup.py     # Backup tool
├── aidiff.py       # Diff tool
├── aifind.py       # Search tool
├── aiconfig.py     # Configuration loader
├── aiencoding.py   # Encoding detection
├── aitool.yml      # Default config
├── install.py      # Installer
└── README.md
```

## Requirements

- Python 3.8 or higher
- No external dependencies (standard library only)

## License

MIT License — see LICENSE file for details.

## Contributing

Contributions welcome. Please ensure any changes:
- Work on Windows, Linux, and macOS
- Handle all supported encodings
- Maintain zero external dependencies
- Include appropriate error handling
