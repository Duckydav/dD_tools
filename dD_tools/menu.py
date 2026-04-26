#############################################################
# Add menu items to Nuke menu (top menu).
# Python Scripting For Nuke
# Duckydave - February 2026
############################################################

import nuke

nuke.menu("Nuke").removeItem("dD")

m = nuke.menu("Nuke").addMenu("dD Tools", icon="dD_48.png")
