# ----------------------------------------------------------------------------------------------------------
# Layer Manager
# Author: David Francois
# Copyright (c) 2024, David Francois
# ----------------------------------------------------------------------------------------------------------

"""

@description:
This tool provides a user-friendly interface for quickly visualizing Viewer Layer Channels with a single click.
It also enables the addition of a LightGrade layer with a second click when selecting a Light Layer.

Features:
- Efficiently navigate through available layers
- Easily create LightGrade, Shuffle, and Contribution nodes
- Customizable sections and preferences for better organization
- Multi-mode auto-refresh with intelligent fallback system
- Docked panel restoration with robust workspace integration

v2_40 CHANGELOG - Multi-Instance Support COMPLETE:
===========================================================
FIXED BUG 1: Limited to 3 simultaneous Nuke instances
  - Cause: cleanup_all_instances() cleaned ALL instances without filtering
  - Solution: Intelligent per-instance filtering in ALL cleanup functions
  - Method: Robust main window detection (metaObject().className())
  - Fallback: Secure (False instead of True if uncertain)
  - Result: UNLIMITED simultaneous instances support (N instances, no limit)

FIXED BUG 2: Docked panel does not reappear after restart
  - Cause: Fragile multi-mode system from v2_38 without fallback
  - Solution: Try/except + automatic fallback to simple polling on failure
  - Result: Reliable docked panel restoration in workspace

NEW: Multi-Mode Refresh System (v2_38) + Robustness:
  - Mode 1 - event_driven: Native Nuke callback (0% CPU idle, instant)
  - Mode 2 - hybrid: Adaptive polling 500ms->2s->10s (-95% CPU idle)
  - Mode 3 - focus_only: Refresh on focus only (near 0% CPU)
  - FALLBACK: If setup fails, automatically switch to simple polling
  - Hot-swap mode without restarting Layer Manager

IMPROVED: Robustness & Reliability:
  - Unified closeEvent (eliminated v2_38 duplication)
  - Auto migration of preferences v2_38 -> v2_39
  - Try/except on all critical points
  - Guarantee: Panel ALWAYS works even in fallback mode
  - Improved logging for diagnosing issues

TECHNICAL BASE:
  - Foundation: v2_37 stable + v2_38 multi-mode + Bug 1 & 2 fixes
  - Robust system with guaranteed fallback
  - Compatible with all modes: docked, floating, panel
  - Thread-safe multi-instance cleanup
"""


import os
import sys
from pathlib import Path

# ----------------------------------------------------------------------------#
# ---------------------------------------------------------------- ADD PATH --#
from lm_config import (
    VERSION, HELP_LINK, AUTHOR_LINK, PANEL_ID, PANEL_NAME,
    DEFAULT_TEXT_COLOR, HIGHLIGHT_COLOR, ICONS_DIR,
    ICON_PREV_NORMAL, ICON_NEXT_NORMAL, ICON_PREV_ORANGE, ICON_NEXT_ORANGE,
    ICON_REFRESH, ICON_CONTACT_1, ICON_CONTACT_0, ICON_SETTINGS,
    STUDIO_MODE, STUDIO_GIZMO_DIR, STUDIO_SCRIPT_DIR,
)

# ----------------------------------------------------------------------------#
# ----------------------------------------------------------------- IMPORTS --#

import nuke
import json
import math
import importlib
import traceback
import time  # v2_39: Multi-mode refresh system
import fnmatch  # wildcard * support in keywords

# Relative imports from layermanager package
import shuffle
import debug_help
import utils_fonctions
import lightgrade_module
import dD_log

from debug_help import open_layermanager_help
from utils_fonctions import insert_node_below_visually, get_last_selected_node
from lightgrade_module import create_lightgrade, add_layer_to_lightgrade, add_layer, get_active_lightgrade_node


from nukescripts import panels



# All users are authorized in open source mode
USER_IS_AUTHORIZED = True

from PySide2.QtWidgets import QApplication, QWidget, QHBoxLayout, QTabWidget, QListWidget, \
    QListWidgetItem, QFrame, QVBoxLayout, QGridLayout, QLabel, QPushButton, QMessageBox, QShortcut, \
    QDialog, QLineEdit, QCheckBox, QComboBox
from PySide2 import QtGui, QtWidgets
from PySide2.QtCore import Qt, Signal, QTimer, QSize, QUrl
from PySide2.QtGui import QColor, QIcon, QKeySequence, QDesktopServices

channel_list_window = None




def credit():
    return (
        f"<p style='color:#A2A1A1'>"
        f"<a href='{HELP_LINK}' style='text-decoration:none; color:#A2A1A1;'>"
        "Layer<b><font color='#545454'>Manager</font></b>"
        "</a>"
        f" <font color='#888888'>{VERSION}</font> &copy; 2024"
        "<span style='color:#888888;'> | </span>"
        f"<a href='{AUTHOR_LINK}' style='text-decoration:none; color:#888888;'><font size=3>DavidF</font></a> "
        "<span style='color:#888888;'> | </span>"
        f"<a href='{HELP_LINK}' style='text-decoration:none; color:#FCB132;'><font size=3>help</font></a>"
        "</p>"
    )


# ========================================================================
# BUG FIX v2_39: Instance Nuke Detection Functions
# Prevents closing LayerManager from other Nuke instances
# ========================================================================

def _get_current_nuke_main_window():
    """
    Returns the main window of this Nuke instance.

    Uses the official Foundry method: identification via metaObject().className()
    instead of searching for "Nuke" in the title (more reliable).

    Used to filter widgets belonging to the current instance
    and avoid affecting other Nuke instances.
    """
    try:
        from PySide2.QtWidgets import QMainWindow
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                # Robust method: use internal Qt className (Foundry official method)
                try:
                    class_name = widget.metaObject().className()
                    if class_name == 'Foundry::UI::DockMainWindow':
                        return widget
                except:
                    pass

        # Fallback: search for "Nuke" in title if metaObject() fails
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, QMainWindow):
                title = widget.windowTitle() if hasattr(widget, 'windowTitle') else ''
                if 'Nuke' in title:
                    return widget
    except Exception as e:
        dD_log.error(f"Nuke window detection error: {e}")
    return None


def _is_same_nuke_instance(widget, main_window):
    """
    Checks if a widget belongs to this Nuke instance.

    Iterates through the parent hierarchy to determine if the widget
    is a child of this Nuke instance's main window.

    SECURITY: If the main window cannot be detected, returns False
    to avoid modifying widgets from other instances.
    """
    if not main_window:
        # Secure fallback: do not touch if uncertain
        dD_log.warning("[SECURITY] Cannot detect main window - skipping widget")
        return False

    try:
        parent = widget
        while parent:
            if parent == main_window:
                return True
            parent = parent.parent() if hasattr(parent, 'parent') else None
    except:
        return True  # Fallback on error

    return False


class LayerSelector(QListWidget):
    """
    A custom QListWidget for managing and interacting with layers.

    Features:
    - Keyboard shortcuts for quick navigation and actions
    - Mouse interactions for selection and layer operations
    - Custom styles and dynamic updates
    """

    keyPressed =Signal(int)
    ctrlClicked =Signal(QListWidgetItem)
    shiftClicked =Signal(QListWidgetItem)
    shiftCtrlClicked =Signal(QListWidgetItem)
    altClicked =Signal(QListWidgetItem)
    ctrlPressed =Signal(bool)
    shiftPressed =Signal(bool)
    rowChanged =Signal(int)
    
    leftPressed = Signal()
    rightPressed = Signal()

    
    is_empty_layer_present = False

    def __init__(self, parent=None):
        super(LayerSelector, self).__init__(parent)

        # Detect if in floating mode via the parent
        parent_widget = parent
        is_floating = False

        # Walk up the parent hierarchy to determine the mode
        while parent_widget:
            if hasattr(parent_widget, 'windowFlags') and (parent_widget.windowFlags() & Qt.Tool):
                is_floating = True
                break
            parent_widget = parent_widget.parent()

        # Configure focus policy based on the mode
        if is_floating:
            self.setFocusPolicy(Qt.StrongFocus)  # Floating
        else:
            self.setFocusPolicy(Qt.ClickFocus)  # Docked

    def keyReleaseEvent(self, event):
        QListWidget.keyReleaseEvent(self, event)

        if event.key() == Qt.Key_Shift:
            self.shiftPressed.emit(False)
        elif event.key() == Qt.Key_Control:
            self.ctrlPressed.emit(False)

    def mousePressEvent(self, event):
        if self.is_empty_layer_present:
            return
        QListWidget.mousePressEvent(self, event)

        item = self.itemAt(event.pos())
        if item:
            if event.button() == Qt.LeftButton and QApplication.keyboardModifiers() == Qt.ControlModifier:
                self.ctrlClicked.emit(item)
            elif event.button() == Qt.LeftButton and QApplication.keyboardModifiers() == Qt.ShiftModifier:
                self.shiftClicked.emit(item)
            elif event.button() == Qt.LeftButton and QApplication.keyboardModifiers() == (Qt.ShiftModifier | Qt.ControlModifier):
                self.shiftCtrlClicked.emit(item)

    def setStyleSheet(self, styleSheet):
        QListWidget.setStyleSheet(self, styleSheet)

    def add_layer_to_list(self, layer_name, custom):
        if not custom:
            layer_name = "!!! Layer Empty !!!"
        item = QListWidgetItem(layer_name)
        self.addItem(item)

def get_active_sections(light, mask, utility, custom):
    active_sections = []
    if not light:
        active_sections.append(0)
    if not mask:
        active_sections.append(1)
    active_sections.append(2)  # Tech Layer
    if not utility:
        active_sections.append(3)
    if not custom:
        active_sections.append(4)
    return active_sections

