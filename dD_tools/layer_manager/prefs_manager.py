# prefs_manager.py
"""
JSON preferences manager for LayerManager.
Replaces the old nuke.toNode("preferences") / _prefs_registered system.
"""
import json
import dD_log
from lm_config import PREFS_FILE, PREFS_DEFAULT


def _load_defaults():
    """Load default preferences from lm_prefs_default.json."""
    with open(PREFS_DEFAULT, 'r', encoding='utf-8') as f:
        return json.load(f)


def load():
    """Load user prefs merged with defaults."""
    defaults = _load_defaults()
    if not PREFS_FILE.exists():
        return defaults.copy()
    try:
        with open(PREFS_FILE, 'r', encoding='utf-8') as f:
            return {**defaults, **json.load(f)}
    except Exception as e:
        dD_log.warning(f"Error reading prefs: {e} -- using defaults")
        return defaults.copy()


def save(prefs):
    """Persist preferences (without _comment/_version keys)."""
    to_save = {k: v for k, v in prefs.items() if not k.startswith('_')}
    try:
        with open(PREFS_FILE, 'w', encoding='utf-8') as f:
            json.dump(to_save, f, indent=2, ensure_ascii=False)
    except Exception as e:
        dD_log.error(f"Error saving prefs: {e}")


def get(key, default=None):
    """Get a single preference value."""
    return load().get(key, default)


def set_pref(key, value):
    """Set a single preference value and save."""
    prefs = load()
    prefs[key] = value
    save(prefs)
