# -*- coding: utf-8 -*-
# ==============================================================================
# LightGrade Gizmo System (2025)  (__LIGHTGRADE_VERSION__)
# Author: David Francois
# ==============================================================================
#
# TABLE OF CONTENTS:
#   1. Imports & Constants
#   2. Main function: create_lightgrade
#   3. Public functions
#   4. Internal utility functions (helpers)
#   5. Export JSON
#
# ==============================================================================


#region 1. Imports & Constants
import json
import os
import sys
import re
import nuke
import dD_log
# REMOVED: import layermanager (to avoid circular import - use lazy import in functions)
from datetime import datetime
import traceback
from PySide2 import QtWidgets


# Relative imports from the layermanager package
import utils_fonctions
from utils_fonctions import get_version_from_filename

# Config directory path
PREFERENCE_DIR = os.path.join(os.path.dirname(__file__), "config")

# NOTE: layermanager import removed to avoid circular import
# Use lazy import in functions that need it
if PREFERENCE_DIR not in sys.path:
    sys.path.append(PREFERENCE_DIR)

from utils_fonctions import format_knob_value, get_last_selected_node, insert_node_below_visually

VERSION = get_version_from_filename(__file__)
# __LIGHTGRADE_VERSION__ = "v2.5"
HELP_LINK = "https://github.com/Duckydav/LayerManager"
AUTHOR_LINK = "https://www.linkedin.com/in/davidfrancois/"


DEFAULT_COLOR = 6064777
WARNING_COLOR = 4278190335
ERROR_COLOR = 2671189247
DEBUG = False


def title():
    return (
        "<br>"
        f"<font size=7>"
        f"<a href='{HELP_LINK}' style='text-decoration:none; color:#DADADA;'>Light</a> "
        "<font color='#FCB132'><b>"
        f"<a href='{HELP_LINK}' style='text-decoration:none; color:#FCB132;'>Grade</a>"
        "</b></font>"
        f"<font size=3 color='#777777'>  {VERSION}</font>"
        "<br>"
    )

def credit():
    return (
        f"<p style='color:#A2A1A1'>"
        f"<a href='{HELP_LINK}' style='text-decoration:none; color:#A2A1A1;'>"
        "Light<b><font color='#545454'>Grade</font></b>"
        "</a>"
        f" <font color='#888888'>{VERSION}</font> &copy; 2024"
        "<span style='color:#888888;'> | </span>"
        f"<a href='{AUTHOR_LINK}' style='text-decoration:none; color:#888888;'><font size=3>DavidF</font></a> "
        "<span style='color:#888888;'> | </span>"
        f"<a href='{HELP_LINK}' style='text-decoration:none; color:#FCB132;'><font size=3>help</font></a>"
        "</p>"
    )


def show_help():
    import nuke
    nuke.message(
        "Comp Tools LightGrade - Help\n\n"
        "- This node is the entry point for creating a LightGrade from LayerManager.\n"
        "- Connect the node to a Read or your render stream.\n"
        "- Open LayerManager to choose a lighting Layer.\n"
        "- Click Build to automatically create a ready-to-use LightGrade.\n"
        "\n"
        "Note: The empty version will be deleted after the real LightGrade is created.\n"
        "\n"
        "For more info, contact DavidF."
    )



def knobChanged():
    n = nuke.thisNode()
    k = nuke.thisKnob()

    if nuke.GUI:
        if k.name() == "updateMuteState":
            for i in range(0, 8):
                layer_name = f"aov_in{i}"
                if f"{layer_name}_disable" in n.knobs():
                    mute_layer(layer_name)

        if k.name().endswith("_disable"):
            layer_name = k.name().replace("_disable", "")
            mute_layer(layer_name)

        if k.name().endswith("_solo"):
            layer_name = k.name().replace("_solo", "")
            solo_layer(layer_name)
            # -- Update the hidden knob that drives the Switch
            solo_active = any(
                n[k].label().strip() == 'solo'
                for k in n.knobs() if k.endswith("_solo")
            )
            if "any_solo_active" in n.knobs():
                n["any_solo_active"].setValue(int(solo_active))

        # -- Display logic for global SOLO state in UI/label node
        solo_active = any(
            n[k].label().strip() == 'solo'
            for k in n.knobs() if k.endswith("_solo")
        )
        if solo_active:
            n["tile_color"].setValue(WARNING_COLOR)
            n["label"].setValue("MODE AOV SOLO")
        else:
            n["tile_color"].setValue(DEFAULT_COLOR)
            n["label"].setValue("")

        # Dynamic autolabel
        if k.Class() == 'Color_Knob' or (
            k.Class() == 'Double_Knob' and k.hasFlag(nuke.USER_DEFINED)
        ):
            # import gradeaov_module
            lightgrade_module.add_lightgrade_module_autolabel(n)