class LayerManagerPrefsDialog(QDialog):
    """Standalone preferences panel matching Nuke Preferences style."""

    def __init__(self, parent=None):
        super(LayerManagerPrefsDialog, self).__init__(parent)
        import prefs_manager
        self.prefs = prefs_manager.load()
        self.setWindowTitle("Preferences - Layer Manager")
        self.setMinimumWidth(700)
        self.setMinimumHeight(520)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 15)
        layout.setSpacing(4)

        # -- Title: Layer Manager VERSION
        title = QLabel(
            '<span style="font-size:18px; color:#FCB132; font-weight:bold;">Layer</span> '
            '<span style="font-size:18px; color:#FFFFFF; font-weight:bold;">Manager</span> '
            '<span style="font-size:14px; color:#888888;">%s</span>' % VERSION
        )
        layout.addWidget(title)
        layout.addSpacing(12)

        # -- Explanation
        layout.addWidget(QLabel(
            '<p style="font-size:11px; color:#777777; font-style:italic;">'
            'Define the keywords for each section of the Layer:</p>'
        ))
        layout.addSpacing(4)

        # -- Keywords grid: Label | Input | Disable checkbox
        self._keyword_fields = {}
        self._disable_checks = {}

        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        # Tech Layer (read-only info)
        tech_label = QLabel('<span style="color:#FCB132;">Tech</span> Layer')
        tech_field = QLineEdit("The default section if no words are specified.")
        tech_field.setEnabled(False)
        tech_disable = QCheckBox("Disable")
        tech_disable.setChecked(bool(self.prefs.get("disable_tech", False)))
        self._disable_checks["disable_tech"] = tech_disable
        grid.addWidget(tech_label, 0, 0)
        grid.addWidget(tech_field, 0, 1)
        grid.addWidget(tech_disable, 0, 2)

        # Light, Mask, Utility layers
        keyword_rows = [
            ("light_keywords", "Light", "disable_light", 1),
            ("mask_keywords", "Mask", "disable_mask", 2),
            ("utility_keywords", "Utility", "disable_utility", 3),
        ]
        for key, name, disable_key, row in keyword_rows:
            label = QLabel('<span style="color:#FCB132;">%s</span> Layer' % name)
            edit = QLineEdit(", ".join(self.prefs.get(key, [])))
            disable_cb = QCheckBox("Disable")
            disable_cb.setChecked(bool(self.prefs.get(disable_key, False)))
            self._keyword_fields[key] = edit
            self._disable_checks[disable_key] = disable_cb
            grid.addWidget(label, row, 0)
            grid.addWidget(edit, row, 1)
            grid.addWidget(disable_cb, row, 2)

        layout.addLayout(grid)
        layout.addSpacing(12)

        # -- Custom Layer section
        custom_grid = QGridLayout()
        custom_grid.setColumnStretch(1, 1)
        custom_grid.setHorizontalSpacing(10)
        custom_grid.setVerticalSpacing(6)

        custom_label = QLabel('<span style="color:#FCB132;">Custom</span> Layer')
        custom_edit = QLineEdit(", ".join(self.prefs.get("custom_keywords", [])))
        self._keyword_fields["custom_keywords"] = custom_edit
        custom_disable = QCheckBox("Disable")
        custom_disable.setChecked(bool(self.prefs.get("disable_custom", True)))
        self._disable_checks["disable_custom"] = custom_disable

        custom_grid.addWidget(custom_label, 0, 0)
        custom_grid.addWidget(custom_edit, 0, 1)
        custom_grid.addWidget(custom_disable, 0, 2)

        custom_title_label = QLabel("Custom Title")
        self._custom_title = QLineEdit(self.prefs.get("custom_title", "custom"))
        custom_grid.addWidget(custom_title_label, 1, 0)
        custom_grid.addWidget(self._custom_title, 1, 1)

        layout.addLayout(custom_grid)
        layout.addWidget(QLabel(
            '<p style="font-size:11px; color:#777777; font-style:italic;">'
            'Use your own <b>Custom Layer</b> name (e.g. Dimatte, Contribution Grade...).</p>'
        ))
        layout.addSpacing(8)

        # -- Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.HLine)
        sep1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep1)
        layout.addSpacing(4)

        # -- Exclusion Keywords
        excl_layout = QHBoxLayout()
        excl_layout.setSpacing(10)
        excl_layout.addWidget(QLabel("Exclusion Keywords"))
        excl_edit = QLineEdit(", ".join(self.prefs.get("exclusion_keywords", [])))
        self._keyword_fields["exclusion_keywords"] = excl_edit
        excl_layout.addWidget(excl_edit, 1)
        layout.addLayout(excl_layout)
        layout.addWidget(QLabel(
            '<p style="font-size:11px; color:#777777; font-style:italic;">'
            'Ignore unwanted layers (e.g. Cryptomatte, rgba...).</p>'
        ))
        layout.addSpacing(8)

        # -- Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep2)
        layout.addSpacing(8)

        # -- Auto-Refresh System
        layout.addWidget(QLabel(
            '<p style="font-size:14px; font-weight:bold; color:#FCB132;">'
            'Auto-Refresh System</p>'
        ))

        refresh_row = QHBoxLayout()
        refresh_row.setSpacing(10)
        refresh_row.addWidget(QLabel("Refresh Mode"))
        self._refresh_combo = QComboBox()
        self._refresh_combo.addItems(["hybrid", "event_driven", "focus_only"])
        current_mode = self.prefs.get("refresh_mode", "hybrid")
        idx = self._refresh_combo.findText(current_mode)
        if idx >= 0:
            self._refresh_combo.setCurrentIndex(idx)
        refresh_row.addWidget(self._refresh_combo)
        refresh_row.addStretch()
        layout.addLayout(refresh_row)

        layout.addWidget(QLabel(
            '<p style="font-size:11px; color:#777777; font-style:italic;">'
            '<b>hybrid</b>: Adaptive polling 500ms&rarr;2s&rarr;10s (-95% CPU idle) - Recommended<br>'
            '<b>event_driven</b>: Native Nuke callback (0% CPU idle, can be unstable)<br>'
            '<b>focus_only</b>: Refresh on focus only (near 0% CPU, less reactive)</p>'
        ))
        layout.addSpacing(4)

        # -- Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        sep3.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep3)

        layout.addStretch()

        # -- Bottom buttons
        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("Restore Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        ok_btn = QPushButton("Save")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _collect_values(self):
        result = {}
        for key, edit in self._keyword_fields.items():
            result[key] = [x.strip() for x in edit.text().split(",") if x.strip()]
        result["custom_title"] = self._custom_title.text().strip() or "custom"
        for key, cb in self._disable_checks.items():
            result[key] = cb.isChecked()
        result["refresh_mode"] = self._refresh_combo.currentText()
        return result

    def accept(self):
        import prefs_manager
        prefs_manager.save(self._collect_values())
        super(LayerManagerPrefsDialog, self).accept()

    def _reset_defaults(self):
        import prefs_manager
        defaults = prefs_manager._load_defaults()
        self._populate_ui(defaults)

    def _populate_ui(self, prefs):
        for key, edit in self._keyword_fields.items():
            edit.setText(", ".join(prefs.get(key, [])))
        self._custom_title.setText(prefs.get("custom_title", "custom"))
        for key, cb in self._disable_checks.items():
            cb.setChecked(bool(prefs.get(key, False)))
        idx = self._refresh_combo.findText(prefs.get("refresh_mode", "hybrid"))
        if idx >= 0:
            self._refresh_combo.setCurrentIndex(idx)


class LayerManagerUI(QWidget):

    """
    LayerManagerUI class for visualizing and managing layer channel in Nuke.

    This class provides an interactive interface to navigate between different layer sections,
    create nodes like LightGrade, Shuffle, Shuffle2, and Contribution with ease, and generate
    a contact sheet of available layers.

    Features:
    - Dynamic display of layers grouped into sections defined in preferences
    - Keyboard shortcuts for quick navigation and node creation
    - Mouse interactions (Ctrl+Click, Shift+Click) to trigger actions based on context
    - Automatic RGBA reset on closure
    - Built-in preferences dialog for customization
    - Contact sheet generation for the active section

    Sections:
    1. Light Layer
    2. Mask Layer
    3. Tech Layer
    4. Utility Layer
    5. Custom Layer (with customizable title)

    Node Creation Capabilities:
    - LightGrade: For layers in the Light Layer section
    - Shuffle2: For layers in Mask, Tech, and Utility sections
    - Contribution: For layers in the Custom Layer section

    The interface is designed to adapt to user actions and provides visual feedback through
    color changes and tooltips.
    """

    channelChanged =Signal(str)
    # Reconstruct active sections

    def __init__(self, parent=None):
        super(LayerManagerUI, self).__init__(parent)
        self.setObjectName("LayerManagerUI")

        self.setWindowTitle("Layer Manager")
        self.section_keywords = load_section_keywords()

        # Centralized disable states retrieval
        disables = self.get_section_disables()
        self.disable_light = disables["light"]
        self.disable_mask = disables["mask"]
        self.disable_utility = disables["utility"]
        self.disable_custom_layer = disables["custom"]

        # Build active section order
        self.section_index = get_active_sections(
            disables["light"],
            disables["mask"],
            disables["utility"],
            disables["custom"]
        )

        custom_title = self.section_keywords.get("custom Title", "Custom")
        self.sections = ["Light", "Mask", "Tech", "Utility", custom_title]

        # Opening section: first active section
        self.current_section = self.section_index[0] if self.section_index else 2  # fallback to Tech Layer

        self.mode = 'Artist' if self.disable_custom_layer else 'Lead'

        self.last_selected_layer = None
        self.last_light_layer = None
        self.has_custom_layers = False
        self.channelChanged.connect(self.set_channel)
        self.initUI()

        self._setup_focus_and_shortcuts_after_init()

        self.channel_list_widget.rowChanged.connect(self.update_viewer_channel)
        self.channel_list_widget.ctrlClicked.connect(self.handle_ctrl_click)
        self.channel_list_widget.shiftClicked.connect(self.handle_shift_click)
        self.channel_list_widget.keyPressed.connect(self.handle_keypress)
        
        self.channel_list_widget.leftPressed.connect(self.prev_section)
        self.channel_list_widget.rightPressed.connect(self.next_section)

        # ========================================================================
        # v2_39: Multi-Mode Refresh System with Robust Fallback
        # ========================================================================

        # === Multi-mode refresh variables ===
        self._refresh_mode = "hybrid"  # Default (event_driven, hybrid, focus_only)
        self._last_input_index = None
        self._viewer_input_timer = None  # Created in _setup_auto_refresh_with_fallback()
        self._viewer_callback_installed = False

        # === Polling variables (hybrid and focus_only modes) ===
        self._poll_interval = 500  # Active interval
        self._poll_interval_idle = 2000  # Idle mode interval
        self._poll_interval_deep = 10000  # Deep sleep interval
        self._idle_counter = 0
        self._max_idle_before_slow = 10  # Switch to idle after 10 x 500ms (5s)
        self._max_idle_deep = 30  # Switch to deep after 30 x 2s (60s)
        self._current_mode = "active"  # Polling state: active, idle, deep
        self._last_nuke_activity = time.time()

        # === Load mode from preferences ===
        self._load_refresh_mode_from_prefs()

        # === Initialize refresh system with robust fallback ===
        self._setup_auto_refresh_with_fallback()
 
        self.channels()
        self.update_section_label()
        
        self.show()

    def _setup_focus_and_shortcuts_after_init(self):
        """Configure focus and shortcuts based on docked/floating mode"""

        # Detect floating vs panel mode
        import inspect
        stack_info = [frame.filename for frame in inspect.stack()]
        called_from_panel = any('panels' in filename for filename in stack_info)
        
        has_parent = self.parent() is not None
        self._is_floating = not called_from_panel and not has_parent
        
        # If we have the Tool flag but came from panels, it's a panel
        if called_from_panel and bool(self.windowFlags() & Qt.Tool):
            self._is_floating = False

        # Configure focus policy for LayerSelector as well
        if hasattr(self, 'channel_list_widget'):
            if self._is_floating:
                self.channel_list_widget.setFocusPolicy(Qt.StrongFocus)
            else:
                self.channel_list_widget.setFocusPolicy(Qt.ClickFocus)

        # FIX: Create Up/Down shortcuts for ALL modes (docked and floating)
        # Up/Down must ALWAYS work
        self.shortcut_up = QShortcut(QKeySequence(Qt.Key_Up), self)
        self.shortcut_down = QShortcut(QKeySequence(Qt.Key_Down), self)
        self.shortcut_up.activated.connect(self.handle_up_key)
        self.shortcut_down.activated.connect(self.handle_down_key)
        dD_log.debug(f"Shortcuts Up/Down created (mode: {'floating' if self._is_floating else 'docked'})")

        if self._is_floating:  # Floating mode
            self.setFocusPolicy(Qt.StrongFocus)

            # Left/Right only in floating mode
            self.shortcut_left = QShortcut(QKeySequence(Qt.Key_Left), self)
            self.shortcut_right = QShortcut(QKeySequence(Qt.Key_Right), self)
            self.shortcut_left.activated.connect(self.handle_left_key)
            self.shortcut_right.activated.connect(self.handle_right_key)

        else:  # Panel/dock mode
            # Use ClickFocus to avoid automatic keyboard event capture
            self.setFocusPolicy(Qt.ClickFocus)
            # Ensure children don't intercept events either
            for child in self.findChildren(QWidget):
                if child != self.channel_list_widget:  # Keep the list focusable
                    child.setFocusPolicy(Qt.NoFocus)

            # Left/Right not created in docked mode (let Nuke handle)
            self.shortcut_left = None
            self.shortcut_right = None
    def handle_left_key(self):
        self.prev_section()
     
    def handle_right_key(self):
        self.next_section()
     
    def handle_up_key(self):
        dD_log.debug("handle_up_key called")
        current_row = self.channel_list_widget.currentRow()
        new_row = max(0, current_row - 1)
        dD_log.debug(f"Moving from row {current_row} to {new_row}")
        self.channel_list_widget.setCurrentRow(new_row)
        self.update_viewer_channel(new_row)

    def handle_down_key(self):
        dD_log.debug("handle_down_key called")
        current_row = self.channel_list_widget.currentRow()
        new_row = min(self.channel_list_widget.count() - 1, current_row + 1)
        dD_log.debug(f"Moving from row {current_row} to {new_row}")
        self.channel_list_widget.setCurrentRow(new_row)
        self.update_viewer_channel(new_row)

    def create_grade_aov_node(self):
        """
        Create a GradeAOV node for the selected layer.

        GradeAOV is an open source gizmo (vfxwiki/Nukepedia, BSD license)
        that applies a subtractive correction on an AOV layer:
        Grade / Saturation / Mask -- without affecting other layers.

        Install: https://github.com/vfxwiki/gradeAOV
        Alternative: Nuke Survival Toolkit (NST) includes GradeAOV.
        """
        selected_layer = self.get_selected_channel()

        try:
            node = nuke.createNode("GradeAOV")
        except Exception:
            nuke.message(
                "GradeAOV gizmo not found.\n\n"
                "Install it from:\n"
                "  https://github.com/vfxwiki/gradeAOV\n\n"
                "Or via Nuke Survival Toolkit (NST).\n\n"
                "Once installed, place GradeAOV.nk in your ~/.nuke/ folder\n"
                "and add:  nuke.pluginAddPath('~/.nuke')  to your init.py"
            )
            return None

        if selected_layer and node:
            try:
                if node.knob("aov_layer"):
                    node["aov_layer"].setValue(selected_layer)
                elif node.knob("layer"):
                    node["layer"].setValue(selected_layer)
            except Exception as e:
                dD_log.info(f"GradeAOV: cannot set layer: {e}")

        return node

    def initUI(self):
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # === RGBA and refresh Buttons ===
        self.rgba_layout = QHBoxLayout()

        # contact sheet
        self.contact_button = QPushButton()
        self.contact_button.setFixedSize(25,25)
        self.contact_button.setFlat(True)
        self.contact_button.setStyleSheet("border: none;")
        self.contact_button.setIcon(QIcon(os.path.join(ICONS_DIR, ICON_CONTACT_1)))
        self.contact_button.clicked.connect(self.create_layer_contact_sheet)
        self.contact_button.setToolTip('Create a LayerContactSheet for the current section layers')


        # rgba
        self.rgba_button = QPushButton('RGBA')
        self.rgba_button.clicked.connect(self.reset_rgba_ui)
        self.rgba_button.setToolTip('Click to set the layer to RGBA')
        # refresh v2_37 - Permanent auto-refresh in background + button for forced refresh
        self.refresh_button = QPushButton()
        self.refresh_button.setFixedSize(25, 25)
        self.refresh_button.setFlat(True)
        self.refresh_button.setStyleSheet("border: none; background: transparent;")
        self.refresh_button.setIcon(QIcon(os.path.join(ICONS_DIR, ICON_REFRESH)))

        # Click: immediate forced refresh
        self.refresh_button.clicked.connect(lambda: self.channels())

        # Tooltip
        self.refresh_button.setToolTip(
            'Manual refresh (auto-refresh runs in background)\n'
            'Click to force refresh layers now'
        )

        self.rgba_layout.addWidget(self.contact_button)
        self.rgba_layout.addWidget(self.rgba_button)
        self.rgba_layout.addWidget(self.refresh_button)
        self.layout.addLayout(self.rgba_layout)

        # ======= Frame for managing layers =======
        frame = QtWidgets.QFrame()
        frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        frame.setStyleSheet("QFrame { border: none; }")




        # Main frame layout
        frame_layout = QtWidgets.QVBoxLayout(frame)

        # === WordWheel-style ===
        self.wordwheel_layout = QtWidgets.QHBoxLayout()

        self.select_channel_label = QLabel('Select Layer')
        self.select_channel_label.setToolTip('This label shows the current section')

        # Add wordwheel
        self.wordwheel_layout.addWidget(self.select_channel_label)
        frame_layout.addLayout(self.wordwheel_layout)

        # Initialize wordwheel
        self.update_wordwheel()

        # === Buttons ← → ===
        self.nav_layout = QtWidgets.QHBoxLayout()

        # Load icons once
        self.icon_prev_normal = QIcon(os.path.join(ICONS_DIR, ICON_PREV_NORMAL))
        self.icon_prev_orange = QIcon(os.path.join(ICONS_DIR, ICON_PREV_ORANGE))
        self.icon_next_normal = QIcon(os.path.join(ICONS_DIR, ICON_NEXT_NORMAL))
        self.icon_next_orange = QIcon(os.path.join(ICONS_DIR, ICON_NEXT_ORANGE))

        # Prev button
        self.prev_button = QPushButton()
        self.prev_button.setFlat(True)
        self.prev_button.setStyleSheet("border: none;")
        self.prev_button.setIcon(self.icon_prev_normal)
        self.prev_button.setIconSize(QSize(75, 18))

        # Next button
        self.next_button = QPushButton()
        self.next_button.setFlat(True)
        self.next_button.setStyleSheet("border: none;")
        self.next_button.setIcon(self.icon_next_normal)
        self.next_button.setIconSize(QSize(75, 18))

        # Add 2 buttons
        self.nav_layout.addStretch()
        self.nav_layout.addWidget(self.prev_button)
        self.nav_layout.addWidget(self.next_button)
        self.nav_layout.addStretch()

        # Add nav layout in frame layout
        frame_layout.addLayout(self.nav_layout)

        # Link buttons
        self.prev_button.clicked.connect(self.prev_section)
        self.next_button.clicked.connect(self.next_section)

        # Add frame in main layout
        self.layout.addWidget(frame)

        # # === Layer list ===
        # self.layout.addWidget(self.select_channel_label)
        self.channel_list_widget = LayerSelector()
        self.channel_list_widget.setStyleSheet(
            "QListWidget::item { color: {DEFAULT_TEXT_COLOR}; }"
            "QListWidget::item:selected { background: {HIGHLIGHT_COLOR}; color: black; }")
        self.channel_list_widget.setSelectionMode(QListWidget.SingleSelection)
        self.channel_list_widget.itemClicked.connect(self.itemClicked)
        self.channel_list_widget.itemSelectionChanged.connect(self.update_lightgrade_button_state)
        self.channel_list_widget.setToolTip('List of available layers')
        self.layout.addWidget(self.channel_list_widget)

        # === Action buttons (GradeAOV, LightGrade, Shuffle) ===

        self.single_action_layout = QVBoxLayout()
        self.action_buttons_layout = QHBoxLayout()
        # self.action2_buttons_layout = QHBoxLayout()


        # Initialize buttons
        self.grade_aov_button = QPushButton("Grade AOV")
        self.grade_aov_button.setToolTip(
            "Create a GradeAOV node for the selected layer\n"
            "Requires: GradeAOV gizmo (Nukepedia / Nuke Survival Toolkit)"
        )
        self.grade_aov_button.clicked.connect(self.create_grade_aov_node)
        self.grade_aov_button.setVisible(False)


        self.create_grade_button = QPushButton("Light Grade")
        self.create_grade_button.setToolTip("Create a Light LightGrade with the selected light layer")
        self.layer_selected = None
        self.create_grade_button.clicked.connect(self.run_lightgrade)
        self.create_grade_button.setVisible(False)

        self.add_layer_button = QPushButton('Add Layer')
        self.add_layer_button.setToolTip('Add a layer to the current LightGrade')
        self.add_layer_button.clicked.connect(
            lambda: self.add_layer_to_lightgrade(self.channel_list_widget.currentItem()))
        self.add_layer_button.setVisible(True)
        
        self.action_shuffle_button = QPushButton("Shuffle")
        self.action_shuffle_button.setToolTip("Create Shuffle for selected layer\nor Ctrl+Click on selected layer")
        self.action_shuffle_button.clicked.connect(self.handle_action_button)
        self.action_shuffle_button.setVisible(True)

        # Add to layouts
        self.single_action_layout.addWidget(self.grade_aov_button)
        self.action_buttons_layout.addWidget(self.create_grade_button)
        self.action_buttons_layout.addWidget(self.add_layer_button)
        self.single_action_layout.addLayout(self.action_buttons_layout)
        self.single_action_layout.addWidget(self.action_shuffle_button)


        self.layout.addLayout(self.single_action_layout)

        # # === Separators ===
        # line5 = QFrame()
        # line5.setFrameShape(QFrame.HLine)
        # line5.setFrameShadow(QFrame.Sunken)
        # line5.setToolTip('Second separator line')
        # self.layout.addWidget(line5)

        # # === Refresh Button ===
        # self.refresh_button = QPushButton('Refresh')
        # self.refresh_button.clicked.connect(lambda: self.channels())
        # self.refresh_button.setToolTip('Refresh the list of layers')
        # self.layout.addWidget(self.refresh_button)



        # === Contact Sheet ===
        # self.contact_sheet_button = QPushButton('Create Contact Sheet')
        # self.contact_sheet_button.clicked.connect(self.create_layer_contact_sheet)
        # self.contact_sheet_button.setToolTip('Create a LayerContactSheet for the current section layers')
        # self.layout.addWidget(self.contact_sheet_button)

        # === Credits ===
        credits_line = QFrame()
        credits_line.setFrameShape(QFrame.HLine)
        credits_line.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(credits_line)

        # === Settings Button + Credits Layout ===
        credits_layout = QHBoxLayout()

        # Settings button (left) - Square button with icon only
        self.settings_btn = QPushButton()
        self.settings_btn.setFixedSize(18, 18)

        # Load setting.png icon
        settings_icon_path = os.path.join(ICONS_DIR, ICON_SETTINGS)
        if os.path.exists(settings_icon_path):
            settings_icon = QIcon(settings_icon_path)
            self.settings_btn.setIcon(settings_icon)
            self.settings_btn.setIconSize(QSize(14, 14))
        else:
            # Fallback if icon does not exist
            self.settings_btn.setText("S")

        # Blue square button style
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background: #1C77C3;
                border: 1px solid #1565B0;
                border-radius: 3px;
                color: white;
            }
            QPushButton:hover {
                background: #1E88D5;
            }
            QPushButton:pressed {
                background: #1565B0;
            }
        """)
        self.settings_btn.setToolTip("Open Layer Manager Preferences (Nuke Preferences > Layer Manager)")
        self.settings_btn.clicked.connect(self._open_layermanager_preferences)

        # Credits label (right)
        credits_label = QLabel()
        credits_label.setText(credit())
        credits_label.setTextFormat(Qt.RichText)
        credits_label.setOpenExternalLinks(False)  # handle opening ourselves
        credits_label.linkActivated.connect(
            lambda url: (open_layermanager_help() if url == HELP_LINK or "AgBG_w" in url
                         else QDesktopServices.openUrl(QUrl(url)))
        )
        credits_label.setStyleSheet("font-size: 12px; color: #bbbbbb;")

        # Add to layout
        credits_layout.addStretch()
        credits_layout.addWidget(self.settings_btn)
        credits_layout.addWidget(credits_label)
        credits_layout.addStretch()

        self.layout.addLayout(credits_layout)

        self.setWindowTitle('Layer Manager')
        self.resize(260, 600)
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        # self.setWindowFlags(Qt.Widget)

        screen_geometry = QApplication.desktop().screenGeometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
        
        #self.channels()
        #self.update_section_label()
        #self.show()

    def get_section_disables(self):
        return {
            "light": self.section_keywords.get("disable Light Layer", False),
            "mask": self.section_keywords.get("disable Mask Layer", False),
            "utility": self.section_keywords.get("disable Utility Layer", False),
            "custom": self.section_keywords.get("disable Custom Layer", True)
        }

    def update_wordwheel(self):
        # Clear previous layout
        while self.wordwheel_layout.count():
            item = self.wordwheel_layout.takeAt(0)
            widget = item.widget()
            if widget:
                if widget is self.select_channel_label:
                    continue  # Do not delete the main label!
                widget.deleteLater()

        if not self.section_index:
            return

        current_index = self.section_index.index(self.current_section)
        total = len(self.section_index)

        for i in range(-2, 3):
            idx = (current_index + i) % total
            section_value = self.section_index[idx]
            word = self.sections[section_value]

            container = QtWidgets.QWidget()
            vbox = QtWidgets.QVBoxLayout(container)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(0)

            label = QtWidgets.QLabel()
            label.setAlignment(Qt.AlignCenter| Qt.AlignCenter)

            if i == 0:
                label.setText(
                    f"<span style='color:#FCB132;'> {word} </span><br><span style='color:white;'>Layer</span>")
                label.setStyleSheet("font-weight: 900; font-size: 16px;")
                label.setTextFormat(Qt.RichText)
                vbox.addSpacing(6)
            else:
                label.setText(word)
                label.setAlignment(Qt.AlignTop | Qt.AlignCenter)
                if abs(i) == 1:
                    label.setStyleSheet("color: gray; font-size: 12px;")
                    vbox.addSpacing(6)
                else:
                    label.setStyleSheet("color: gray; font-size: 8px;")
                    vbox.addSpacing(14)

            vbox.addWidget(label)
            self.wordwheel_layout.addWidget(container)

    def prev_section(self):
        disables = self.get_section_disables()
        self.section_index = get_active_sections(**disables)

        current_index = self.section_index.index(self.current_section)
        prev_index = (current_index - 1) % len(self.section_index)
        self.current_section = self.section_index[prev_index]

        self.channels()
        self.update_wordwheel()
        self.update_section_label()
        # Debug if switching to custom section
        if self.current_section == 4:
            self.get_custom_section_analytics()

    def next_section(self):
        disables = self.get_section_disables()
        self.section_index = get_active_sections(**disables)

        current_index = self.section_index.index(self.current_section)
        next_index = (current_index + 1) % len(self.section_index)
        self.current_section = self.section_index[next_index]

        self.channels()
        self.update_wordwheel()
        self.update_section_label()
        # Debug if switching to custom section
        if self.current_section == 4:
            self.get_custom_section_analytics()

    def sync_preferences_from_nuke(self):
        # Reload from Nuke prefs
        self.section_keywords = load_section_keywords()

        # Update active sections and display
        disables = self.get_section_disables()
        self.disable_light = disables["disable_light"]
        self.disable_mask = disables["disable_mask"]
        self.disable_utility = disables["disable_utility"]
        self.disable_custom_layer = disables["disable_custom"]

        self.mode = 'Artist' if self.disable_custom_layer else 'Lead'

        # Update visually
        self.channels()
        self.update_section_label()

    def reset_rgba_ui(self):
        """Reset the Viewer to RGBA and clean the entire UI"""
        self.set_channel("rgba")
        self.reset_list_item_styles()
        self.channel_list_widget.clearSelection()
        self.channel_list_widget.setCurrentRow(-1)
        self.rgba_button.setStyleSheet("color: #FCB132; font-weight: bold;")

    def load_section_keywords(self):
        """Returns centralized default values"""
        return get_default_keywords()

    def get_current_user_name(self):
        return os.getenv('USER') or os.getenv('USERNAME') or 'unknown_user'

    def update_layer_selection(self, layer_name):
        self.last_selected_layer = layer_name
        if layer_name.startswith("CONT_specular_direct_"):
            self.last_light_layer = layer_name.replace("CONT_specular_direct_", "RGBA_")
        elif layer_name.startswith("CONT_specular_indirect_"):
            self.last_light_layer = layer_name.replace("CONT_specular_indirect_", "RGBA_")
        else:
            self.last_light_layer = None

    def update_lightgrade_button_state(self):
        if self.current_section != 0:
            self.create_grade_button.setEnabled(False)
            return

        selected_item = self.channel_list_widget.currentItem()
        has_valid_layer = selected_item is not None and selected_item.text().strip() != ""
        self.create_grade_button.setEnabled(has_valid_layer)


    def create_Shuffle2(self, item):
        try:
            node = get_last_selected_node()
            if node is None:
                nuke.message("No relevant node found to place the Shuffle2 node next to.")
                return
     
            shuffle2_node = nuke.nodes.Shuffle2(inputs=[])
            shuffle2_node.setInput(0, node)
            shuffle2_node.setXpos(int(node.xpos() + node.screenWidth() + 50))
            shuffle2_node.setYpos(node.ypos())
     
            shuffle2_node['in1'].setValue(item.text())
            shuffle2_node['label'].setValue(item.text())
     
            # Get the channels available for this layer
            all_channels = nuke.channels()
            available_channels = [ch for ch in all_channels if ch.startswith(item.text())]

            # Configure mappings according to the available channels
            mappings = []
            if item.text() == 'motion':
                mappings = [(0, 'forward.u', 'rgba.red'), (0, 'forward.v', 'rgba.green'),
                            (0, 'backward.u', 'rgba.blue'), (0, 'backward.v', 'rgba.alpha')]
            elif item.text() == 'N':
                mappings = [(0, 'N.X', 'rgba.red'), (0, 'N.Y', 'rgba.green'), (0, 'N.Z', 'rgba.blue'),
                            (-1, 'black', 'rgba.alpha')]
            elif item.text() == 'N_filter':
                mappings = [(0, 'N_filter.X', 'rgba.red'), (0, 'N_filter.Y', 'rgba.green'),
                            (0, 'N_filter.Z', 'rgba.blue'),
                            (-1, 'black', 'rgba.alpha')]
            elif item.text() == 'P':
                mappings = [(0, 'P.X', 'rgba.red'), (0, 'P.Y', 'rgba.green'), (0, 'P.Z', 'rgba.blue'),
                            (-1, 'black', 'rgba.alpha')]
            elif item.text() == 'P_filter':
                mappings = [(0, 'P_filter.X', 'rgba.red'), (0, 'P_filter.Y', 'rgba.green'),
                            (0, 'P_filter.Z', 'rgba.blue'),
                            (-1, 'black', 'rgba.alpha')]
            elif item.text() == 'depth':
                mappings = [(0, 'depth.Z', 'rgba.red'),
                            (-1, 'black', 'rgba.green'),
                            (-1, 'black', 'rgba.blue'),
                            (-1, 'black', 'rgba.alpha')]

            elif item.text() == 'rfx_depth':
                mappings = [(0, 'rfx_depth.Z', 'rgba.red'), (-1, 'black', 'rgba.green'),
                            (-1, 'black', 'rgba.blue'),
                            (-1, 'black', 'rgba.alpha')]
            elif item.text() == 'other':
                mappings = [(0, 'other.caustic', 'rgba.red'), (-1, 'other.glint', 'rgba.green'),
                            (-1, 'other.rfx_depth', 'rgba.blue'),
                            (-1, 'black', 'rgba.alpha')]

            else:
                # For other layers, map the RGBA channels generic
                channel_map = {'red': 'red', 'green': 'green', 'blue': 'blue', 'alpha': 'alpha'}
                for channel in ['red', 'green', 'blue', 'alpha']:
                    input_channel = f'{item.text()}.{channel}'
                    if input_channel in available_channels:
                        output_channel = f'rgba.{channel_map[channel]}'
                        mappings.append((0, input_channel, output_channel))

                # If no classic RGBA mapping found, try intelligent fallback
                # No classic RGBA mapping -> try .x .y .z
                if not mappings:
                    # Fallback 1 : .x, .y, .z
                    suffixes = ['.x', '.y', '.z']
                    found_xyz = [f"{item.text()}{sfx}" for sfx in suffixes if
                                 f"{item.text()}{sfx}" in available_channels]

                    if len(found_xyz) >= 3:
                        mappings.append((0, found_xyz[0], 'rgba.red'))
                        mappings.append((0, found_xyz[1], 'rgba.green'))
                        mappings.append((0, found_xyz[2], 'rgba.blue'))
                        mappings.append((-1, 'black', 'rgba.alpha'))

                    else:
                        # Fallback 2: subchannels (e.g. deep.front, deep.back)
                        subchannels = [c for c in available_channels if c.startswith(f"{item.text()}.")]
                        if subchannels:
                            if len(subchannels) >= 2:
                                mappings.append((0, subchannels[0], 'rgba.red'))
                                mappings.append((0, subchannels[1], 'rgba.green'))
                            else:
                                mappings.append((0, subchannels[0], 'rgba.red'))
                                mappings.append((-1, 'black', 'rgba.green'))
                            mappings.append((-1, 'black', 'rgba.blue'))
                            mappings.append((-1, 'black', 'rgba.alpha'))

            if mappings:
                shuffle2_node['mappings'].setValue(mappings)

                importlib.reload(shuffle)
                shuffle.run()
            else:
                nuke.delete(shuffle2_node)
                nuke.message("No valid channel mapping could be determined.")

        except Exception as e:
            tb = sys.exc_info()[2]
            lineno = traceback.extract_tb(tb)[-1].lineno
            nuke.message(f"Error creating Shuffle2 node: {str(e)}\nline : {lineno}")


    def run_lightgrade(self):
        selected_layer = self.get_selected_channel()
        if not selected_layer:
            nuke.message("Please select a layer first.")
            return

        try:
            create_lightgrade(selected_layer)
            self.add_layer_button.setEnabled(True)
        except RuntimeError as e:
            # FIX: If 'lightgrade' gizmo not found, fallback to Group
            if "Unknown command" in str(e):
                nuke.message(
                    "LightGrade gizmo not found.\n\n"
                    "Possible causes:\n"
                    "1. Gizmo path not configured in menu.py\n"
                    "2. Gizmo file missing in /gizmos/\n"
                    "3. Wrong gizmo name in lightgrade_module_v2_54.py\n\n"
                    f"Error: {str(e)}"
                )
            else:
                raise


    def add_layer_to_lightgrade(self, item=None):

        # Find the active node
        node = get_active_lightgrade_node()
        if not node:
            try:
                viewer = nuke.activeViewer()
                input_index = viewer.activeInput()
                viewer_node = viewer.node()
                current_node = viewer_node.input(input_index)

                visited = set()
                while current_node and current_node not in visited:
                    visited.add(current_node)
                    if current_node.Class() == "Group" and current_node.name().startswith("dD_lightgrade"):
                        node = current_node
                        break
                    current_node = current_node.input(0)
            except Exception:
                pass

        if not node:
            nuke.message("No LightGrade node found or selected.")
            return

        # Selected layer
        layer = item.text() if item else self.get_selected_channel()
        if not layer:
            nuke.message("Please select a layer first.")
            return

        # Call the actual function
        add_layer_to_lightgrade(node, layer)

    def Ctrl_Click(self, item):
        if self.current_section in [0]:
            create_lightgrade()
        elif self.current_section in [1, 2, 3]:
            self.create_Shuffle2(item)
        elif self.current_section in [4]:
            self.create_contribution(item)

    def handle_ctrl_click(self, item):
        """Create a shuffle2 with Ctrl + Click on a Channel Layer."""
        self.create_Shuffle2(item)

    def create_contribution(self, item):
        """
        Create a Shuffle2 node for contribution layers (Custom Layer section).
        This is essentially the same as create_Shuffle2 but specifically for custom layers.
        """
        if not item:
            nuke.message("Please select a layer first.")
            return
        # Use the same logic as create_Shuffle2
        self.create_Shuffle2(item)

    def handle_shift_click(self, item):
        """
        Action activated by Shift+Click.
        - Section 0 : Create LightGrade.
        - Section 4 : Create contribution.
        """
        try:
            if self.current_section == 0:
                self.create_grade_aov_node()
        except Exception as e:
            nuke.message(f"Error handling Shift+Click: {str(e)}")

    def handle_shift_ctrl_click(self, item):
        """Action activated by Shift+Ctrl+Click to add a layer to the selected LightGrade."""
        pass

    def handle_keypress(self, key):
        selected_item = self.channel_list_widget.currentItem()

        if key == Qt.Key_H:
            if self.current_section in [0, 1, 2, 3, 4]:
                if selected_item:
                    self.create_Shuffle2(selected_item)

        elif key == Qt.Key_O:
            nuke.createNode("Roto")

        elif key == Qt.Key_P:
            nuke.createNode("Cryptomatte")

        elif key == Qt.Key_L and self.current_section == 0:
            if STUDIO_MODE:
                pass
            else:
                self.create_grade_aov_node()

        elif key == Qt.Key_G and self.current_section == 0:
            if STUDIO_MODE:
                pass
            else:
                self.run_lightgrade()

        elif key == Qt.Key_A and self.current_section == 0:
            if STUDIO_MODE:
                return
            if not selected_item:
                nuke.message("Please select a layer first.")
                return

            # Check that a LightGrade is selected
            has_lightgrade_node = any(
                n.Class() == "Group" and n.name().startswith("dD_lightgrade")
                for n in nuke.selectedNodes()
            )
            if not has_lightgrade_node:
                nuke.message("Please select a LightGrade node before adding a layer.")
                return

            # All good, proceed
            self.add_layer_to_lightgrade(selected_item)

    def handle_action_button(self):
        selected_item = self.channel_list_widget.currentItem()

        if selected_item:
            if self.current_section in [0, 1, 2, 3, 4]:
                self.create_Shuffle2(selected_item)
            # elif self.current_section == 4:
            #     self.create_contribution(selected_item)

    def hide_knobs(self, node):
        for i in range(2, 9):
            for suffix in ['in', 'disable', 'solo']:
                knob_name = f"aov_in{i}_{suffix}"
                if knob_name in node.knobs():
                    try:
                        node.knobs()[knob_name].setVisible(False)
                    except Exception as e:
                        pass

    def reveal_knobs(self, node, knob_names):
        for name in knob_names:
            if name in node.knobs():
                knob = node.knobs()[name]
                knob.setVisible(True)
                if hasattr(knob, "flags"):
                    knob.clearFlag(nuke.INVISIBLE)

    def create_layer_contact_sheet(self):
        try:
            group = nuke.thisGroup()
            if group is None:
                group = nuke.root()

            with group:
                layers = []
                section_name = self.getSectionText()

                for index in range(self.channel_list_widget.count()):
                    item = self.channel_list_widget.item(index)
                    if item and item.text() and item.text() != "!!! Layer Empty !!!":
                        layers.append(item.text())

                if not layers:
                    nuke.message('No valid layers found to create LayerContactSheet.')
                    return

                # Determine source node for insertion (selection or viewer input)
                selected_nodes = nuke.selectedNodes()
                if selected_nodes:
                    input_node_for_group = selected_nodes[-1]
                else:
                    viewer = nuke.activeViewer()
                    viewer_node = viewer.node() if viewer else None
                    input_index = viewer.activeInput() if viewer else None
                    input_node_for_group = viewer_node.input(
                        input_index) if viewer_node and input_index is not None else None

                group_name = "{} ContactSheet".format(section_name)

                group_node = insert_node_below_visually(
                    node_class='Group',
                    original_node=input_node_for_group,
                    node_name=group_name
                )

                if group_node is None:
                    nuke.message("Unable to create/insert the Contact Sheet (no valid input).")
                    return

                group_node['tile_color'].setValue(4278190335)

                group_node.begin()

                input_node = nuke.createNode('Input', inpanel=False)
                input_dot = nuke.createNode('Dot', inpanel=False)
                input_dot.setInput(0, input_node)
                input_dot.setYpos(input_dot.ypos() - 50)

                shuffle_nodes = []
                text_nodes = []
                crop_nodes = []
                grid_nodes = []

                xpos_start = input_dot.xpos() - (80 * len(layers) // 2)

                for i, layer in enumerate(layers):
                    shuffle_node = nuke.createNode('Shuffle', inpanel=False)
                    shuffle_node['in'].setValue(layer)
                    shuffle_node['label'].setValue(layer)
                    shuffle_node.setInput(0, input_dot)

                    xpos = xpos_start + (i * 80)
                    shuffle_node.setXpos(xpos)
                    shuffle_node.setYpos(input_dot.ypos() + 100)
                    shuffle_nodes.append(shuffle_node)

                    crop_node = nuke.createNode('Crop', inpanel=False)
                    crop_node['box'].setValue([-14, -70, 2012, 1090])
                    crop_node['reformat'].setValue(True)
                    crop_node.setInput(0, shuffle_node)

                    crop_node.setXpos(xpos)
                    crop_node.setYpos(shuffle_node.ypos() + 50)
                    crop_nodes.append(crop_node)

                    grid_node = nuke.createNode('Grid', inpanel=False)
                    grid_node['number'].setValue(1)
                    grid_node['size'].setValue(4)
                    grid_node.setInput(0, crop_node)

                    grid_node.setXpos(xpos)
                    grid_node.setYpos(crop_node.ypos() + 100)
                    grid_nodes.append(grid_node)

                    text_node = nuke.createNode('Text', inpanel=False)
                    text_node['message'].setValue(layer)
                    text_node['box'].setValue([0, 0, 1998, 1080])
                    text_node['xjustify'].setValue('center')
                    text_node['yjustify'].setValue('bottom')
                    text_node.setInput(0, grid_node)

                    text_node.setXpos(xpos)
                    text_node.setYpos(grid_node.ypos() + 100)
                    text_nodes.append(text_node)

                num_layers = len(layers)
                rows = int(math.floor(math.sqrt(num_layers)))
                columns = int(math.ceil(num_layers / rows))

                contact_sheet_node = nuke.createNode('ContactSheet', inpanel=False)
                contact_sheet_node['width'].setValue(1998)
                contact_sheet_node['height'].setValue(1080)
                contact_sheet_node['rows'].setValue(rows)
                contact_sheet_node['columns'].setValue(columns)
                contact_sheet_node['center'].setValue(True)
                contact_sheet_node['roworder'].setValue('TopBottom')
                contact_sheet_node['gap'].setValue(8)

                for i, text_node in enumerate(text_nodes):
                    contact_sheet_node.setInput(i, text_node)

                contact_sheet_node.setXpos(input_dot.xpos())
                contact_sheet_node.setYpos(text_nodes[0].ypos() + 200)

                output_node = nuke.createNode('Output', inpanel=False)
                output_node.setInput(0, contact_sheet_node)

                group_node.end()

                # Connect viewer to the group
                viewer_nodes = nuke.allNodes('Viewer')
                if viewer_nodes:
                    viewer_node = viewer_nodes[0]
                    viewer_node.setInput(0, group_node)

                self.set_channel('rgba')

        except Exception as e:
            nuke.message(f"Error creating LayerContactSheet: {str(e)}")



    def get_selected_channel(self):
        """Retrieves the layer currently selected from the list."""
        selected_item = self.channel_list_widget.currentItem()
        if selected_item:
            return selected_item.text()
        else:
            return None

    # --- Update button display and section title ---
    def update_section_label(self):
        custom_title = self.section_keywords.get("custom Title", "custom Layer")
        if not isinstance(custom_title, str):
            custom_title = "custom Layer"
        custom_title = custom_title.strip() or "custom"
     
        titles = {0: "Light", 1: "Mask", 2: "Tech", 3: "Utility", 4: custom_title}
        title_text = titles.get(self.current_section, "Unknown")
        html_title = f'<p align="center" style="font-size: 16px; font-weight: bold; color: #FCB132; margin: 0;">{title_text} <span style="color: #FFFFFF;">Layer</span></p>'
        self.select_channel_label.setText(html_title)
     
        self.grade_aov_button.setVisible(False)
        self.create_grade_button.setVisible(False)
        self.add_layer_button.setVisible(False)
        self.action_shuffle_button.setVisible(False)

        if self.current_section == 0:
            self.create_grade_button.setVisible(True)
            self.add_layer_button.setVisible(True)
            self.action_shuffle_button.setVisible(True)
        elif self.current_section in {1, 2, 3, 4}:
            self.action_shuffle_button.setVisible(True)

        has_lightgrade_node = any(
            n.Class() == "Group" and n.name().startswith("lightgrade")
            for n in nuke.selectedNodes()
        )
        self.add_layer_button.setEnabled(has_lightgrade_node)

        # self.action_buttons_layout.addWidget(self.add_layer_button)
        #
        # vbox.addLayout(self.action_buttons_layout)
        # self.single_action_layout.addLayout(vbox)

        # self.prev_button.setText('← prev.')
        # self.next_button.setText('next →')
        self.channels()
        self.update_lightgrade_button_state()

    def channels(self):
        self.channel_list_widget.clear()

        try:
            viewer_node = nuke.activeViewer().node()
            input_index = nuke.activeViewer().activeInput()
            if viewer_node is None or input_index is None:
                raise ValueError("Viewer or input index not available")

            source_node = viewer_node.input(input_index)
            if source_node is None:
                raise ValueError("Viewer input not connected")

            all_layers = list(set([layer.split('.')[0] for layer in source_node.channels()]))

        except Exception:
            pass
            all_layers = []

        filtered_layers = self.get_filtered_layers(all_layers)

        if not filtered_layers:
            for _ in range(4):
                empty_item = QListWidgetItem("")
                self.channel_list_widget.addItem(empty_item)

            empty_item = QListWidgetItem("!!! Layer Empty !!!")
            empty_item.setTextAlignment(Qt.AlignCenter)
            font = empty_item.font()
            font.setBold(True)
            empty_item.setFont(font)
            self.channel_list_widget.addItem(empty_item)

            # Keep the button on even if the list is empty
            if self.action_shuffle_button:
                self.action_shuffle_button.setEnabled(True)

            self.channel_list_widget.is_empty_layer_present = True
            return

        for layer in filtered_layers:
            item = QListWidgetItem(layer)
            self.channel_list_widget.addItem(item)

        if self.action_shuffle_button:
            self.action_shuffle_button.setEnabled(True)

        self.channel_list_widget.is_empty_layer_present = False

        has_lightgrade_node = any(
            n.Class() == "Group" and n.name().startswith("lightgrade")
            for n in nuke.selectedNodes()
        )
        self.add_layer_button.setEnabled(has_lightgrade_node)

    def get_filtered_layers(self, all_layers):
        """Keep the button on even if the list is empty"""
        keywords = self.section_keywords
        exclusion_keywords = keywords.get("Exclusion Keywords", [])

        # Exclude layers containing exclusion keywords
        filtered_layers = [layer for layer in all_layers if not any(kw in layer for kw in exclusion_keywords)]

        # Function to get the main prefix of a layer (up to the next '_' or '-')
        def get_prefix(layer):
            import re
            if '_' in layer:
                base = layer.split('_')[0]
            elif '-' in layer:
                base = layer.split('-')[0]
            else:
                base = layer
            # Remove numeric suffixes: "lgt01" -> "lgt", "rgb1" -> "rgb"
            stripped = re.sub(r'\d+$', '', base)
            return stripped if stripped else base

        # Function to check if a layer exactly matches a keyword or prefix
        def matches_keyword(layer, section_keywords):
            layer_l = layer.lower()
            prefix_l = get_prefix(layer).lower()

            for kw in section_keywords:
                kw_l = kw.lower().strip()
                if not kw_l:
                    continue
                # Wildcard support: "lg_*" matches "lg_fill", "lgt*" matches "lgt01"
                if '*' in kw_l:
                    if fnmatch.fnmatch(layer_l, kw_l):
                        return True
                elif len(kw_l) == 1:
                    if layer_l == kw_l or prefix_l == kw_l:
                        return True
                else:
                    if prefix_l == kw_l or kw_l in layer_l:
                        return True
            return False

        def get_match_priority(layer, section_keywords):
            prefix = get_prefix(layer)
            for i, kw in enumerate(section_keywords):
                if layer == kw:
                    return i  # highest priority
            for i, kw in enumerate(section_keywords):
                if prefix == kw:
                    return i  # medium priority
            for i, kw in enumerate(section_keywords):
                if kw in layer:
                    return i  # low priority
            return len(section_keywords)  # not found


        # Prioritize keywords "custom Layer"
        custom_layers = [layer for layer in filtered_layers if matches_keyword(layer, keywords["custom Layer"])]
        filtered_layers = [layer for layer in filtered_layers if layer not in custom_layers]

        # Debug custom layers if found
        if custom_layers and self.current_section == 4:
            self._debug_custom_layers_found(custom_layers)

        # Filtering for each remaining section
        light_layers_raw = [layer for layer in filtered_layers if matches_keyword(layer, keywords["Light Layer"])]

        # Sorting entirely driven by keyword order in preferences
        light_kws = keywords["Light Layer"]

        def get_sort_key(layer):
            """Returns the position of the first matching keyword (= priority)"""
            layer_l = layer.lower()
            prefix_l = get_prefix(layer).lower()
            for i, kw in enumerate(light_kws):
                kw_l = kw.lower().strip()
                if not kw_l:
                    continue
                if '*' in kw_l:
                    if fnmatch.fnmatch(layer_l, kw_l):
                        return (i, layer_l)
                elif len(kw_l) == 1:
                    if layer_l == kw_l or prefix_l == kw_l:
                        return (i, layer_l)
                else:
                    if prefix_l == kw_l or kw_l in layer_l:
                        return (i, layer_l)
            return (len(light_kws), layer_l)  # fallback: end of list, alpha sort

        light_layers = sorted(light_layers_raw, key=get_sort_key)

        mask_layers = [layer for layer in filtered_layers if matches_keyword(layer, keywords["Mask Layer"])]
        tech_layers = []
        utils_layers = [layer for layer in filtered_layers if matches_keyword(layer, keywords["Utility Layer"])]

        # Identify unclassified layers and avoid duplicates
        classified_layers = set(light_layers + mask_layers + tech_layers + utils_layers + custom_layers)
        unclassified_layers = [layer for layer in filtered_layers if layer not in classified_layers]

        # Add unclassified layers to "Tech Layer"
        tech_layers += unclassified_layers

        # Remove duplicates in each section while preserving order



        def remove_duplicates_preserve_order(seq):
            seen = set()
            return [x for x in seq if not (x in seen or seen.add(x))]

        mask_layers = remove_duplicates_preserve_order(mask_layers)
        tech_layers = remove_duplicates_preserve_order(tech_layers)
        utils_layers = remove_duplicates_preserve_order(utils_layers)
        custom_layers = remove_duplicates_preserve_order(custom_layers)

        if self.current_section == 0:
            return light_layers

        elif self.current_section == 1:
            return sorted(mask_layers)
        elif self.current_section == 2:
            return sorted(tech_layers)
        elif self.current_section == 3:
            return sorted(utils_layers)
        elif self.current_section == 4:
            return sorted(custom_layers)
        return []


    def _debug_custom_layers_found(self, custom_layers):
        """Trace the custom layers found during filtering"""
        return {
            "custom_layers": custom_layers,
            "count": len(custom_layers),
            "keywords_used": self.section_keywords.get("custom Layer", []),
            "custom_title": self.section_keywords.get("custom Title", "Custom")
        }


    def get_custom_section_analytics(self, custom_layers=None):
        """Complete analysis of the custom section for debugging"""
        custom_title = self.section_keywords.get("custom Title", "Custom")
        custom_keywords = self.section_keywords.get("custom Layer", [])
        is_disabled = self.disable_custom_layer

        if custom_layers is not None:
            custom_layers_count = len(custom_layers)
            custom_layers_list = custom_layers
        else:
            custom_layers_count = self.channel_list_widget.count() if self.current_section == 4 else 0
            custom_layers_list = []
            if self.current_section == 4:
                for i in range(self.channel_list_widget.count()):
                    item = self.channel_list_widget.item(i)
                    if item and item.text() and item.text() != "!!! Layer Empty !!!":
                        custom_layers_list.append(item.text())

        analytics = {
            "custom_title": custom_title,
            "custom_keywords": custom_keywords,
            "is_disabled": is_disabled,
            "layers_count": custom_layers_count,
            "layers_list": custom_layers_list,
            "current_user": self.get_current_user_name(),
            "mode": self.mode
        }

        return analytics

    def print_current_section_layers(self):
        self.active_viewer = nuke.activeViewer().node()
        viewer = self.active_viewer
        input_index = nuke.activeViewer().activeInput() if nuke.activeViewer() else None
        viewer = viewer.input(input_index) if viewer and input_index is not None else None

        all_layers = list(set([layer.split('.')[0] for layer in viewer.channels()]))

        filtered_layers = self.get_filtered_layers(all_layers)

    def getSectionText(self):               # simplified nested if
        sections = ("Light Layer",
            "Mask Layer",
            "Tech Layer",
            "Utility Layer",
            self.section_keywords.get("custom Title", "custom Layer").strip() or "custom Layer"
        )
        return sections[self.current_section] if 0 <= self.current_section < len(sections) else ""

    def resetLabel(self):                   # simplified nested if
        sections = ("Light Layer", "Mask Layer", "Tech Layer", "Utility Layer")
        originalText = sections[self.current_section] if 0 <= self.current_section < len(sections) else ""
        self.select_channel_label.setStyleSheet(
            "QLabel { background-color: none; font-weight: bold; text-align: center; }")
        self.select_channel_label.setText(originalText)

    def keyPressEvent(self, event):
        current_row = self.channel_list_widget.currentRow()
        selected_item = self.channel_list_widget.currentItem()

        is_floating = getattr(self, '_is_floating', True)

        # Shortcut section 0 : G = create_GradeAOV
        if event.key() == Qt.Key_G and self.current_section == 0:
            dD_log.debug("Shortcut: G - Create Grade AOV")
            if selected_item:
                self.run_lightgrade()  # FIX: Use run_lightgrade instead of create_gradeaov

        # Shortcut  section 4 : G = create_contribution
        elif event.key() == Qt.Key_G and self.current_section == 4:
            dD_log.debug("Shortcut: G - Create contribution")
            if selected_item:
                self.create_contribution(selected_item)

        # Navigation Up/Down: ALWAYS allow (docked or floating mode)
        # FIX BUG: Up/Down must work even without active focus in docked mode
        elif event.key() == Qt.Key_Up:
            new_row = max(0, current_row - 1)
            self.channel_list_widget.setCurrentRow(new_row)
            self.update_viewer_channel(new_row)  # Refresh the viewer

        elif event.key() == Qt.Key_Down:
            new_row = min(self.channel_list_widget.count() - 1, current_row + 1)
            self.channel_list_widget.setCurrentRow(new_row)
            self.update_viewer_channel(new_row)  # Refresh the viewer

        # Navigation Left/Right: Only if focus is active (don't interfere with Nuke)
        elif event.key() == Qt.Key_Left:
            if is_floating or self.hasFocus() or self.channel_list_widget.hasFocus():
                self.prev_section()
            else:
                event.ignore()  # Let Nuke handle in docked mode without focus

        elif event.key() == Qt.Key_Right:
            if is_floating or self.hasFocus() or self.channel_list_widget.hasFocus():
                self.next_section()
            else:
                event.ignore()  # Let Nuke handle in docked mode without focus

        # Escape: Close window (floating) or return to RGBA (docked)
        elif event.key() == Qt.Key_Escape:
            if is_floating:
                self.close()
            else:
                # Docked mode: Return to RGBA + reset UI
                self.set_channel("rgba")
                self.reset_list_item_styles()
                self.channel_list_widget.clearSelection()
                self.channel_list_widget.setCurrentRow(-1)
                self.rgba_button.setStyleSheet("color: #FCB132; font-weight: bold;")

        else:
            QWidget.keyPressEvent(self, event)

    def focusInEvent(self, event):
        """Handle incoming focus"""
        if not getattr(self, '_is_floating', True):  # Docked mode
            # Transfer focus to the list to avoid intercepting global keys
            QTimer.singleShot(0, lambda: self.channel_list_widget.setFocus())
        QWidget.focusInEvent(self, event)

    def update_viewer_channel(self, row):
        dD_log.debug(f"update_viewer_channel called with row={row}")
        if row != -1:
            item = self.channel_list_widget.item(row)
            if item:
                layer_name = item.text()
                self.last_selected_layer = layer_name
                dD_log.debug(f"Setting viewer channel to: '{layer_name}'")
                nuke.executeInMainThread(self.set_channel, layer_name)

                # Reset RGBA button
                self.rgba_button.setStyleSheet("")

                # Revert to active orange style
                self.channel_list_widget.setStyleSheet("""
                QListWidget::item {
                    color: {DEFAULT_TEXT_COLOR};
                }
                QListWidget::item:selected {
                    background: {HIGHLIGHT_COLOR};
                    color: black;
                }
                """)
            else:
                dD_log.debug("No item found for the current row.")
        else:
            dD_log.debug("Invalid row index.")

    def set_channel(self, channel):
        try:
            dD_log.debug(f"set_channel called with: '{channel}'")
            viewer = nuke.activeViewer()
            if viewer:
                viewer_node = viewer.node()
                current_channel = viewer_node['channels'].value()
                dD_log.debug(f"Current viewer channel: '{current_channel}'")
                if current_channel != channel:
                    viewer_node['channels'].setValue(channel)
                    dD_log.debug(f"Viewer updated to channel: '{channel}'")
                else:
                    dD_log.debug(f"Viewer already set to channel: '{channel}'")
            else:
                dD_log.debug("No active viewer found.")
        except Exception as e:
            dD_log.debug(f"Error setting channel: {e}")

    def itemClicked(self, item):
        layer = item.text()
        self.set_channel(layer)
        # Reset RGBA button style
        self.rgba_button.setStyleSheet("")
        # Revert to active orange style
        self.channel_list_widget.setStyleSheet("""
        QListWidget::item {
            color: {DEFAULT_TEXT_COLOR};
        }
        QListWidget::item:selected {
            background: {HIGHLIGHT_COLOR};
            color: black;
        }
        """)

    def reset_list_item_styles(self):
        """Clear all item colors and the global list style."""
        for i in range(self.channel_list_widget.count()):
            item = self.channel_list_widget.item(i)
            item.setBackground(QColor('transparent'))
            item.setForeground(QColor(DEFAULT_TEXT_COLOR))

        self.channel_list_widget.setStyleSheet("""
        QListWidget::item {
            color: {DEFAULT_TEXT_COLOR};
        }
        QListWidget::item:selected {
            background: {HIGHLIGHT_COLOR};
            color: black;
        }
        """)

    def _open_layermanager_preferences(self):
        """Open the LayerManager preferences dialog."""
        dialog = LayerManagerPrefsDialog(self)
        if dialog.exec_():
            # Reload keywords after prefs change
            self.section_keywords = self.load_section_keywords()
            self._load_refresh_mode_from_prefs()
            self.channels()

    # ========================================================================
    # v2_39: Multi-Mode Refresh System - Main Methods
    # ========================================================================

    def _load_refresh_mode_from_prefs(self):
        """
        Load the refresh mode from JSON preferences.
        """
        import prefs_manager
        self._refresh_mode = prefs_manager.get("refresh_mode", "hybrid")

    def _setup_auto_refresh_with_fallback(self):
        """
        Configure the refresh system based on the chosen mode.
        Includes automatic fallback to simple polling on failure.

        Supported modes:
        - event_driven: Native Nuke callback (0% CPU idle)
        - hybrid: Adaptive polling 500ms->2s->10s
        - focus_only: Refresh on focus only

        FALLBACK: If setup fails, automatically switch to guaranteed simple polling.
        """
        try:
            # Clean up existing system if any
            self._cleanup_refresh_system()

            dD_log.info(f"Initializing refresh mode: {self._refresh_mode}")

            # Try to configure the chosen mode
            if self._refresh_mode == 'event_driven':
                self._setup_event_driven_mode()
            elif self._refresh_mode == 'hybrid':
                self._setup_hybrid_polling_mode()
            elif self._refresh_mode == 'focus_only':
                self._setup_focus_only_mode()
            else:
                # Unknown mode, fallback
                raise ValueError(f"Unknown refresh mode: {self._refresh_mode}")

            # Verify timer is active (checkpoint)
            if not self._viewer_input_timer or not self._viewer_input_timer.isActive():
                raise RuntimeError("Timer not started after setup")

            dD_log.info(f"Mode {self._refresh_mode} activated successfully")

        except Exception as e:
            dD_log.error(f"Setup mode {self._refresh_mode} failed: {e}")
            dD_log.info("Fallback to guaranteed simple polling...")

            # ROBUST FALLBACK: Simple polling that ALWAYS works
            try:
                # Clean up anything that may have been created
                if self._viewer_input_timer:
                    self._viewer_input_timer.stop()
                    self._viewer_input_timer.deleteLater()

                # Remove callback if installed
                if self._viewer_callback_installed:
                    try:
                        nuke.removeKnobChanged(
                            self._on_viewer_input_changed,
                            nodeClass='Viewer'
                        )
                    except:
                        pass

                # Remove event filter if installed
                try:
                    self.removeEventFilter(self)
                except:
                    pass

                # Create simple fallback timer
                self._viewer_input_timer = QTimer(self)
                self._viewer_input_timer.timeout.connect(self.channels)
                self._viewer_input_timer.start(500)  # Fixed 500ms polling

                self._refresh_mode = 'fallback'
                dD_log.info("Fallback simple polling activated (guaranteed to work)")

            except Exception as fallback_error:
                dD_log.error(f"Even fallback failed: {fallback_error}")
                # Last resort: at least have a working timer
                try:
                    if not self._viewer_input_timer:
                        self._viewer_input_timer = QTimer(self)
                        self._viewer_input_timer.timeout.connect(self.channels)
                    self._viewer_input_timer.start(1000)
                except:
                    dD_log.error("Unable to create a timer. UI disabled.")

    def _cleanup_refresh_system(self):
        """
        Cleanly tear down the old refresh system before creating a new one.
        Prevents memory leaks and ghost callbacks.
        """
        try:
            # 1. Stop and delete timer if existing
            if self._viewer_input_timer:
                try:
                    self._viewer_input_timer.stop()
                    self._viewer_input_timer.deleteLater()
                    self._viewer_input_timer = None
                except:
                    pass

            # 2. Remove Nuke callback if installed
            if self._viewer_callback_installed:
                try:
                    nuke.removeKnobChanged(
                        self._on_viewer_input_changed,
                        nodeClass='Viewer'
                    )
                    self._viewer_callback_installed = False
                except:
                    pass

            # 3. Remove event filter if present
            try:
                self.removeEventFilter(self)
            except:
                pass

        except Exception as e:
            dD_log.warning(f"Cleanup error: {e}")

    # ========================================================================
    # Mode 1: EVENT-DRIVEN (0% CPU idle, instant)
    # ========================================================================

    def _setup_event_driven_mode(self):
        """
        Event-driven mode with native Nuke callback.
        Advantage: 0% CPU usage in idle
        Disadvantage: Depends on Nuke API, more complex
        """
        try:
            viewer = nuke.activeViewer()
            if not viewer:
                dD_log.warning("No active viewer for event_driven, fallback to hybrid")
                self._refresh_mode = 'hybrid'
                self._setup_hybrid_polling_mode()
                return

            # Add knobChanged callback
            nuke.addKnobChanged(
                self._on_viewer_input_changed,
                nodeClass='Viewer'
            )
            self._viewer_callback_installed = True

            # Create backup timer (fallback if callback fails)
            self._viewer_input_timer = QTimer(self)
            self._viewer_input_timer.timeout.connect(self._check_viewer_hybrid)
            self._viewer_input_timer.start(5000)  # Check every 5s

            dD_log.info("Event-driven activated (0% CPU idle)")

        except Exception as e:
            dD_log.error(f"Event-driven setup failed: {e}")
            raise

    def _on_viewer_input_changed(self):
        """
        Callback called by Nuke when a Viewer knob changes.
        Triggers refresh only if it's the 'input_number' knob.
        """
        try:
            if nuke.thisKnob() and nuke.thisKnob().name() == 'input_number':
                viewer = nuke.activeViewer()
                if viewer:
                    current_input = viewer.activeInput()

                    # Check for actual change
                    if current_input != self._last_input_index:
                        self._last_input_index = current_input
                        # Thread-safe refresh (Qt)
                        QTimer.singleShot(0, self.channels)
        except:
            pass

    # ========================================================================
    # Mode 2: HYBRID POLLING (500ms→2s→10s, -95% CPU idle)
    # ========================================================================

    def _setup_hybrid_polling_mode(self):
        """
        Hybrid mode with 3-level adaptive polling.
        Advantage: Simple, efficient, -95% CPU in idle
        Disadvantage: Polling (not instant like event-driven)
        """
        try:
            # Create timer
            self._viewer_input_timer = QTimer(self)
            self._viewer_input_timer.timeout.connect(self._check_viewer_hybrid)

            # Start in active mode (500ms)
            self._current_mode = "active"
            self._idle_counter = 0
            self._viewer_input_timer.start(self._poll_interval)

            dD_log.info("Hybrid polling activated (500ms->2s->10s, -95% CPU idle)")

        except Exception as e:
            dD_log.error(f"Hybrid polling setup failed: {e}")
            raise

    def _check_viewer_hybrid(self):
        """
        Hybrid polling method with 3 interval levels:
        - Active mode: 500ms (active usage)
        - Idle mode: 2000ms (inactivity > 5s)
        - Deep mode: 10000ms (inactivity > 60s)
        """
        try:
            # Check viewer input change
            viewer = nuke.activeViewer()
            if viewer:
                current_input = viewer.activeInput()

                if current_input != self._last_input_index:
                    # Change detected
                    self._last_input_index = current_input
                    self.channels()  # Refresh
                    self._idle_counter = 0
                    self._current_mode = "active"
                    self._viewer_input_timer.setInterval(self._poll_interval)
                    self._last_nuke_activity = time.time()
                    return

            # Adapt interval based on inactivity
            time_since_activity = time.time() - self._last_nuke_activity

            if self._current_mode == "active":
                self._idle_counter += 1
                if self._idle_counter >= self._max_idle_before_slow:
                    # Switch to idle mode
                    self._current_mode = "idle"
                    self._viewer_input_timer.setInterval(self._poll_interval_idle)
                    dD_log.info("Switching to idle mode (2000ms)")

            elif self._current_mode == "idle":
                self._idle_counter += 1
                if self._idle_counter >= self._max_idle_deep:
                    # Switch to deep mode
                    self._current_mode = "deep"
                    self._viewer_input_timer.setInterval(self._poll_interval_deep)
                    dD_log.info("Switching to deep mode (10000ms)")

        except Exception as e:
            # Error -> continue silently
            pass

    # ========================================================================
    # Mode 3: FOCUS-ONLY (quasi 0% CPU)
    # ========================================================================

    def _setup_focus_only_mode(self):
        """
        Focus-only mode: refresh only when LayerManager has focus.
        Advantage: Near 0% CPU usage (no polling)
        Disadvantage: Refresh only if LayerManager is visible
        """
        try:
            # Install event filter to detect focus
            self.installEventFilter(self)

            # Backup timer (fallback if event filter doesn't work)
            self._viewer_input_timer = QTimer(self)
            self._viewer_input_timer.timeout.connect(self._check_focus_mode)
            self._viewer_input_timer.start(2000)  # Check every 2s

            dD_log.info("Focus-only mode activated (near 0% CPU)")

        except Exception as e:
            dD_log.error(f"Focus-only setup failed: {e}")
            raise

    def _check_focus_mode(self):
        """Periodic check for focus_only mode (fallback)"""
        try:
            if self.hasFocus():
                # Refresh if we have focus
                viewer = nuke.activeViewer()
                if viewer:
                    current_input = viewer.activeInput()
                    if current_input != self._last_input_index:
                        self._last_input_index = current_input
                        self.channels()
        except:
            pass

    def eventFilter(self, obj, event):
        """Event filter pour focus_only mode"""
        try:
            from PySide2.QtCore import QEvent
            if event.type() == QEvent.FocusIn:
                # LayerManager just received focus
                self.channels()
                self._last_nuke_activity = time.time()
        except:
            pass

        return super().eventFilter(obj, event)

    def _get_refresh_mode_stats(self):
        """
        Returns usage stats for the current refresh mode.
        Useful for diagnosing performance issues.
        """
        try:
            return {
                'mode': self._refresh_mode,
                'timer_active': self._viewer_input_timer.isActive() if self._viewer_input_timer else False,
                'interval_ms': self._viewer_input_timer.interval() if self._viewer_input_timer else 0,
                'callback_installed': self._viewer_callback_installed,
                'current_polling_level': getattr(self, '_current_mode', 'unknown'),
                'idle_counter': getattr(self, '_idle_counter', 0)
            }
        except:
            return {'status': 'error', 'mode': self._refresh_mode}

    def change_refresh_mode(self, new_mode):
        """
        Hot-swap the refresh mode without restarting Layer Manager.
        Modes: 'event_driven', 'hybrid', 'focus_only'
        """
        if new_mode not in ['event_driven', 'hybrid', 'focus_only']:
            dD_log.error(f"Invalid mode: {new_mode}")
            return False

        try:
            dD_log.info(f"Changing refresh mode: {self._refresh_mode} -> {new_mode}")
            self._refresh_mode = new_mode

            # Reinitialize the system
            self._setup_auto_refresh_with_fallback()

            # Save to JSON preferences
            try:
                import prefs_manager
                prefs_manager.set_pref("refresh_mode", new_mode)
            except:
                pass

            dD_log.info(f"Mode successfully changed to '{new_mode}'")
            return True

        except Exception as e:
            dD_log.error(f"Mode change error: {e}")
            return False

    def closeEvent(self, event):
        """
        Clean shutdown with complete refresh system cleanup.
        Called when LayerManager is closed (floating or docked).
        """
        global channel_list_window

        # ========================================================================
        # 1. TOP PRIORITY: Clean up the refresh system
        # ========================================================================

        try:
            self._cleanup_refresh_system()
            dD_log.info("Refresh system cleaned up")
        except Exception as e:
            dD_log.warning(f"Cleanup refresh system error: {e}")

        # ========================================================================
        # 2. Reset global variable
        # ========================================================================

        channel_list_window = None

        # ========================================================================
        # 3. Reset viewer to RGBA
        # ========================================================================

        try:
            if nuke.exists('root'):
                viewer = nuke.activeViewer()
                if viewer:
                    viewer.node()['channels'].setValue('rgba')
                    dD_log.info("Viewer set back to RGBA")
        except Exception as e:
            dD_log.warning(f"Error setting viewer RGBA: {e}")

        # ========================================================================
        # 4. UI cleanup if docked mode
        # ========================================================================

        if not getattr(self, "_is_floating", False):
            try:
                # 1. Remove orange highlighting
                for i in range(self.channel_list_widget.count()):
                    item = self.channel_list_widget.item(i)
                    if item:
                        item.setBackground(QColor('transparent'))
                        item.setForeground(QColor(DEFAULT_TEXT_COLOR))

                # 2. Reset RGBA button to normal style
                if hasattr(self, 'rgba_button'):
                    self.rgba_button.setStyleSheet("")

            except Exception as e:
                dD_log.warning(f"UI cleanup error: {e}")

        # ========================================================================
        # 5. Accept close event
        # ========================================================================

        event.accept()
        dD_log.info("Shutdown complete")

    # ========================================================================
    # v2_37 Legacy Method (Obsolete in v2_39, kept for compatibility)
    # ========================================================================
    # _check_viewer_input_changed() from v2_37 has been replaced by
    # the robust multi-mode system in v2_39 (_check_viewer_hybrid, etc.).
    # Kept only for compatibility if external code references it.
    # ========================================================================

    def _check_viewer_input_changed(self):
        """
        [DEPRECATED v2_39] Old v2_37 polling system.
        Replaced by _check_viewer_hybrid() and the multi-mode system.
        Kept for compatibility only.
        """
        # Fallback to the hybrid method of the multi-mode system
        if hasattr(self, '_check_viewer_hybrid'):
            self._check_viewer_hybrid()
        else:
            # If even the fallback doesn't exist (critical situation)
            try:
                self.channels()
            except:
                pass

    def updateValue(self):
        """Required method for Nuke panel integration"""
        pass

def lightgrade_empty(this_node):
    """
    Replaces the LightGrade_0 node (gizmo) with a real LightGrade.
    Only deletes the gizmo, and forces display of the new node in the node graph.
    """
    import nuke
    import time
    try:
        # Verify we are acting on the gizmo template
        if not this_node or this_node.name() != "LightGrade_0":
            nuke.message("Please run this operation ONLY on the LightGrade_0 node (gizmo).")
            return

        # Find the LayerManager window
        from PySide2.QtWidgets import QApplication
        layer_manager_widget = None
        for widget in QApplication.topLevelWidgets():
            if widget.__class__.__name__ == "LayerManagerUI":
                layer_manager_widget = widget
                break

        if not layer_manager_widget:
            nuke.message("LayerManager is not open.\nOpen LayerManager and select a Layer.")
            return

        # Get the selection
        selected_layer = layer_manager_widget.get_selected_channel()
        if not selected_layer:
            nuke.message("Please select a Layer in LayerManager.")
            return

        # List of Groups before creation
        before_groups = set(n.name() for n in nuke.allNodes('Group'))

        # Create the real LightGrade (new Group node)
        create_lightgrade(selected_layer)

        # Give Nuke time to add the node (important in script)
        nuke.Root().begin()
        time.sleep(0.05)

        # List of Groups after creation
        after_groups = set(n.name() for n in nuke.allNodes('Group'))
        new_groups = after_groups - before_groups

        # Delete only the LightGrade_0 node (gizmo)
        if this_node.knob('selected'):
            this_node['selected'].setValue(False)
        try:
            nuke.delete(this_node)
        except Exception as e:
            dD_log.warning(f"Nuke node delete raised (usually harmless): {e}")

        # Force display/selection of the new LightGrade in the Node Graph
        for node_name in new_groups:
            node = nuke.toNode(node_name)
            if node:
                try:
                    node['selected'].setValue(True)
                    nuke.show(node)
                    # Optional: recenter the node graph
                    # panel = nuke.getPaneFor('Node Graph')
                    # nuke.zoomToFitSelected(panel)
                except Exception:
                    pass

    except Exception as e:
        nuke.message(f"Error in LightGrade Build: {e}")

def show_sticky_warning(title, message):
    box = QMessageBox(QMessageBox.Warning, title, message)
    box.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
    box.exec_()


def load_section_keywords():
    import prefs_manager
    p = prefs_manager.load()
    return {
        "Light Layer":           p.get("light_keywords", []),
        "Mask Layer":            p.get("mask_keywords", []),
        "Utility Layer":         p.get("utility_keywords", []),
        "custom Layer":          p.get("custom_keywords", []),
        "Exclusion Keywords":    p.get("exclusion_keywords", []),
        "custom Title":          p.get("custom_title", "custom"),
        "disable Tech Layer":    p.get("disable_tech", False),
        "disable Light Layer":   p.get("disable_light", False),
        "disable Mask Layer":    p.get("disable_mask", False),
        "disable Utility Layer": p.get("disable_utility", False),
        "disable Custom Layer":  p.get("disable_custom", True),
    }

def get_default_keywords():
    """Returns centralized default values - single source of truth"""
    return {
        "Light Layer": ["lgt*", "rgb*", "dome", "key", "fill", "rim", "sun", "emit"],
        "Mask Layer": ["matte", "mask"],
        "Tech Layer": [],
        "Utility Layer": ["ao", "normal", "pos", "depth", "motion", "pref", "uv", "deep", "_world", "_object"],
        "custom Layer": ["DIMATTE"],
        "Exclusion Keywords": ["rgba", "other", "Crypto"],
        "custom Title": "Dimatte",
        "disable Light Layer": False,
        "disable Mask Layer": False,
        "disable Tech Layer": False,
        "disable Utility Layer": False,
        "disable Custom Layer": True
    }

# No longer need load_preferences_from_file(), using get_default_keywords() directly

def hide_all_knobs(node):
    for i in range(0, 8):
        for suffix in ['in', 'disable', 'solo']:
            knob_name = f"aov_in{i}_{suffix}"
            if knob_name in node.knobs():
                try:
                    node[knob_name].setVisible(False)
                    node[knob_name].setFlag(nuke.INVISIBLE)
                except Exception as e:
                    dD_log.warning(f"Cannot hide {knob_name}: {e}")


def handle_add_layer_button_from_gizmo():
    try:
        import lightgrade_module as lightgrade

        viewer = nuke.activeViewer()
        if not viewer:
            nuke.message("No active Viewer.")
            return

        channel = viewer.node()['channels'].value()
        layer_name = channel.split('.')[0] if '.' in channel else channel
        dD_log.debug(f"channel:{channel}")
        dD_log.debug(f"layer_name:{layer_name}")


        if not layer_name or layer_name.lower() == "rgba":
            nuke.message("No valid layer selected in the Viewer.")
            return

        node = lightgrade.get_active_lightgrade_node()
        if not node:
            nuke.message("No LightGrade selected.")
            return

        lightgrade.add_layer_to_lightgrade(node, layer_name)

    except Exception as e:
        nuke.message(f"Error: {e}")

def get_last_selected_layer():
    try:
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, LayerManagerUI):
                return widget.last_selected_layer
    except:
        pass
    return None

def input_active():
    active_viewer = nuke.activeViewer()
    if not active_viewer:
        nuke.message("No active Viewer.")
        return
    view_node = active_viewer.node()
    input_index = active_viewer.activeInput()
    try:
        connected_node = view_node.input(input_index)
    except:
        nuke.message(f"The Viewer's active input is not connected to any node.")
        return
    return connected_node

def launch_layer_manager():
    try:
        run()
    except Exception as e:
        dD_log.error(f"LayerManager launch failed: {e}")
        import traceback
        traceback.print_exc()


def run():
    global channel_list_window

    def cleanup_this_instance_only():
        """Remove ONLY the existing instances from THIS Nuke instance cleanly

        v2_40 IMPORTANT: Only cleans the current Nuke instance, not other instances!
        """
        global channel_list_window

        # Get the main window of THIS Nuke instance
        nuke_main_window = _get_current_nuke_main_window()

        # 1. Clean up the global reference
        if channel_list_window:
            try:
                channel_list_window.close()
                channel_list_window.deleteLater()
            except:
                pass
            channel_list_window = None

        # 2. Find and remove ONLY the LayerManagers from THIS Nuke instance
        all_layer_managers = [
            w for w in QtWidgets.QApplication.allWidgets()
            if isinstance(w, LayerManagerUI) and _is_same_nuke_instance(w, nuke_main_window)
        ]
        for widget in all_layer_managers:
            try:
                widget.close()
                widget.deleteLater()
            except:
                pass

        # 3. Clean ONLY the LayerManager tabs from THIS Nuke instance
        for w in QtWidgets.QApplication.allWidgets():
            if isinstance(w, QtWidgets.QTabWidget) and _is_same_nuke_instance(w, nuke_main_window):
                to_remove = []
                for i in range(w.count()):
                    if w.tabText(i) == "Layer Manager":
                        to_remove.append(i)
                # Remove in reverse order to avoid index shifts
                for i in reversed(to_remove):
                    w.removeTab(i)

    def is_docked_in_this_instance():
        """Check if LayerManager is already docked IN THIS Nuke instance only"""
        nuke_main_window = _get_current_nuke_main_window()

        for w in QtWidgets.QApplication.allWidgets():
            if isinstance(w, QtWidgets.QTabBar) and _is_same_nuke_instance(w, nuke_main_window):
                for i in range(w.count()):
                    if w.tabText(i) == "Layer Manager":
                        return True
        return False

    # v2_40 STRATEGY: One instance per Nuke instance
    # If a panel is already open in a dock OF THIS INSTANCE, do not create a floating one
    nuke_main_window = _get_current_nuke_main_window()

    if is_docked_in_this_instance():
        # Remove ONLY existing floating windows FROM THIS INSTANCE
        floating_widgets = [
            w for w in QtWidgets.QApplication.allWidgets()
            if isinstance(w, LayerManagerUI) and (w.windowFlags() & Qt.Tool)
            and _is_same_nuke_instance(w, nuke_main_window)
        ]
        for w in floating_widgets:
            w.close()
            w.deleteLater()
        return

    # Check if there is already a visible floating IN THIS INSTANCE
    existing_floating = None
    for w in QtWidgets.QApplication.allWidgets():
        if (isinstance(w, LayerManagerUI) and
            (w.windowFlags() & Qt.Tool) and
            w.isVisible() and
            _is_same_nuke_instance(w, nuke_main_window)):
            existing_floating = w
            break

    # If already a visible floating in this instance, bring it to front
    if existing_floating:
        existing_floating.raise_()
        existing_floating.activateWindow()
        return

    # v2_40 CLEAN CREATION: Clean first (this instance), create next
    cleanup_this_instance_only()


    # Wait for an event cycle so deletions take effect
    def create_new():
        global channel_list_window
        channel_list_window = LayerManagerUI()
        channel_list_window._is_floating = bool(channel_list_window.windowFlags() & Qt.Tool)
        channel_list_window.show()
        if channel_list_window._is_floating:
            # Short timer for RGBA click
            QTimer.singleShot(50, channel_list_window.rgba_button.click)
    # Deferred creation to avoid conflicts
    QTimer.singleShot(10, create_new)


import __main__

# Place the class in __main__ so nukescripts.panels can resolve it via eval()
__main__.LayerManagerUI = LayerManagerUI

panels.registerWidgetAsPanel(
    'LayerManagerUI',           # Class accessible via __main__
    PANEL_NAME,                 # Name displayed in Panes > Custom
    PANEL_ID,                   # Unique panel ID
    False                       # Do not create immediately
)

# run()
# if __name__ == "__main__":
#     run()


