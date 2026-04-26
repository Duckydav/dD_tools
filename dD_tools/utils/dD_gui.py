# ----------------------------------------------------------------------------------------------------------
# $GUI v1.2
# Author: David Francois
# Copyright (c) 2024, David Francois
# ----------------------------------------------------------------------------------------------------------

import nuke
import json
import os
import dD_log

# Path to the JSON settings file (next to this script)
SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "dD_gui_settings.json")


def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        initial_settings = {
            "node_names": ["defocus", "vector", "denoise"],
            "filter_type": "name"
        }
        save_settings(initial_settings)
        return initial_settings

    with open(SETTINGS_PATH, 'r') as file:
        return json.load(file)


def save_settings(settings):
    """Save the settings to the JSON file."""
    with open(SETTINGS_PATH, 'w') as file:
        json.dump(settings, file, indent=4)


def setting():
    settings = load_settings()
    node_names = settings.get("node_names", [])
    filter_type = settings.get("filter_type", "name")

    # Rearrange the order so the saved choice is first
    filter_options = ["name", "class"]
    if filter_type == "class":
        filter_options.reverse()

    node_identifier_key = "Node Identifiers\n\n(list separated by commas)"

    # UI Panel
    panel = nuke.Panel("$GUI Settings")
    panel.addEnumerationPulldown("Filter by", " ".join(filter_options))
    panel.addNotepad(node_identifier_key, ", ".join(node_names))

    if panel.show():
        new_filter_type = panel.value("Filter by")
        new_identifiers = panel.value(node_identifier_key)
        if new_identifiers:
            new_identifiers = new_identifiers.strip().split(',')
        else:
            new_identifiers = []

        settings["filter_type"] = new_filter_type
        settings["node_names"] = [name.strip().lower() for name in new_identifiers if name.strip()]
        save_settings(settings)


def run_all():
    settings = load_settings()
    node_identifiers = [name.lower() for name in settings.get("node_names", [])]
    filter_type = settings.get("filter_type", "name")

    for node in nuke.allNodes():
        if filter_type == "name":
            match = any(identifier in node.name().lower() for identifier in node_identifiers)
        else:  # filter_type == "class"
            match = any(identifier in node.Class().lower() for identifier in node_identifiers)

        if match:
            disable_knob = node['disable']
            if disable_knob.isAnimated():
                disable_knob.clearAnimated()
                disable_knob.setValue(0)
                dD_log.info(f"Animation cleared and {node.name()} disabled.")
            else:
                disable_knob.setExpression("$gui")
                disable_knob.setValue(1)
                dD_log.info(f"Expression $gui added and {node.name()} enabled.")


def run():
    """Toggle $gui expression on selected nodes."""
    selected_nodes = nuke.selectedNodes()
    if not selected_nodes:
        nuke.message("No nodes selected.")
        return

    for node in selected_nodes:
        disable_knob = node['disable']
        current_expression = disable_knob.toScript().strip()

        if "$gui" in current_expression:
            # Remove the $gui expression and reset
            disable_knob.setExpression("")
            disable_knob.clearAnimated()
            disable_knob.setValue(0)
            dD_log.info(f"Expression '$gui' removed for {node.name()}.")
        else:
            # Add the $gui expression
            disable_knob.clearAnimated()
            disable_knob.setExpression("$gui")
            dD_log.info(f"Expression '$gui' added to {node.name()}.")
