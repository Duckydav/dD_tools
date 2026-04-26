# ============================================================
# KnobChanged Shuffle Toggle v1.0
# Toggle knobChanged callbacks for Shuffle/Shuffle2 nodes only.
# Author: David Francois
# Copyright (c) 2024, David Francois
# ============================================================

import nuke
import builtins
import dD_log

try:
    from PySide2.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QPushButton
    from PySide2.QtCore import Qt
    HAS_PYSIDE2 = True
except ImportError:
    HAS_PYSIDE2 = False

VERSION = "1.0"
AUTHOR_LINK = "https://www.linkedin.com/in/davidfrancois/"
BACKUP_KEY = "_kc_shuffle_backup"

if not hasattr(builtins, BACKUP_KEY):
    setattr(builtins, BACKUP_KEY, [])


def credit():
    return (
        "<p style='color:#A2A1A1'>"
        "KC Shuffle<b><font color='#545454'>Toggle</font></b>"
        f" <font color='#888888'>{VERSION}</font> &copy; 2024"
        "<span style='color:#888888;'> | </span>"
        f"<a href='{AUTHOR_LINK}' style='text-decoration:none; color:#888888;'>"
        "<font size=3>DavidF</font></a>"
        "</p>"
    )


def _is_shuffle_callback(fn):
    """Identifies callbacks originating from shuffle.py."""
    name = getattr(fn, "__qualname__", "") or getattr(fn, "__name__", "")
    module = getattr(fn, "__module__", "")
    return (
        "knob_changed_callback_short" in name or
        "knob_changed_callback_long" in name or
        "shuffle" in module.lower()
    )


def _disable():
    """Disable all Shuffle knobChanged callbacks and back them up."""
    kc = nuke.callbacks.knobChangeds
    backup = []
    log_lines = []

    for node_class, callbacks in list(kc.items()):
        to_remove = [(fn, args, kwargs, node) for fn, args, kwargs, node in callbacks
                     if _is_shuffle_callback(fn)]
        for entry in to_remove:
            fn, args, kwargs, node = entry
            backup.append((node_class, fn, args, kwargs, node))
            nuke.removeKnobChanged(fn, node=node, nodeClass=node_class)
            line = f"  DISABLED [{node_class}] {fn} (node={node})"
            dD_log.debug(line)
            log_lines.append(line)

    setattr(builtins, BACKUP_KEY, backup)

    if backup:
        summary = f"[Shuffle kC] DISABLED -- {len(backup)} callback(s)."
    else:
        summary = "[Shuffle kC] No shuffle callbacks found."

    dD_log.info(summary)
    return summary, log_lines


def _enable():
    """Re-enable previously backed up Shuffle knobChanged callbacks."""
    backup = getattr(builtins, BACKUP_KEY, [])
    log_lines = []

    if not backup:
        summary = "[Shuffle kC] Backup empty -- nothing to restore."
        dD_log.info(summary)
        return summary, log_lines

    for node_class, fn, args, kwargs, node in backup:
        try:
            nuke.addKnobChanged(fn, args=args, kwargs=kwargs,
                                node=node, nodeClass=node_class)
            line = f"  RESTORED [{node_class}] {fn} (node={node})"
            dD_log.debug(line)
            log_lines.append(line)
        except Exception as e:
            line = f"  ERROR [{node_class}] {fn}: {e}"
            dD_log.error(line)
            log_lines.append(line)

    count = len(backup)
    setattr(builtins, BACKUP_KEY, [])
    summary = f"[Shuffle kC] ENABLED -- {count} callback(s) restored."
    dD_log.info(summary)
    return summary, log_lines


def _show_result(title, summary, log_lines):
    """Show a formatted result window with credits."""
    if not HAS_PYSIDE2:
        nuke.message(summary)
        return

    dialog = QDialog()
    dialog.setWindowTitle(title)
    dialog.setMinimumWidth(450)
    layout = QVBoxLayout(dialog)

    # Summary
    summary_label = QLabel(f"<b>{summary}</b>")
    layout.addWidget(summary_label)

    # Log details
    if log_lines:
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setPlainText("\n".join(log_lines))
        log_text.setMaximumHeight(200)
        layout.addWidget(log_text)

    # Credits
    credits_label = QLabel()
    credits_label.setText(credit())
    credits_label.setTextFormat(Qt.RichText)
    credits_label.setOpenExternalLinks(True)
    credits_label.setAlignment(Qt.AlignRight)
    layout.addWidget(credits_label)

    # OK button
    ok_btn = QPushButton("OK")
    ok_btn.clicked.connect(dialog.accept)
    layout.addWidget(ok_btn)

    dialog.exec_()


def run():
    """Toggle Shuffle knobChanged callbacks on/off."""
    backup = getattr(builtins, BACKUP_KEY, [])

    if backup:
        dD_log.info("[Shuffle kC] Backup detected -- ENABLING...")
        summary, log_lines = _enable()
        _show_result("KnobChanged Shuffle - Enabled", summary, log_lines)
    else:
        dD_log.info("[Shuffle kC] -- DISABLING shuffle callbacks...")
        summary, log_lines = _disable()
        _show_result("KnobChanged Shuffle - Disabled", summary, log_lines)
