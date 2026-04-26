# lm_config.py
"""
LayerManager -- Central configuration.
Single source of truth for all paths, constants and metadata.

To adapt to a studio environment, modify only this file.
"""
from pathlib import Path

# -- Project root (auto-detected, portable) ------------------------------------
LM_ROOT        = Path(__file__).parent
ICONS_DIR      = LM_ROOT / "icons"
PREFS_FILE     = LM_ROOT / "lm_prefs.json"
PREFS_DEFAULT  = LM_ROOT / "lm_prefs_default.json"

# -- Version & Metadata -------------------------------------------------------
VERSION        = "2.40"
HELP_LINK      = "https://github.com/Duckydav/LayerManager"
AUTHOR_LINK    = "https://www.linkedin.com/in/davidfrancois/"

# -- Nuke Panel ----------------------------------------------------------------
PANEL_ID       = "com.duckydav.LayerManager"
PANEL_NAME     = "Layer Manager"

# -- UI Constants --------------------------------------------------------------
DEFAULT_TEXT_COLOR  = "#c0c0c0"
HIGHLIGHT_COLOR     = "orange"

# -- Icons (filenames -- resolved via ICONS_DIR) --------------------------------
ICON_PREV_NORMAL    = "prev31.png"
ICON_NEXT_NORMAL    = "next31.png"
ICON_PREV_ORANGE    = "prev31_orange.png"
ICON_NEXT_ORANGE    = "next31_orange.png"
ICON_REFRESH        = "refresh.png"
ICON_CONTACT_1      = "contact_sheet_1.png"
ICON_CONTACT_0      = "contact_sheet_0.png"
ICON_SETTINGS       = "settings.png"

# -- LightGrade export (studio-specific, override as needed) -------------------
LIGHTGRADE_EXPORT_DIR = None   # None = export next to Nuke script
LIGHTGRADE_PATH_REGEX = None   # None = use generic extraction

# -- Studio Mode ---------------------------------------------------------------
# True = studio version  |  False = personal / open-source version
STUDIO_MODE = False

# Override these to point to your studio's shared gizmo/toolset directories:
STUDIO_GIZMO_DIR  = None   # e.g. r"/shared/nuke/gizmos"
STUDIO_SCRIPT_DIR = None   # e.g. r"/shared/nuke/toolsets"
