#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import nuke
import time
import shutil
import re
import dD_log


LOGO_PATH = os.path.join(os.path.dirname(__file__), "icons", "layerM.png")
# Default values per node type
# These values are used to detect if a knob has been modified from its initial state.
NODE_DEFAULTS = {
    "Grade": {
        "blackpoint": [0.0, 0.0, 0.0, 0.0],
        "whitepoint": [1.0, 1.0, 1.0, 1.0],
        "black": [0.0, 0.0, 0.0, 0.0],
        "white":[1.0, 1.0, 1.0, 1.0],
        "add": [0.0, 0.0, 0.0, 0.0],
        "multiply": [1.0, 1.0, 1.0, 1.0],
        "gamma": [1.0, 1.0, 1.0, 1.0]
    },
    "ColorCorrect": {
        "saturation": [1.0, 1.0, 1.0, 1.0],
        "contrast": [1.0, 1.0, 1.0, 1.0],
        "gamma": [1.0, 1.0, 1.0, 1.0],
        "gain": [1.0, 1.0, 1.0, 1.0],
        "offset": [0.0, 0.0, 0.0, 0.0]
    },
    "Saturation": {
        "saturation": 1.0
    },
    "Toe2": {
        "lift": [0.0, 0.0, 0.0, 0.0]
    },
    "HueShift": {
        "ingray": [0.25, 0.25, 0.25, 0.25],
        "outgray": [0.25, 0.25, 0.25, 0.25],
        "saturation": 1.0,
        "color": [1.0, 0.0, 0.0],
        "color_saturation": 1.0,
        "hue_rotation": 0.0,
        "brightness": 1.0
    }
}

# Simplified labels for display
# Shortens long knob names for quick readability.
NODE_LABELS = {
    "Grade": {
        "blackpoint": "blck pt",
        "whitepoint": "wht pt",
        "black": "lift",
        "white": "gain",
        "add": "offs",
        "multiply": "multi",
        "gamma": "gam"
    },
    "ColorCorrect": {
        "saturation": "sat",
        "contrast": "cont",
        "gamma": "gam",
        "gain": "gain",
        "offset": "offs"
    },
    "Saturation": {
        "saturation": "sat"
    },
    "Toe2": {
        "lift": "lift"
    },
    "HueShift": {
        "ingray": "in",
        "outgray": "out",
        "saturation": "sat",
        "color": "col_axis",
        "color_saturation": "sat_axis",
        "hue_rotation": "hue_rot",
        "brightness": "brigh"

    }
}

KNOBCHECK_ENABLED = True
DEFAULT_COLOR = 6064777
_LAST_RUN_TIMESTAMP = 0
DOUBLE_PRESS_INTERVAL = 0.5  # max seconds between two V presses



def get_version_from_filename(filename=None):
    """Extract version from the script filename

    Args:
        filename: Path to the file. If None, uses __file__ of this module

    Returns:
        str: Version string (e.g., "v3.0")
    """
    dD_log.debug(f"get_version_from_filename called with filename: {filename}")
    if filename is None:
        script_name = os.path.basename(__file__)
        dD_log.debug(f"Using __file__ from utils_fonctions: {__file__}")
    else:
        script_name = os.path.basename(filename)
        dD_log.debug(f"Using provided filename: {filename}")

    dD_log.debug(f"script_name:{script_name}")
    match = re.search(r'_v(\d+_\d+)', script_name)
    dD_log.debug(f"match:{match}")
    if match:
        version = "v" + match.group(1)
        dD_log.debug(f"Found version: {version}")
        return version
    dD_log.debug("No version found, returning v1.0")
    return "v1.0"

def center_below(reference, target, y_offset=40):
    """Center 'target' horizontally below 'reference' with a vertical gap."""
    try:
        x = int(reference.xpos() + reference.screenWidth() / 2 - target.screenWidth() / 2)
        y = reference.ypos() + reference.screenHeight() + y_offset
        target.setXpos(x)
        target.setYpos(y)
    except Exception as e:
        dD_log.debug(f"Unable to center the node: {e}")

def clean_labels_with_marker(marker="⟳"):
    """
    Removes the line containing the marker from all nodes that have it in their label.
    Called automatically when knobChanged is globally disabled.
    """
    count = 0
    for node in nuke.allNodes():
        if "label" in node.knobs():
            label = node["label"].value()
            if marker in label:
                # Remove the line containing the marker plus any trailing newline
                cleaned = "\n".join(line for line in label.splitlines() if marker not in line).strip()
                node["label"].setValue(cleaned)
                count += 1
    dD_log.debug(f"{count} node(s) cleaned of '{marker}'")

