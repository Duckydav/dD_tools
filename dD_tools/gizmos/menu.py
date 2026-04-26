#############################################################
# dD_tools/gizmos/menu.py
# Add gizmos to the Nuke Nodes menu (side bar).
# duckyDave - March 2026
#############################################################


import nuke
import os
_icon_dir = os.path.join(os.path.dirname(__file__), 'icons')
nuke.pluginAddPath(_icon_dir)


n = nuke.menu('Nodes').addMenu("dD Gizmos", icon="dD_48.png")

n.addCommand( "color/dD_LightGrade", "nuke.createNode('dD_lightgrade')" )