def add_lightgrade_module_autolabel(node):
    code = (
        "'LightGrade\\n' + '\\n'.join([\n"
        "    '%s = (%%.2f, %%.2f, %%.2f)' %% (k, v[0], v[1], v[2])\n"
        "    for k in nuke.thisNode().knobs()\n"
        "    if nuke.thisNode()[k].Class() == 'Color_Knob'\n"
        "    and isinstance(nuke.thisNode()[k].value(), tuple)\n"
        "    and (abs(nuke.thisNode()[k].value()[0] - 1.0) > 0.001 or\n"
        "         abs(nuke.thisNode()[k].value()[1] - 1.0) > 0.001 or\n"
        "         abs(nuke.thisNode()[k].value()[2] - 1.0) > 0.001)\n"
        "    for v in [nuke.thisNode()[k].value()]\n"
        "] + [\n"
        "    'saturation = %.2f' %% nuke.toNode(n.name()).node('saturation')['saturation'].value()\n"
        "    if abs(nuke.toNode(n.name()).node('saturation')['saturation'].value() - 1.0) > 0.001 else ''\n"
        "])"
    )
    node["autolabel"].setValue(code)

def add_autolabel(node):
    expr = (
        "'LightGrade\\n' + "
        "'\\n'.join(["
        "nuke.thisNode()[k].value().replace('lg_', '') "
        "if nuke.thisNode()[k].value().startswith('lg_') else nuke.thisNode()[k].value() "
        "for k in sorted(nuke.thisNode().knobs()) "
        "if k.startswith('aov_in') and k.endswith('_in') and "
        "nuke.thisNode()[k].value() != 'none' and "
        "(k.replace('_in', '_disable') not in nuke.thisNode().knobs() or not nuke.thisNode()[k.replace('_in', '_disable')].value())"
        "])"
    )
    node["autolabel"].setValue(expr)

def update_layer_label(node):
    """
    Dynamically updates the node label with enabled layers, on a single line.
    """
    if not node or not isinstance(node, nuke.Node):
        return

    tcl_exprs = []
    for i in range(1, 9):
        input_knob = f"aov_in{i}_in"
        disable_knob = f"aov_in{i}_disable"

        if input_knob in node.knobs():
            raw = node[input_knob].value()
            val = raw.strip() if isinstance(raw, str) else ""
            disabled = node[disable_knob].value() if disable_knob in node.knobs() else 0

            excluded = {"rgba", "rgb", "alpha", "none", ""}
            if val and val.lower() not in excluded and not disabled:
                tcl_exprs.append('[regsub lg_ [value aov_in{}_in] ""]'.format(i))

    lines = []
    for i in range(0, len(tcl_exprs), 3):
        lines.append(" | ".join(tcl_exprs[i:i+3]))
    label = "\n".join(lines)
    node["autolabel"].setValue("")
    node["label"].setValue(label)

def lightgrade_empty(this_node):
    try:
        # 1. Check that the node is a valid LightGrade "template"
        if not this_node or not this_node.name().lower().startswith("lightgrade"):
            nuke.message("Invalid LightGrade node.")
            return

        # 2. Open LayerManager if needed (optional, or manually by the user)
        # launch_layer_manager()  # uncomment to open automatically

        # 3. Call the actual LightGrade creation function
        # Retrieve the Layer selection from LayerManager, or let the user choose.
        selected_layer = get_last_selected_layer()
        dD_log.debug(f"selected_layer:{selected_layer}")
        if not selected_layer:
            nuke.message("Please select a Layer in LayerManager.")
            return
        create_lightgrade(selected_layer)

        # 4. Delete the empty LightGrade node (this_node)
        nuke.delete(this_node)

    except Exception as e:
        nuke.message(f"Error in LightGrade Build: {e}")

