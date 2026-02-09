"""
aiconfig.py — Shared configuration loader for AI tools.

Searches upward from CWD for aitool.yml, falls back to ~/.aitool.yml,
then falls back to built-in defaults. Project config overrides global.

Usage from other tools:
    from aiconfig import cfg
    if cfg("backup.enabled"):
        ...
"""

import os
import sys

try:
    import yaml as _yaml
    def _load_yaml(path):
        with open(path, "r", encoding="utf-8") as f:
            return _yaml.safe_load(f) or {}
except ImportError:
    _yaml = None
    def _load_yaml(path):
        """Minimal YAML-subset parser. Handles flat and one-level nested keys,
        strings, ints, bools, and simple lists (- item). Good enough for aitool.yml."""
        data = {}
        current_section = None
        current_list_key = None
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.rstrip()
                stripped = line.lstrip()

                # skip blanks and comments
                if not stripped or stripped.startswith("#"):
                    current_list_key = None
                    continue

                indent = len(line) - len(stripped)

                # list item under a key
                if stripped.startswith("- ") and current_list_key and current_section:
                    val = stripped[2:].strip().strip('"').strip("'")
                    data[current_section][current_list_key].append(val)
                    continue

                current_list_key = None

                if ":" not in stripped:
                    continue

                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip()

                # section header (no value)
                if not val and indent == 0:
                    current_section = key
                    if current_section not in data:
                        data[current_section] = {}
                    continue

                # value line
                val = val.strip('"').strip("'")

                # type coercion
                parsed = _parse_value(val)

                if indent > 0 and current_section:
                    if parsed == "__empty_list__":
                        data[current_section][key] = []
                        current_list_key = key
                    else:
                        data[current_section][key] = parsed
                else:
                    if parsed == "__empty_list__":
                        data[key] = []
                        current_list_key = key
                    else:
                        data[key] = parsed

        return data

    def _parse_value(val):
        if val == "" or val is None:
            return "__empty_list__"
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False
        try:
            return int(val)
        except ValueError:
            pass
        try:
            return float(val)
        except ValueError:
            pass
        return val


DEFAULTS = {
    "backup": {
        "enabled": True,
        "dir": ".aibackup",
        "max_backups": 20,
    },
    "view": {
        "max_lines": 500,
        "number_width": 5,
    },
    "edit": {
        "confirm_large_delete": 50,
        "create_if_missing": False,
    },
    "find": {
        "ignore_dirs": [".git", "node_modules", "__pycache__", ".aibackup", ".venv", "venv"],
        "max_results": 100,
    },
}


def _find_config_file(start_dir):
    """Walk upward from start_dir looking for aitool.yml."""
    d = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(d, "aitool.yml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def _deep_merge(base, override):
    """Merge override into base, returning new dict. Override wins on conflicts."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def load_config():
    """Load merged config: defaults <- global ~/.aitool.yml <- project aitool.yml"""
    config = dict(DEFAULTS)

    # global config
    global_path = os.path.join(os.path.expanduser("~"), ".aitool.yml")
    if os.path.isfile(global_path):
        try:
            config = _deep_merge(config, _load_yaml(global_path))
        except Exception:
            pass

    # project config (walk up from cwd)
    project_path = _find_config_file(os.getcwd())
    if project_path:
        try:
            config = _deep_merge(config, _load_yaml(project_path))
        except Exception:
            pass

    return config


_config = None

def cfg(dotpath, default=None):
    """Get a config value by dot-separated path. e.g. cfg("backup.enabled")"""
    global _config
    if _config is None:
        _config = load_config()

    keys = dotpath.split(".")
    val = _config
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            return default
    return val


def reload_config():
    """Force config reload."""
    global _config
    _config = None
    return cfg("backup.enabled")  # trigger load


if __name__ == "__main__":
    import json
    config = load_config()
    print(json.dumps(config, indent=2))