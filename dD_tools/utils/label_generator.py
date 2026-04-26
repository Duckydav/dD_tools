import nuke
import dD_log
from utils_fonctions import format_grade_knob_value

# Get the selected node
# node = nuke.selectedNode()
# node_class = node.Class()

def inject_knobChanged(node):
    node_class = node.Class()

    knobs = {
        "Grade": ["blackpoint", "whitepoint", "black", "white", "multiply", "add", "gamma"],
        "ColorCorrect": ["saturation", "contrast", "gain", "gamma", "offset"],
        "Saturation": ["saturation"],
        "HueShift": ["ingray", "outgray", "saturation", "color", "color_saturation", "hue_rotation", "brightness"],
        "Toe2": ["lift"]
    }

    if node_class not in knobs:
        nuke.tprint(f"[WARN] Node class {node_class} not supported for injection.")
        return

    watched = knobs[node_class]
    modulename = __name__
    code = f"""
knob = nuke.thisKnob()
node = nuke.thisNode()
watched = {watched}
section = knob.name().split(".")[0]
short = knob.name().split(".")[-1]
if section in ("shadows", "midtones", "highlights") and short in watched:
    import {modulename}
    {modulename}.value_section(section)
elif short in watched:
    import {modulename}
    {modulename}.run()
"""
    node["knobChanged"].setValue(code)
    dD_log.info(f"knobChanged injected into {node.name()} ({node_class})")


def value():
    try:
        node = nuke.selectedNode()
    except:
        try:
            node = nuke.thisNode()
        except:
            nuke.message("No active or selected node.")
            return

    node_class = node.Class()

    if node_class not in ("Group", "Grade", "ColorCorrect", "Saturation", "Toe2", "HueShift"):
        nuke.message("This script only works on Group, Grade, ColorCorrect, Saturation, Toe2, or HueShift.")
        return

    dD_log.debug(f"Selected node: {node.name()} ({node_class})")

    knobs = {
        "Grade": ["blackpoint", "whitepoint", "black", "white", "multiply", "add", "gamma"],
        "ColorCorrect": ["saturation", "contrast", "gain", "gamma", "offset"],
        "Saturation": ["saturation"],
        "HueShift": ["ingray", "outgray", "saturation", "color", "color_saturation", "hue_rotation", "brightness"],
        "Toe2": ["lift"]
    }

    watched = knobs.get(node_class, [])
    lines = []

    for k in watched:
        if node_class == "ColorCorrect":
            for section in ("shadows", "midtones", "highlights", "master"):
                knob_name = f"{section}.{k}"
                if knob_name in node.knobs():
                    val = node[knob_name].value()
                    defval = node[knob_name].defaultValue()
                    if val != defval:
                        lines.append(f"{section[:3]} {k[:3]} {round(val, 2)}")
        else:
            if k in node.knobs():
                val = node[k].value()
                defval = node[k].defaultValue()
                if val != defval:
                    lines.append(format_grade_knob_value(k, node[k], node_class))

    # Extract all aov_in*_in knobs from the group
    try:
        group_name = node["group_ref"].value()
        group_node = nuke.toNode(group_name)
    except:
        group_node = None

    # Always build the prefix with the group name and non-none AOVs
    prefix = group_name if group_node else node.name()

    layer_names = []
    if group_node:
        for i in range(1, 9):
            knob_name = f"aov_in{i}_in"
            if knob_name in group_node.knobs():
                val = group_node[knob_name].value()
                if val and val != "none":
                    layer_names.append(val)

    if layer_names:
        prefix += "\\n" + "\\n".join(layer_names)

    # Build the final label
    if lines:
        label_result = "\\n".join(lines)
        label_result = f"{prefix}\\n{label_result}"
    else:
        label_result = prefix

    node["label"].setValue(label_result)

    # Dynamic injection
    try:
        inject_knobChanged(node)
    except Exception as e:
        nuke.tprint(f"[WARN] Failed to inject knobChanged in value(): {e}")


def value_detailed():
    node = nuke.selectedNode()
    node_class = node.Class()

    if node_class != "ColorCorrect":
        nuke.message("This detailed function is only intended for ColorCorrect nodes.")
        return

    knobs_to_check = ["saturation", "contrast", "gain", "gamma", "offset"]

    # Prefixes for clear label display
    section_prefixes = {
        "shadows": "sha",
        "midtones": "mid",
        "highlights": "high"
    }

    lines = []

    # Iterate through all knobs in these sections
    for name, knob in node.knobs().items():
        parts = name.split(".")
        if len(parts) != 2:
            continue

        section, short = parts
        if section in section_prefixes and short in knobs_to_check:
            formatted = format_grade_knob_value(short, knob, node_class)
            if formatted:
                prefix = section_prefixes[section]
                lines.append(f"{prefix} {formatted}")

    label = "\\n".join(lines)
    if label:
        label = "\\n" + label
    dD_log.debug(f"Detailed label: {label}")
    node["label"].setValue(label)