#region 2. Main function: create_lightgrade
def create_lightgrade(layer=None):
    """
    Creates a LightGrade node and ensures the title and credit are always in the correct order,
    without touching the existing gizmo system UI.
    """


    # Step 1 -- Get the last selected node (to connect the new lightgrade to it)
    last_selected_node = get_last_selected_node()

    if not last_selected_node:
        # Fallback: use the node connected in the Viewer
        try:
            viewer = nuke.activeViewer()
            if viewer:
                input_index = viewer.activeInput()
                viewer_node = viewer.node()
                last_selected_node = viewer_node.input(input_index)
        except:
            last_selected_node = None

    if not last_selected_node:
        nuke.message("No relevant node found to connect the LightGrade.")
        return

    # Step 2 -- Retrieve the selected layer from the UI
    selected_layer = layer
    if not selected_layer:
        nuke.message("Please select a layer before creating a LightGrade lightgrade_node.")
        return

    # Step 3 -- Create the lightgrade node between 2 nodes
    lightgrade_node = insert_node_below_visually(node_class='dD_lightgrade', original_node=last_selected_node)
    if not last_selected_node or last_selected_node.Class() == "Root":
        nuke.message("No valid node selected or connected in the Viewer.")
        return

    # --- Title at the top (always up to date, never duplicated)
    if "lightgrade_title" in lightgrade_node.knobs():
        lightgrade_node["lightgrade_title"].setValue(title())
        lightgrade_node["lightgrade_title"].setTooltip("link to help")
        # lightgrade_node.addKnob(title_knob)

    lightgrade_node.setInput(0, last_selected_node)

    # --- Add the chosen layer (original code)
    add_layer_to_lightgrade(lightgrade_node, selected_layer)

    # --- Update the expression node based on layers
    update_expression_node(lightgrade_node)

    # --- Display the list of available layers
    if "available_layers_text" in lightgrade_node.knobs():
        layers = find_light_layers(lightgrade_node)
        lightgrade_node["available_layers_text"].setValue(
            '<font color="#888888">Layers available: ' +
            " | ".join(l.replace("lg_", "") for l in layers) +
            '</font>'
        )

    # --- Hide all aov_in knob groups except the first
    hide_knobs(lightgrade_node)

    # --- Credit at the bottom (always up to date, never duplicated)
    if "lightgrade_credit" in lightgrade_node.knobs():
        lightgrade_node.removeKnob(lightgrade_node["lightgrade_credit"])
    credit_knob = nuke.Text_Knob("lightgrade_credit", "", credit())
    credit_knob.setTooltip("link to help")
    lightgrade_node.addKnob(credit_knob)

    # --- Open node properties and show the Settings tab if possible
    try:
        nuke.show(lightgrade_node)
        tab_knobs = [knob for knob in lightgrade_node.knobs().values() if knob.Class() == "Tab_Knob"]
        for tab in tab_knobs:
            if "Settings" in tab.label():
                lightgrade_node[tab.name()].setFlag(0x1000)
                break
    except Exception:
        pass


def lightgrade_credit(version=None):
    version = version or VERSION
    return (
        "\n<a href='{help}' style='text-decoration:none; color:#888888;'>"
        "<font size=3>Light<b><font color='#545454'>Grade</font></b>"
        "<font color='#888888'> {ver}</font> &copy; 2024</font></a> "
        "<span style='color:#888888;'> | </span>"
        "<a href='{author}' style='text-decoration:none; color:#888888;'><font size=3>DavidF</font></a> "
        "<span style='color:#888888;'> | </span>"
        "<a href='{help}' style='text-decoration:none; color:#FCB132;'><font size=3>help</font></a>"
    ).format(
        help=HELP_LINK,
        ver=version,
        author=AUTHOR_LINK
    )

def find_light_layers(node):
    channels = node.channels()
    raw_layers = set(c.split('.')[0] for c in channels)

    # Separate the 3 groups
    lg_layers = sorted([l for l in raw_layers if l.startswith('lg_')])
    has_emission = 'emission' in raw_layers
    has_glow = 'glow' in raw_layers

    result = []
    if has_emission:
        result.append('emission')
    result.extend(lg_layers)
    if has_glow:
        result.append('glow')

    return result

