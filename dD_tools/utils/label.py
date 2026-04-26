# label_v2_70.py
#
# Simplified version - Direct application without toggle
# - Removal of the dynamic_autolabel knob (temporarily disabled)
# - Direct label application without toggle logic
# - Callbacks preserved in comments for future reactivation
# - Full Shuffle2 and Cryptomatte support via dedicated modules
#
# Changes v2.70:
# - Disabled ensure_dynamic_autolabel_knob() (no longer creates the knob)
# - Simplified run() for direct application only
# - Callbacks inject_*_knobChanged() disabled but preserved in comments

import nuke
from PySide2 import QtWidgets
import sys
import os

# Relative imports from the layermanager package
import utils_fonctions
import shuffle
import crypto_tool
import label_generator
from utils_fonctions import format_knob_value, format_grade_knob_value
from utils_fonctions import get_version_from_filename

import dD_log


# Default dynamic knobs - Extended configuration
DEFAULT_KNOBS_BY_CLASS = {
    "Grade": ["blackpoint", "whitepoint", "black", "white", "multiply", "gamma"],
    "ColorCorrect": ["saturation", "contrast", "gain", "gamma", "offset"],
    "Saturation": ["saturation"],
    "Toe2": ["lift"],
    "HueShift": ["ingray", "outgray", "saturation", "hue_rotation", "brightness"],
}


_VERSION_ = get_version_from_filename(__file__)
dD_log.info(f"_VERSION_:{_VERSION_}")

def _module_name_from_version():
    v = get_version_from_filename(__file__)   # e.g.: 'v2_6' or 'v2.6'
    return f"label_{v.replace('.', '_')}"     # -> 'label_v2_6'