def value_section(section):
    node = nuke.selectedNode()
    node_class = node.Class()
    if node_class != "ColorCorrect":
        return

    # Example: if section="midtones", only check midtones.saturation, midtones.gamma, etc.
    prefixes = {
        "shadows": "sha",
        "midtones": "mid",
        "highlights": "high"
    }
    if section not in prefixes:
        return

    knobs_to_check = ["saturation", "contrast", "gain", "gamma", "offset"]
    lines = []

    for name, knob in node.knobs().items():
        if not name.startswith(f"{section}."):
            continue

        short = name.split(".")[-1]
        if short in knobs_to_check:
            formatted = format_grade_knob_value(short, knob, node_class)
            if formatted:
                lines.append(f"{prefixes[section]} {formatted}")

    label = "\\n".join(lines)
    if label:
        label = "\\n" + label
    node["label"].setValue(label)


def clear_label():
    try:
        node = nuke.selectedNode()
        node["label"].setValue("")
        if node.knob("knobChanged"):
            node["knobChanged"].setValue("")
        dD_log.info(f"Label and knobChanged cleared for {node.name()}")
    except:
        nuke.message("No node selected for cleanup.")



def run(node=None):
    if node is None:
        try:
            node = nuke.selectedNode()
        except:
            try:
                node = nuke.thisNode()
            except:
                nuke.message("No active or selected node.")
                return


    dD_log.debug(f"Selected node: {node.name()} ({node.Class()})")

    node_class = node.Class()
    dD_log.debug(f"node_class: {node_class}")

    if node_class not in ("Group", "Grade", "ColorCorrect", "Saturation", "Toe2", "HueShift"):
        nuke.tprint(f"[SKIP] Node {node.name()} class {node_class} skipped (not supported)")
        return


    knobs_to_check = {
        "Grade": ["blackpoint", "whitepoint", "black", "white", "multiply", "add", "gamma"],
        "ColorCorrect": ["saturation", "contrast", "gain", "gamma", "offset"],
        "Saturation": ["saturation"],
        "Toe2": ["lift"],
        "HueShift": ["ingray", "outgray", "saturation", "color", "color_saturation", "hue_rotation", "brightness"]
    }.get(node_class, [])

    lines = []

    # Check if each knob should be displayed
    for name, knob in node.knobs().items():
        short = name.split(".")[-1]

        # ColorCorrect: only display master.* knobs
        if node_class == "ColorCorrect" and "." in name and not name.startswith("master."):
            continue

        # HueShift: ignore any hierarchical knobs
        if node_class == "HueShift" and "." in name:
            continue

        if short in knobs_to_check:
            v = knob.value()
            d = knob.defaultValue()
            if v != d:
                dD_log.debug(f"DIFF {short} -> v={v} | default={d}")
            else:
                continue  # skip if equal

            formatted = format_grade_knob_value(short, knob, node_class)
            if formatted:
                lines.append(formatted)

    # Find the parent group
    try:
        group_name = node["group_ref"].value()
        group_node = nuke.toNode(group_name)
    except:
        group_node = None

    prefix = group_name if group_node else node.name()

    # Extract all aov_in*_in knobs from the group
    layer_names = []
    if group_node:
        for i in range(1, 9):
            knob_name = f"aov_in{i}_in"
            if knob_name in group_node.knobs():
                val = group_node[knob_name].value()
                if val and val != "none":
                    layer_names.append(val)

    if layer_names:
        formatted_layers = [name.replace("lg_", "") if name.startswith("lg_") else name for name in layer_names]
        prefix += "\n" + "\n".join(formatted_layers)

    if lines:
        # Do not include prefix here as it is already handled at the Group level
        label_result = f"{prefix}\n" + "\n".join(lines)


    else:
        # Do not modify if no values have changed
        return

    # Do not reformat for a node inside a Group (already handled)
    if group_node is None:
        label_result = "\n".join(lines)
    else:
        pass

    node["label"].setValue(label_result)

    # Inject knobChanged after label update
    try:
        inject_knobChanged(node)
    except Exception as e:
        nuke.tprint(f"[WARN] Failed to inject knobChanged in run(): {e}")