def update_expression_node(node):
    """
    Updates the Expression node in the LightGrade gizmo by accumulating all 'lg_' and 'emission'
    layers on the RGB components.
    """
    try:
        layers = find_light_layers(node)
        if not layers:
            return

        expr_node = node.node("Expression1")
        if not expr_node:
            return

        # Define the output channels to leftover
        nuke.tcl("add_layer", "leftover leftover.red leftover.green leftover.blue")
        expr_node["channel0"].setValue("leftover.red")
        expr_node["channel1"].setValue("leftover.green")
        expr_node["channel2"].setValue("leftover.blue")

        # Expression1: leftover = rgb - (sum of layers)
        for i, c in enumerate(["red", "green", "blue"]):
            knob_name = f"expr{i}"
            if knob_name in expr_node.knobs():
                expr = f"{c} - ({' + '.join(f'{layer}.{c}' for layer in layers)})"
                expr_node[knob_name].setValue(expr)
            else:
                pass

        # Expression2: reconstruction = sum of layers + leftover
        expr2_node = node.node("Expression2")
        if not expr2_node:
            return
        #
        layers_with_leftover = layers + ["leftover"]
        for i, c in enumerate(["red", "green", "blue"]):
            expr = " + ".join(f"{layer}.{c}" for layer in layers_with_leftover)
            expr2_node[f"expr{i}"].setValue(expr)




    except Exception:
        pass

def hide_knobs(node):
    for i in range(2, 9):
        for suffix in ['in', 'disable', 'solo']:
            knob_name = f"aov_in{i}_{suffix}"
            if knob_name in node.knobs():
                try:
                    node.knobs()[knob_name].setVisible(False)
                except Exception:
                    pass

def hide_all_knobs():
    node = get_active_lightgrade_node()
    if not node:
        nuke.message("No lightgrade node selected.")
        return

    for i in range(0, 8):
        base = f"aov_in{i}"
        for suffix in ['_in', '_disable', '_solo']:
            knob = f"{base}{suffix}"
            if knob in node.knobs():
                try:
                    node[knob].setValue("none") if suffix == '_in' else None
                    node[knob].setVisible(False)
                    node[knob].setFlag(nuke.INVISIBLE)
                except:
                    pass

    node["layer_count"].setValue(0)
    # Lazy import to avoid circular import
    try:
        import layer_manager as layermanager
        layermanager.hide_all_knobs(node)
    except (ImportError, AttributeError):
        # If layermanager is not available, continue without calling this function
        pass

def mute_layer(layer_name):
    node = nuke.thisNode()
    disable_knob = f"{layer_name}_disable"
    input_knob = f"{layer_name}_in"

    if disable_knob not in node.knobs() or input_knob not in node.knobs():
        return

    disable = node[disable_knob].value()

    # Special case: Expression1
    if layer_name == "Expression1":
        expr_node = node.node("Expression1")
        if expr_node:
            expr_node["disable"].setValue(disable)
        return

    # Normal case: Shuffle
    shuffle = next((n for n in node.nodes() if n.name() == layer_name and n.Class() == "Shuffle"), None)
    if not shuffle:
        return

    shuffle["disable"].setValue(disable)
    node[input_knob].setEnabled(not disable)


def solo_layer(layer_name):
    node = nuke.thisNode()
    solo_knob = f"{layer_name}_solo"

    solo_btn = node[solo_knob]
    is_solo_active = solo_btn.label() == '<font size=3 color=Red> solo'
    new_state = not is_solo_active

    solo_btn.setLabel('<font size=3 color=Red> solo' if new_state else ' solo')

    for i in range(1, 9):
        target = f"aov_in{i}"
        mute_knob = f"{target}_disable"
        dD_log.debug(f"mute_knob:{mute_knob}")

        if mute_knob in node.knobs():
            node[mute_knob].setValue(0 if target == layer_name else int(new_state))

    # Apply mute visually
    for i in range(1, 9):
        if f"aov_in{i}_disable" in node.knobs():
            mute_layer(f"aov_in{i}")


    # Color and label
    if new_state:
        label = f"solo {node[f'{layer_name}_in'].value().replace('lg_', '')}"
        node["tile_color"].setValue(WARNING_COLOR)
        node["autolabel"].setValue("")
        node["label"].setValue(label)

        if "Merge_add_noise" in node.knobs():
            node["Merge_add_noise"].setEnabled(False)
    else:
        node["tile_color"].setValue(DEFAULT_COLOR)
        # add_autolabel(node)
        node["label"].setValue("")
        node["note_font"].setValue("")
        update_layer_label(node)

    # update_switch()
    nuke.updateUI()