def format_knob_value(label_name, knob):
    """
    Formats a knob value (mono or vector) for display in a label.
    Only returns something if the knob is visible, enabled,
    and different from its neutral value (1.0 or 0.0).
    """

    if not knob.enabled() or not knob.visible():
        return None

    v = knob.value()

    if hasattr(knob, "value") and isinstance(v, (tuple, list)) and len(v) >= 3:
        channel_labels = ["r", "g", "b"]
        display_parts = []
        for i, channel in enumerate(channel_labels):
            c = float(v[i])
            if abs(c - 1.0) > 0.001:
                if c == 0:
                    display_parts.append(f"{channel}0")
                elif c.is_integer():
                    display_parts.append(f"{channel}{int(c)}")
                else:
                    display_parts.append(f"{channel}{round(c, 1)}")
        if display_parts:
            return f"{label_name} {' '.join(display_parts)}"

    elif isinstance(v, float):
        if abs(v - 1.0) > 0.001:
            if v == 0:
                return f"{label_name} 0"
            elif v.is_integer():
                return f"{label_name} {int(v)}"
            else:
                return f"{label_name} {round(v, 1)}"

    return None

def format_grade_knob_value(knob_name, knob, node_class):
    """
    Advanced version for formatting a knob value,
    based on:
    - the node class (Grade, ColorCorrect, etc.)
    - its default values
    - its custom names
    """

    if not knob.enabled() or not knob.visible():
        return None

    # Get node-type-specific configs
    defaults = NODE_DEFAULTS.get(node_class, {})
    pretty_names = NODE_LABELS.get(node_class, {})

    # If the knob is not defined for this node type, skip
    if knob_name not in defaults:
        return None

    default = defaults[knob_name]
    label_name = pretty_names.get(knob_name, knob_name)
    v = knob.value()

    # If the default value is a list (e.g. RGBA), treat as vector
    if isinstance(default, list):
        # If v is a scalar, duplicate it across all channels
        if not isinstance(v, (list, tuple)):
            v = [v] * len(default)
        else:
            v = list(v)
        default = list(default)

        # Common vector processing
        channel_labels = ["r", "g", "b"]
        values = []
        for i in range(len(channel_labels)):
            if i >= len(v) or i >= len(default):
                continue
            values.append(float(v[i]))

        defaults = default[:len(values)]
        diffs = [abs(values[i] - defaults[i]) > 0.001 for i in range(len(values))]

        if any(diffs):
            if all(abs(values[i] - values[0]) < 0.001 for i in range(1, len(values))):
                val = values[0]
                return f"{label_name} {int(val) if val.is_integer() else round(val, 1)}"
            else:
                display_parts = []
                for i, channel in enumerate(["r", "g", "b", "a"]):
                    if i >= len(values):
                        continue
                    c = values[i]
                    d = default[i]
                    if abs(c - d) > 0.001:
                        display_parts.append(f"{channel}{int(c) if c.is_integer() else round(c, 1)}")
                if display_parts:
                    return f"{label_name} {' '.join(display_parts)}"

    # Otherwise, scalar processing (e.g. Saturation)
    elif isinstance(default, (float, int)) and isinstance(v, (float, int)):
        if abs(v - default) > 0.001:
            return f"{label_name} {int(v) if v.is_integer() else round(v, 1)}"

    dD_log.debug(f"{label_name} -> v={v} | default={default}")

    return None

def get_last_selected_node():
    """ Return the last node selected or the node connected to the viewer"""
    selected = nuke.selectedNodes()
    if selected:
        return selected[-1]
    else:
        viewer = nuke.activeViewer()
        if viewer:
            input_index = viewer.activeInput()
            return viewer.node().input(input_index) if input_index is not None else None
    return None

def is_called_from_knob_changed():
    """
    Detects if the script is being executed from a knobChanged (internal context).
    """
    import inspect
    for frame in inspect.stack():
        if "knobChanged" in frame.filename or "knobChanged" in frame.function:
            return True
    return False

def is_double_press():
    global _LAST_RUN_TIMESTAMP
    now = time.time()
    delta = now - _LAST_RUN_TIMESTAMP
    _LAST_RUN_TIMESTAMP = now
    return delta < DOUBLE_PRESS_INTERVAL

def is_knobcheck_enabled():
    return KNOBCHECK_ENABLED

