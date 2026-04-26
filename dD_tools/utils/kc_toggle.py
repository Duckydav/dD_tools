# ============================================================
# KnobChanged Toggle v1.0
# Toggle ALL knobChanged callbacks on/off (in-memory backup).
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
BACKUP_KEY = "_kc_backup"

if not hasattr(builtins, BACKUP_KEY):
    setattr(builtins, BACKUP_KEY, {})


def credit():
    return (
        "<p style='color:#A2A1A1'>"
        "KC<b><font color='#545454'>Toggle</font></b>"
        f" <font color='#888888'>{VERSION}</font> &copy; 2024"
        "<span style='color:#888888;'> | </span>"
        f"<a href='{AUTHOR_LINK}' style='text-decoration:none; color:#888888;'>"
        "<font size=3>DavidF</font></a>"
        "</p>"
    )


def _disable():
    """Disable all knobChanged callbacks and back them up."""
    kc = nuke.callbacks.knobChangeds
    log_lines = []

    if not kc:
        summary = "[knobChanged] Nothing to disable."
        dD_log.info(summary)
        return summary, log_lines

    # Deep copy entries before clearing
    backup = {}
    for node_class, callbacks in list(kc.items()):
        backup[node_class] = list(callbacks)

    setattr(builtins, BACKUP_KEY, backup)
    kc.clear()

    total = sum(len(v) for v in backup.values())
    summary = f"[knobChanged] DISABLED -- {total} callback(s) backed up across {len(backup)} class(es)."
    dD_log.info(summary)

    for cls, cbs in backup.items():
        for fn, args, kwargs, node in cbs:
            line = f"  [{cls}] {fn}"
            dD_log.debug(line)
            log_lines.append(line)

    return summary, log_lines


def _enable():
    """Re-enable all previously backed up knobChanged callbacks."""
    backup = getattr(builtins, BACKUP_KEY, {})
    log_lines = []

    if not backup:
        summary = "[knobChanged] Backup empty -- nothing to restore."
        dD_log.info(summary)
        return summary, log_lines

    restored = 0
    for node_class, callbacks in backup.items():
        for fn, args, kwargs, node in callbacks:
            try:
                nuke.addKnobChanged(fn, args=args, kwargs=kwargs, nodeClass=node_class)
                restored += 1
                line = f"  RESTORED [{node_class}] {fn}"
                dD_log.debug(line)
                log_lines.append(line)
            except Exception as e:
                line = f"  ERROR [{node_class}] {fn}: {e}"
                dD_log.error(line)
                log_lines.append(line)

    setattr(builtins, BACKUP_KEY, {})
    summary = f"[knobChanged] ENABLED -- {restored} callback(s) restored."
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
    """Toggle all knobChanged callbacks on/off."""
    if nuke.callbacks.knobChangeds:
        dD_log.info("[knobChanged] Active callbacks detected -- DISABLING...")
        summary, log_lines = _disable()
        _show_result("KnobChanged - Disabled", summary, log_lines)
    else:
        dD_log.info("[knobChanged] No active callbacks -- ENABLING from backup...")
        summary, log_lines = _enable()
        _show_result("KnobChanged - Enabled", summary, log_lines)