def update_switch():
    node = nuke.thisNode()
    solo_active = any(
        node[k].label().startswith('<font size=3 color=Red>')
        for k in node.knobs() if k.endswith("_solo")
    )
    dD_log.debug(f"solo_active:{solo_active}")
    try:
        switch = node.node("switch")
        if solo_active:
            switch["which"].setExpression("1")
        else:
            switch["which"].setExpression("0")
        nuke.updateUI()
    except Exception as e:
        dD_log.debug(f"[DEBUG SWITCH] {e}")

    if solo_active:
        switch["which"].setValue(1)
    else:
        switch["which"].setValue(0)

#region 3. Public functions
def add_layer():
    n = nuke.thisNode()
    layer_count = int(n["layer_count"].value())

    if layer_count >= 8:
        nuke.message("limit to 8 layers")
        return

    knob_index = layer_count + 1
    knob_base = f"aov_in{knob_index}"

    # Increment the counter now
    n["layer_count"].setValue(knob_index)

#region 5. Export JSON
def export_lightgrade_values_to_json():
    # Export values from all modified Grade nodes in the group to a .json file.

    n = nuke.thisNode()  # First get the node
    if "dynamic_export" in n.knobs() and not n["dynamic_export"].value():
        nuke.message("Dynamic export disabled.")
        return

    node_name = n.name()

    # Find the first valid Read in the input chain
    def find_read_recursive(node, visited=None):
        if visited is None:
            visited = set()
        if node in visited:
            return None
        visited.add(node)

        if node.Class() == "Read":
            return node
        elif node.Class() == "Group":
            with node:
                for sub in nuke.allNodes("Read"):
                    if sub["file"].value():
                        return sub

        for i in range(node.inputs()):
            dep = node.input(i)
            if dep:
                found = find_read_recursive(dep, visited)
                if found:
                    return found

        return None

    read_node = find_read_recursive(n)
    if not read_node:
        nuke.message("No Read node found in the chain.")
        return

    exr_path = read_node.metadata("input/filename") or read_node["file"].value()
    dD_log.debug(f"exr_path:{exr_path}")


    # debug(f"exr_path: {exr_path}")

    if not exr_path or not os.path.basename(exr_path).lower().endswith(".exr"):
        nuke.message("The EXR file could not be found.")
        return

    # Regex extraction -- generic pattern: project/season/episode/sequence_shot/pass/version
    match = re.search(
        r"[\\/](?P<project>[^\\/]+)[\\/].+?[\\/](?P<season>S_\d+)[\\/](?P<episode>\d+)[\\/](?P<sequence>\d{3})_(?P<shot>\d{3})[\\/].+?[\\/](?P<passname>[^\\/]+)[\\/](?P<version>\d+_\d+_\d+)[\\/].*",
        exr_path.replace("/", "\\")
    )

    if not match:
        nuke.message("EXR path does not match expected format.")
        return

    data = match.groupdict()

    intermediate_match = re.search(rf"{data['sequence']}_{data['shot']}/([^/\\]+?)/Cmp/", exr_path.replace("\\", "/"))
    intermediate_dir = intermediate_match.group(1) if intermediate_match else ""

    # Output directory -- export JSON next to the Nuke script
    script_dir = os.path.dirname(nuke.root().name()) if nuke.root().name() else os.path.expanduser("~")
    base_dir = os.path.join(script_dir, "JSON")

    os.makedirs(base_dir, exist_ok=True)

    # Final filename
    basename = os.path.basename(exr_path)
    match_filename = re.search(r"^([A-Za-z0-9]+)_(beauty_[a-zA-Z0-9_]+)_v(\d+_\d+_\d+)", basename)
    if not match_filename:
        nuke.message("Unable to extract info from the EXR filename.")
        return


    proj_name = match_filename.group(1)
    passname = match_filename.group(2)
    version = match_filename.group(3)
    shot_str = f"{data['episode']}_{data['sequence']}_{data['shot']}"

    script_name = os.path.basename(nuke.root().name()).replace(".nk", "")
    json_name = f"{proj_name}_{shot_str}_{script_name}_{passname}_{version}_{node_name}.json"
    export_path = os.path.join(base_dir, json_name)


    # Export modified values
    export_data = {}
    grade_knobs_to_check = [
        "blackpoint", "whitepoint", "lift", "gain",
        "multiply", "offset", "gamma"
    ]

    for node in nuke.allNodes(group=n):
        if node.Class() != "Grade":
            continue

        channel_name = node["channels"].value()
        values = {}

        for knob_name in grade_knobs_to_check:
            if knob_name not in node.knobs():
                continue  # skip if the knob does not exist

            val = node[knob_name].value()
            if isinstance(val, (tuple, list)) and any(abs(c - 1.0) > 0.001 for c in val):
                values[knob_name] = {
                    "r": round(val[0], 3),
                    "g": round(val[1], 3),
                    "b": round(val[2], 3),
                    "a": round(val[3], 3)
                }

        if values:
            export_data[channel_name] = {
                "type": "grade",
                "values": values
            }

    if not export_data:
        nuke.message("No values were changed. Nothing to export.")
        return

    export_data = dict(sorted(export_data.items()))

    class CompactEncoder(json.JSONEncoder):
        def __init__(self, *args, **kwargs):
            kwargs['indent'] = 4
            super().__init__(*args, **kwargs)

        def iterencode(self, o, _one_shot=False):
            for s in super().iterencode(o, _one_shot):
                yield s.replace('\n        "r"', ' "r"') \
                    .replace(',\n        "g"', ', "g"') \
                    .replace(',\n        "b"', ', "b"') \
                    .replace(',\n        "a"', ', "a"') \
                    .replace('\n    }', '}')

    comment = n["export_comment"].value() if "export_comment" in n.knobs() else ""

    metadata = {
        "project": data["project"],
        "season": data["season"],
        "episode": data["episode"],
        "sequence": data["sequence"],
        "shot": data["shot"],
        "passname": passname,
        "version": version,
        "script_name": script_name,
        "node": node_name,
        "export_date": datetime.now().isoformat(),
        "comment": comment
    }

    final_export = dict(sorted(export_data.items()))
    final_export["_meta"] = metadata

    with open(export_path, "w") as f:
        json.dump(final_export, f, cls=CompactEncoder)

    nuke.message(f"File exported:\n{export_path}")