class LabelPrefsPanel(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(LabelPrefsPanel, self).__init__(parent)
        self.setWindowTitle("Label Preferences")
        self.setMinimumWidth(600)

        self.group = "LabelPrefs"
        self.prefs = nuke.toNode("preferences")
        self.inputs = {}

        layout = QtWidgets.QVBoxLayout(self)
        grid = QtWidgets.QGridLayout()

        self.nodes = [
            ("LightGrade", True),
            ("Grade", True),
            ("ColorCorrect", True),
            ("Saturation", True),
            ("Toe2", True),
            ("HueShift", True),
            ("Shuffle2", True),
            ("Cryptomatte", True),
        ]

        for row, (cls, enabled_default) in enumerate(self.nodes):
            key = cls.lower()
            knob_field = f"{self.group}_knobs_{key}"
            knob_enable = f"label_enable_{key}_autolabel"

            # Retrieve existing values or use defaults
            if self.prefs and self.prefs.knob(knob_field):
                knobs_str = self.prefs[knob_field].value()
            else:
                default_knobs = DEFAULT_KNOBS_BY_CLASS.get(cls, [])
                knobs_str = ", ".join(default_knobs)

            enabled = self.prefs[knob_enable].value() if self.prefs and self.prefs.knob(
                knob_enable) else enabled_default

            label = QtWidgets.QLabel(cls)
            field = QtWidgets.QLineEdit(knobs_str)
            checkbox = QtWidgets.QCheckBox("Disable")
            checkbox.setChecked(not enabled)

            grid.addWidget(label, row, 0)
            grid.addWidget(field, row, 1)
            grid.addWidget(checkbox, row, 2)

            self.inputs[cls] = (field, checkbox)

        layout.addLayout(grid)

        btn_layout = QtWidgets.QHBoxLayout()
        apply_btn = QtWidgets.QPushButton("Apply")
        reset_btn = QtWidgets.QPushButton("Reset by Default")
        close_btn = QtWidgets.QPushButton("Close")
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(reset_btn)
        btn_layout.addWidget(close_btn)

        apply_btn.clicked.connect(self.apply)
        reset_btn.clicked.connect(self.reset_defaults)
        close_btn.clicked.connect(self.close)

        layout.addLayout(btn_layout)

    def apply(self):
        for cls, (field, checkbox) in self.inputs.items():
            key = cls.lower()
            knob_field = f"LabelPrefs_knobs_{key}"
            knob_enable = f"label_enable_{key}_autolabel"

            if self.prefs.knob(knob_field):
                self.prefs[knob_field].setValue(field.text())
            if self.prefs.knob(knob_enable):
                self.prefs[knob_enable].setValue(not checkbox.isChecked())

            dD_log.info(f"[Apply] {cls:<12} | knobs: {field.text()} | enabled: {not checkbox.isChecked()}")

    def reset_defaults(self):
        for cls, (field, checkbox) in self.inputs.items():
            key = cls.lower()
            knob_field = f"LabelPrefs_knobs_{key}"
            knob_enable = f"label_enable_{key}_autolabel"

            default = DEFAULT_KNOBS_BY_CLASS.get(cls, [])
            default_str = ", ".join(default)
            enabled = cls not in ("LightGrade",)

            field.setText(default_str)
            checkbox.setChecked(not enabled)

            if self.prefs.knob(knob_field):
                self.prefs[knob_field].setValue(default_str)
            if self.prefs.knob(knob_enable):
                self.prefs[knob_enable].setValue(enabled)

            dD_log.info(f"[Reset] {cls:<12} | knobs: {default_str or '-'} | enabled: {enabled}")


def show_label_prefs_panel():
    panel = LabelPrefsPanel()
    panel.show()


def register_label_prefs():
    """Register preferences in Nuke"""
    prefs = nuke.toNode("preferences")
    if not prefs:
        return

    group = "LabelPrefs"

    # ALWAYS update the header with the current version
    header_knob = prefs.knob(f"{group}_header")
    if header_knob:
        header_knob.setValue(
            '<p align="center" style="font-size: 16px; font-weight: bold; color: #FCB132;">'
            f'Dynamic <span style="color:#FFFFFF;">Label</span> <font color="#888888">{_VERSION_}</font></p>'
        )

    # ALWAYS update the reset button with the current version
    reset_knob = prefs.knob(f"{group}_reset_button")
    if reset_knob:
        module_name = _module_name_from_version()
        reset_knob.setCommand(f"import {module_name} as _m\n_m.reset_label_prefs_defaults()")

    if not prefs.knob(f"{group}_tab"):
        prefs.addKnob(nuke.Tab_Knob(f"{group}_tab", "Label"))
        prefs.addKnob(nuke.Text_Knob(f"{group}_header", "",
                                     '<p align="center" style="font-size: 16px; font-weight: bold; color: #FCB132;">'
                                     f'Dynamic <span style="color:#FFFFFF;">Label</span> <font color="#888888">{_VERSION_}</font></p>'
                                     ))
        prefs.addKnob(nuke.Text_Knob(f"{group}_separator0", "", "<br>"))
        prefs.addKnob(nuke.Text_Knob(f"{group}_separator1", "", ""))

        prefs.addKnob(nuke.Text_Knob(f"{group}_explanation", "",
                                     '<p style="font-size: 11px; color: #777777; font-style: italic; text-align: justify; line-height: 2.5;">'
                                     '<ul style="list-style-type: disc; margin-left: 20px; padding-left: 0;">'
                                     '<li>This section controls the dynamic label nodes.<br>'
                                     '</ul></p>'
                                     ))

        all_nodes = [
            ("LightGrade", True),
            ("Grade", True),
            ("ColorCorrect", True),
            ("Saturation", True),
            ("Toe2", True),
            ("HueShift", True),
            ("Shuffle2", True),
            ("Cryptomatte", True),
        ]

        for cls, enabled in all_nodes:
            key = cls.lower()
            default_knobs = DEFAULT_KNOBS_BY_CLASS.get(cls, [])
            initial = ", ".join(default_knobs) if default_knobs else ""

            knobs = nuke.String_Knob(f"{group}_knobs_{key}", "", initial)
            knobs.setLabel(f"<b>{cls}</b>")
            prefs.addKnob(knobs)

            checkbox = nuke.Boolean_Knob(f"label_enable_{key}_autolabel", "Dynamic Value")
            checkbox.clearFlag(nuke.STARTLINE)
            checkbox.setValue(enabled)
            prefs.addKnob(checkbox)

        prefs.addKnob(nuke.Text_Knob(f"{group}_separator2", "", ""))
        # Create a PyScript knob that will reset all label-related preferences to their
        # factory default values. Without setting a command on the PyScript knob,
        # clicking the button does nothing. We therefore explicitly assign a
        # command that calls the helper function defined below.
        reset_btn = nuke.PyScript_Knob(f"{group}_reset_button", "Reset by Default")
        reset_btn.setTooltip("Resets all label preferences to their original state.")
        # Attach a script to the PyScript knob so it actually performs the reset
        # when clicked. The command imports this module and invokes
        # reset_label_prefs_defaults(), which performs the reset logic.
        module_name = _module_name_from_version()
        reset_btn.setCommand(f"import {module_name} as _m\n_m.reset_label_prefs_defaults()")

        prefs.addKnob(reset_btn)

        dD_log.info(f"[LabelPrefs] Preferences registered for {_VERSION_}.")


def register_label_panel():
    module_name = _module_name_from_version()
    nuke.registerWidgetAsPanel(
        f"{module_name}.LabelPrefsPanel",
        "Label Preferences",
        "uk.co.labelprefs.panel",
        True
    )


def register():
    register_label_prefs()


# -----------------------------------------------------------------------------
# Helper function invoked by the preferences "Reset by Default" button
# -----------------------------------------------------------------------------
def reset_label_prefs_defaults():
    """Reinitialize all LabelPrefs knobs to their default values.

    This function is designed to be called from the PyScript button registered in
    ``register_label_prefs``. It loops over all supported node types and writes
    the default knobs lists and enabled flags back into the Nuke preferences.

    If the preferences node cannot be obtained, nothing will happen.
    """
    prefs = nuke.toNode("preferences")
    group = "LabelPrefs"
    if not prefs:
        nuke.tprint("[LabelPrefs] Unable to find preferences node, reset aborted.")
        return

    # Define all supported node types along with whether they should be
    # enabled by default. LightGrade is disabled by default.
    all_nodes = [
        ("LightGrade", False),
        ("Grade", True),
        ("ColorCorrect", True),
        ("Saturation", True),
        ("Toe2", True),
        ("HueShift", True),
        ("Shuffle2", True),
        ("Cryptomatte", True),
    ]

    for cls, enabled in all_nodes:
        key = cls.lower()
        knob_field = f"{group}_knobs_{key}"
        knob_enable = f"label_enable_{key}_autolabel"

        # Retrieve default knobs list from the constant mapping. If no entry
        # exists, default to an empty list.
        default_knobs = DEFAULT_KNOBS_BY_CLASS.get(cls, [])
        default_str = ", ".join(default_knobs)

        # Write default list into the preferences string knob if present
        if prefs.knob(knob_field):
            prefs[knob_field].setValue(default_str)
        # Write the enabled state into the preferences boolean knob if present
        if prefs.knob(knob_enable):
            prefs[knob_enable].setValue(enabled)

        # Verbose logging for debug: show what values were restored
        try:
            nuke.tprint(
                f"[LabelPrefs Reset] {cls:<12} | knobs: {default_str or '-'} | enabled: {enabled}"
            )
        except Exception:
            # In case nuke.tprint is not available (e.g. outside of Nuke's UI),
            # fallback to dD_log so that unit tests can still see output.
            dD_log.info(
                f"[LabelPrefs Reset] {cls:<12} | knobs: {default_str or '-'} | enabled: {enabled}"
            )

    # Indicate that the reset completed successfully
    try:
        nuke.tprint("[LabelPrefs] Preferences reset to defaults.")
    except Exception:
        dD_log.info("[LabelPrefs] Preferences reset to defaults.")


def get_dynamic_knobs_from_prefs():
    """Retrieve configured knobs from preferences"""
    prefs = nuke.toNode("preferences")
    group = "LabelPrefs"
    result = {}

    # Full list of supported classes
    supported_classes = ["Grade", "ColorCorrect", "Saturation", "Toe2", "HueShift", "Shuffle2", "Cryptomatte"]

    for cls in supported_classes:
        field_name = f"{group}_knobs_{cls.lower()}"

        # If preferences exist, use them
        if prefs and prefs.knob(field_name):
            raw = prefs[field_name].value()
            knobs = [k.strip() for k in raw.split(",") if k.strip()]
            if knobs:
                result[cls] = knobs
        # Otherwise use default values
        elif cls in DEFAULT_KNOBS_BY_CLASS:
            result[cls] = DEFAULT_KNOBS_BY_CLASS[cls]

    return result


def debug_label(msg):
    """Label-specific debug output"""
    prefs = nuke.toNode("preferences")
    if prefs and prefs.knob("LabelPrefs_debug_mode") and prefs["LabelPrefs_debug_mode"].value():
        nuke.tprint(f"[Label] {msg}")


def is_lightgrade_enabled():
    """Check whether LightGrade is enabled in preferences"""
    prefs = nuke.toNode("preferences")
    if prefs and prefs.knob("label_enable_lightgrade_autolabel"):
        return prefs["label_enable_lightgrade_autolabel"].value()
    return True  # Enabled by default


def update_label_from_values(node):
    """
    Corrected version that uses format_grade_knob_value for standard nodes
    """
    if not node.knob("label"):
        return

    lines = []
    name = node.name()
    cls = node.Class()

    debug_label(f"Updating label for {name} ({cls})")

    # === LightGrade (Special Group) ===
    if name.startswith("dD_lightgrade"):
        debug_label(f"Processing LightGrade: {name}")
        # AOV layers
        aov_layers = []
        for i in range(1, 9):
            key = f"aov_in{i}_in"
            if node.knob(key):
                val = node[key].value()
                if val and val != "none":
                    aov_layers.append(val)
        if aov_layers:
            lines.append(" / ".join(aov_layers))
            debug_label(f"LightGrade AOV layers: {' / '.join(aov_layers)}")

        # Internal nodes
        with node:
            for sub in nuke.allNodes():
                label_knobs = get_dynamic_knobs_from_prefs()
                knob_list = label_knobs.get(sub.Class(), [])
                for k in knob_list:
                    if k in sub.knobs():
                        formatted = format_grade_knob_value(k, sub[k], sub.Class())
                        if formatted:
                            lines.append(formatted)
                            debug_label(f"LightGrade internal: {formatted}")

    # === Standard nodes (Grade, ColorCorrect, etc.) ===
    else:
        label_knobs = get_dynamic_knobs_from_prefs()
        knob_list = label_knobs.get(cls, [])

        debug_label(f"Processing {cls} with knobs: {knob_list}")

        for k in knob_list:
            if node.knob(k):
                formatted = format_grade_knob_value(k, node[k], cls)
                if formatted:
                    lines.append(formatted)
                    debug_label(f"Added to label: {formatted}")

    # Apply the label
    label_text = "\n".join(lines) if lines else ""
    node["label"].setValue(label_text)
    debug_label(f"Final label for {name}: '{label_text}'")

    # Debug info
    if not lines and cls in get_dynamic_knobs_from_prefs():
        debug_label(f"No modified values for {node.name()}, all at defaults")


# ============================================================================
# [V2.70 DISABLED] Function ensure_dynamic_autolabel_knob disabled
# ============================================================================
# Original code preserved for future reactivation:
#
# def ensure_dynamic_autolabel_knob(node):
#     """Ensures the dynamic_autolabel knob exists on the node"""
#     if not node.knob("dynamic_autolabel"):
#         debug_label(f"Adding dynamic_autolabel knob to {node.name()}")
#         knob = nuke.Boolean_Knob("dynamic_autolabel", "Dynamic Label")
#         knob.setValue(True)
#         node.addKnob(knob)
#         return True
#     return False

def ensure_dynamic_autolabel_knob(node):
    """[V2.70] DISABLED - No longer creates the dynamic_autolabel knob"""
    return False


def run(nodes=None):
    """
    [V2.70] Main function - Direct application without toggle

    Simplified mode: Directly applies the label to selected nodes.
    No dynamic_autolabel knob creation, no automatic callbacks.

    To update the label after modifying values, rerun the function.
    """
    if nodes is None:
        nodes = nuke.selectedNodes()
    if not nodes:
        return

    # Informational message
    debug_label("=" * 60)
    debug_label("[V2.70] SIMPLIFIED MODE: Direct application without callbacks")
    debug_label("=" * 60)

    def disable_label(node):
        if node.knob("label"):
            node["label"].setValue("")
            debug_label(f"Cleared label for {node.name()}")

    def force_refresh(node):
        if node.knob("label"):
            current_label = node["label"].value()
            node["label"].setValue(current_label)
            debug_label(f"Refreshed label for {node.name()}")

    for node in nodes:
        try:
            cls = node.Class()
            name = node.name()

            debug_label(f"Processing {name} ({cls})")

            # === LightGrade Groups ===
            if cls == "Group" and name.startswith("dD_lightgrade"):

                # Check global preferences
                if not is_lightgrade_enabled():
                    debug_label(f"LightGrade disabled in preferences, skipping {name}")
                    disable_label(node)
                    continue

                # [V2.70] Direct label application without toggle
                debug_label(f"Applying direct label to {name}")
                update_label_from_values(node)

                # [V2.70 DISABLED] No callback injection
                # inject_group_knobChanged(node)
                # if name.startswith("dD_lightgrade"):
                #     inject_internal_callbacks(node)

            # === Standard nodes ===
            elif cls in ("Grade", "ColorCorrect", "Saturation", "Toe2", "HueShift", "Shuffle2", "Cryptomatte"):
                # Check global preferences
                prefs = nuke.toNode("preferences")
                pref_key = f"label_enable_{cls.lower()}_autolabel"
                global_enabled = prefs[pref_key].value() if prefs and prefs.knob(pref_key) else True

                if not global_enabled:
                    debug_label(f"{cls} disabled in global preferences, skipping {name}")
                    disable_label(node)
                    continue

                # [V2.70] Direct label application without toggle
                debug_label(f"Applying direct label to {name}")
                if cls == "Shuffle2":
                    shuffle.run()
                elif cls == "Cryptomatte":
                    crypto_tool.run()
                else:
                    update_label_from_values(node)

                # [V2.70 DISABLED] No callback injection
                # inject_native_knobChanged(node)

            else:
                debug_label(f"Node '{name}' of type {cls} ignored.")

            force_refresh(node)

        except Exception as e:
            dD_log.error(f"[Label] Error on {node.name()}: {e}")
            import traceback
            traceback.print_exc()

    debug_label(f"[V2.70] Update completed for {len(nodes)} node(s).")


def test_on_grade():
    """[V2.70] Test function to verify direct application on Grade"""
    # Create a test Grade
    grade = nuke.createNode("Grade")
    grade.setName("TestGrade_v2_70")

    # Modify some values
    grade["multiply"].setValue([1.5, 1.2, 0.8, 1.0])
    grade["gamma"].setValue([0.8, 0.8, 0.8, 1.0])
    grade["blackpoint"].setValue([0.1, 0.05, 0.0, 0.0])

    # Select only this node
    for n in nuke.allNodes():
        n.setSelected(False)
    grade.setSelected(True)

    dD_log.info("")
    dD_log.info("=" * 50)
    dD_log.info("TEST GRADE V2.70 - DIRECT APPLICATION")
    dD_log.info("=" * 50)

    # First run - direct application
    dD_log.info("[RUN] First run() - direct label application...")
    run()

    # Check the result
    label = grade["label"].value()
    has_knob = grade.knob("dynamic_autolabel") is not None
    dD_log.info(f"[OK] Grade created: {grade.name()}")
    dD_log.info(f"[LABEL] Generated label: '{label}'")
    dD_log.info(f"[INFO] dynamic_autolabel knob created: {has_knob}")

    # Second run - reapplication of the label (no toggle)
    dD_log.info("")
    dD_log.info("[RUN] Second run() - label reapplication...")
    run()

    # Check the result
    label2 = grade["label"].value()
    dD_log.info(f"[LABEL] Label after second run: '{label2}'")
    dD_log.info(f"[INFO] Note: No toggle, the label is simply reapplied")

    return grade


# Direct test if executed as main script
if __name__ == "__main__":
    register_label_prefs()
    test_on_grade()
