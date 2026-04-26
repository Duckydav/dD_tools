# ----------------------------------------------------------------------------------------------------------
# viewer_caller v1.1
# Author: David Francois
# Copyright (c) 2024, David Francois
# ----------------------------------------------------------------------------------------------------------

"""
Viewer Caller - Locate and organize Viewer nodes in Nuke's Node Graph.
"""

import nuke


def run():
    """Find all Viewer nodes and align them at the bottom of the current view."""
    viewer_nodes = [node for node in nuke.allNodes() if node.Class() == "Viewer"]

    if not viewer_nodes:
        nuke.message("No Viewer found in the script!")
        return

    # Sort Viewers by name (alphanumeric order)
    viewer_nodes.sort(key=lambda v: v['name'].value())

    # Get the current center position and zoom level
    current_center = nuke.center()
    zoom_level = nuke.zoom()

    center_x, center_y = current_center[0], current_center[1]
    spacing = 100  # Horizontal spacing between Viewers

    # Position Viewers at the bottom of the current view
    start_x = center_x - (len(viewer_nodes) - 1) * spacing // 2
    adjusted_y = center_y + (200 / zoom_level)

    for i, viewer in enumerate(viewer_nodes):
        viewer.setXpos(int(start_x + i * spacing))
        viewer.setYpos(int(adjusted_y))