def get_active_lightgrade_node():
    # Step 1: explicit selection
    for node in nuke.selectedNodes():
        if node.Class() == 'Group' and node.name().startswith('dD_lightgrade'):
            return node

    # Step 2: fallback via current context
    try:
        n = nuke.thisNode()
        if n.Class() == 'Group' and n.name().startswith('dD_lightgrade'):
            return n
    except:
        pass

    return None

def gizmo_add_layer():
    node = nuke.thisNode()
    if not node:
        return

    # Iterate all widgets to find LayerManagerUI
    for widget in QtWidgets.QApplication.allWidgets():

        if widget.objectName() == "LayerManagerUI":
            indexes = widget.channel_list_widget.selectedIndexes()

            if not indexes:
                nuke.message("Please select a layer.")
                return
            layer = indexes[0].data()

            add_layer_to_lightgrade(node, layer)
            return

    nuke.message("Layer Manager must be open to use this button.")


def hide_all_knobs(node):
    for i in range(0, 8):
        for suffix in ['in', 'disable', 'solo']:
            knob_name = f"aov_in{i}_{suffix}"
            if knob_name in node.knobs():
                try:
                    node[knob_name].setVisible(False)
                    node[knob_name].setFlag(nuke.INVISIBLE)
                except Exception:
                    pass


    node = nuke.thisNode()
    if not node:
        return

    for i in range(1, 9):
        for suffix in ['in', 'disable', 'solo']:
            knob_name = f"aov_in{i}_{suffix}"
            if knob_name in node.knobs():
                knob = node[knob_name]
                if suffix == 'in':
                    knob.setValue("none")
                knob.setVisible(False)
                # knob.setFlag(nuke.INVISIBLE)

    if "layer_count" in node.knobs():
        node["layer_count"].setValue(0)

    # Remove Link_Knobs tied to AOV if still invisible (.gizmo case)
    for knob in list(node.knobs().values()):
        if knob.Class() == "Link_Knob":
            link_target = knob.toScript().strip().strip('"')
            if link_target.startswith("aov_in") and link_target.endswith("_in"):
                # If this Link_Knob is still INVISIBLE (cannot be recovered dynamically), remove it
                if knob.hasFlag(nuke.INVISIBLE):
                    node.removeKnob(knob)

    # Dynamically recreate all Link_Knobs so they are always ready to be reactivated
    for i in range(1, 9):
        recreate_link_knob(node, i)

