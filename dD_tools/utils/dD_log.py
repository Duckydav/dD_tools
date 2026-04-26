# dD_log.py
"""
Centralized logging module for LayerManager.
Import in each module and use dD_log.debug/info/warning/error.
Toggle debug output with dD_log.set_debug(True/False).
"""

_debug = False
_prefix = "[LayerManager]"


def set_debug(enabled):
    """Enable or disable debug-level output."""
    global _debug
    _debug = bool(enabled)


def is_debug():
    """Return True if debug mode is active."""
    return _debug


def debug(msg):
    """Print a debug message (only when debug mode is active)."""
    if _debug:
        print(f"{_prefix} [DEBUG] {msg}")


def info(msg):
    """Print an informational message."""
    print(f"{_prefix} {msg}")


def warning(msg):
    """Print a warning message."""
    print(f"{_prefix} [WARNING] {msg}")


def error(msg):
    """Print an error message."""
    print(f"{_prefix} [ERROR] {msg}")