def insert_node_below_visually(node_class, original_node,
                               node_name=None, x_tolerance=30, y_offset=70):
    """
    Insert a node of class `node_class` between `original_node` and its first connected downstream node
    that is visually aligned (within `x_tolerance`), and vertically lower.
    If no downstream node is found or no valid original_node is given, the new node is created and positioned at (300, 300).
    """
    if original_node is None:
        selected = nuke.selectedNodes()
        original_node = selected[0] if selected else None

    # If node is invalid (Root or no position), fallback to a fixed position
    if not original_node or original_node.Class() == "Root" or not hasattr(original_node, "xpos"):
        new_node = nuke.createNode(node_class, inpanel=True)
        new_node.showControlPanel()
        new_node.setXpos(300)
        new_node.setYpos(300)
        new_node["tile_color"].setValue(DEFAULT_COLOR)
        return new_node

    # Find a downstream node that is vertically aligned
    target_node = None
    target_input_index = None
    min_delta_y = float('inf')

    for dep in original_node.dependent(nuke.INPUTS):
        for i in range(dep.inputs()):
            if dep.input(i) == original_node:
                if abs(dep.xpos() - original_node.xpos()) <= x_tolerance:
                    delta_y = dep.ypos() - original_node.ypos()
                    if delta_y > 0 and delta_y < min_delta_y:
                        target_node = dep
                        target_input_index = i
                        min_delta_y = delta_y

    # Temporarily deselect all nodes
    prev_sel = nuke.selectedNodes()
    for n in prev_sel:
        n['selected'].setValue(False)

    # Create the new node
    new_node = nuke.createNode(node_class, inpanel=True)
    if node_name:
        new_node.setName(node_name)
    new_node.showControlPanel()

    new_node.setInput(0, None)

    # Connect to original_node
    new_node.setInput(0, original_node)

    # Reconnect a downstream node if applicable
    if target_node:
        target_node.setInput(target_input_index, new_node)

    # Position correctly
    xpos = original_node.xpos() + original_node.screenWidth() // 2 - new_node.screenWidth() // 2
    ypos = original_node.ypos() + (min_delta_y // 2 if target_node else y_offset)
    new_node.setXpos(xpos)
    new_node.setYpos(ypos)
    new_node["tile_color"].setValue(DEFAULT_COLOR)

    return new_node



def set_knobcheck_enabled(state: bool):
    global KNOBCHECK_ENABLED
    KNOBCHECK_ENABLED = state

    if not state:
        clean_labels_with_marker("⟳")  # Automatic cleanup

def toggle_knobcheck():
    global KNOBCHECK_ENABLED
    KNOBCHECK_ENABLED = not KNOBCHECK_ENABLED
    state = "ON" if KNOBCHECK_ENABLED else "OFF"
    nuke.message(f"knobChanged global is now: {state}")

def format_label(values):
    """
    values: list of tuples (value, color name)
    return string with HTML colors.
    """
    html_colors = {
        'red': '#ff5555',
        'green': '#55ff55',
        'blue': '#5555ff',
        'grey': '#aaaaaa'
    }

    parts = []
    for val, color in values:
        hex_color = html_colors.get(color, '#ffffff')  # white if unknown
        parts.append(f'<font color="{hex_color}">{val}</font>')
    return ' '.join(parts)

def get_colored_knob_value(node, knob_name):
    """ return the colored values of knobs changed
    args::
        node
        knob_name
    return :: str()
        1 or 3 value with colors
    """
    knob = node[knob_name]
    knobs = {
        "Grade": ["blackpoint", "whitepoint", "black", "white", "multiply", "add", "gamma"],
        "ColorCorrect": ["saturation", "contrast", "gain", "gamma", "offset"],
        "Saturation": ["saturation"],
        "HueShift": ["ingray", "outgray", "saturation", "color", "color_saturation", "hue_rotation", "brightness"],
        "Toe2": ["lift"]
    }

    color_labels = ('red', 'green', 'blue', 'grey')
    rounded = 2
    result = []

    if node.Class() not in knobs:
        return None

    if knob_name not in knobs[node.Class()]:
        return None

    knob_size = knob.arraySize()
    values = [knob.value(i) for i in range(knob_size)]

    # Handle default values
    try:
        default = knob.defaultValue()
        if isinstance(default, (list, tuple)):
            defaults = list(default)
        else:
            defaults = [default] * knob_size  # fallback
    except Exception:
        defaults = [0.0] * knob_size  # last resort

    # Case: scalar or equal RGB
    if knob_size == 1 or (knob_size >= 3 and values[0] == values[1] == values[2]):
        if values[0] != defaults[0]:
            result.append((round(values[0], rounded), color_labels[3]))  # grey

    # Case: RGBA with differences
    elif knob_size == 4:
        for i in range(4):
            if values[i] != defaults[i]:
                result.append((round(values[i], rounded), color_labels[i]))

    else:
        result.append(None)

    return result