def clear_all_layers():
    node = nuke.thisNode()
    if not node:
        return

    for i in range(1, 9):
        for suffix in ['in', 'disable', 'solo']:
            knob_name = f"aov_in{i}_{suffix}"
            if knob_name in node.knobs():
                knob = node[knob_name]
                if suffix == 'in':
                    knob.setValue("none")
                    knob.setVisible(True)

    if "layer_count" in node.knobs():
        node["layer_count"].setValue(0)
    if "label" in node.knobs():
        node["label"].setValue("")
    if "autolabel" in node.knobs():
        node["autolabel"].setValue("")


    # Hide or remove AOV Link_Knobs
    for knob in list(node.knobs().values()):
        if knob.Class() == "Link_Knob":
            link_target = knob.toScript().strip().strip('"')
            dD_log.debug(f"link_target:{link_target}")
            if link_target.startswith("aov_in") and link_target.endswith("_in"):
                knob.setVisible(True)
                if knob.hasFlag(nuke.INVISIBLE):
                    node.removeKnob(knob)

    # # Dynamically recreate all Link_Knobs (AOV1-8)
    # for i in range(1, 9):
    #     recreate_link_knob(node, i)

def recreate_link_knob(node, index):
    try:
        if not isinstance(index, int) or not (1 <= index <= 8):
            return

        target_knob = f"aov_in{index}_in"
        link_knob_name = f"link_layer_aov{index}"

        if link_knob_name in node.knobs():
            node.removeKnob(node[link_knob_name])

        link = nuke.Link_Knob(link_knob_name, f"Layer AOV{index}", target_knob)
        link.setVisible(False)
        link.setEnabled(False)
        link.clearFlag(nuke.INVISIBLE)
        node.addKnob(link)

    except Exception as e:
        pass

def get_next_available_slot(node):
    ''' get the index of the first free slot '''
    if not node:
        nuke.message("Node not found.")
        return None

    for i in range(1, 9):
        knob_name = f"aov_in{i}_in"
        if knob_name in node.knobs():
            if node[knob_name].value().strip().lower() in ['', 'none']:
                return i
    return None

def add_layer_to_lightgrade(active_node, item):
    lightgrade_node = nuke.toNode(active_node) if isinstance(active_node, str) else active_node
    if not lightgrade_node:
        nuke.message('No LightGrade node selected.')
        return

    layer_to_add = item
    index = get_next_available_slot(lightgrade_node)

    if index is None or index > 8:
        nuke.message("You have reached the maximum limit of 8 AOV layers.")
        return

    if index == 0:
        return

    input_knob = f"aov_in{index}_in"
    disable_knob = f"aov_in{index}_disable"
    solo_knob = f"aov_in{index}_solo"

    if input_knob not in lightgrade_node.knobs():
        return

    # Apply the layer
    lightgrade_node[input_knob].setValue(layer_to_add)
    reveal_knobs(lightgrade_node, [input_knob, disable_knob, solo_knob])

    # Hide all other AOV Link_Knobs
    for knob in lightgrade_node.knobs().values():
        if knob.Class() == "Link_Knob":
            link_target = knob.toScript().strip().strip('"')
            if link_target.startswith("aov_in") and link_target.endswith("_in"):
                knob.setVisible(False)

    # Show or recreate the associated Link_Knob
    for knob in lightgrade_node.knobs().values():
        if knob.Class() == "Link_Knob":
            link_target = knob.toScript().strip().strip('"')
            if link_target == input_knob:
                knob.setVisible(True)
                try: knob.clearFlag(nuke.INVISIBLE)
                except: pass
                try: knob.setEnabled(True)
                except: pass
                break
    else:
        recreate_link_knob(lightgrade_node, index)

    # Show all valid AOVs
    for i in range(1, 9):
        key = f"aov_in{i}_in"
        if key in lightgrade_node.knobs():
            val = lightgrade_node[key].value()
            if val and val.lower() != 'none':
                reveal_list = [key, f"aov_in{i}_disable", f"aov_in{i}_solo"]
                reveal_knobs(lightgrade_node, reveal_list)

    # Increment the layer_count
    if "layer_count" in lightgrade_node.knobs():
        count = int(lightgrade_node["layer_count"].value())
        lightgrade_node["layer_count"].setValue(count + 1)

    update_layer_label(lightgrade_node)


def reveal_knobs(node, knob_names):
    """
    Shows the specified knobs on the given node (typically a LightGrade).
    """
    for name in knob_names:
        if name in node.knobs():
            knob = node.knobs()[name]  # important: avoid node[name]
            knob.setVisible(True)
            knob.clearFlag(nuke.INVISIBLE)
