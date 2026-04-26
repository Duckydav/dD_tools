import nuke
import os
import label
import dD_tools

_icon_dir = os.path.join(os.path.dirname(__file__), 'icons')
nuke.pluginAddPath(_icon_dir)

nuke.menu('Nuke').removeItem('dD')

m = nuke.menu('Nuke').addMenu('dD Tools', icon='dD_48.png')

m.addCommand("&Layer Manager...", "import layer_manager; layer_manager.run()",
             icon="layerM.png", shortcut='`')

# Utilities sub-menu
m_utils = m.addMenu("Utilities", icon="utils.png")
m_utils.addCommand("Label auto", "label.run()", "V", icon="label.png")
m_utils.addCommand("$GUI", "import dD_gui; dD_gui.run()", icon="toggle.png", shortcut='alt+D')
m_utils.addCommand("$GUI Settings", "import dD_gui; dD_gui.setting()")
m_utils.addCommand("$GUI All", "import dD_gui; dD_gui.run_all()", shortcut='shift+alt+D')
m_utils.addCommand("Viewer Caller", "import dD_viewer_caller; dD_viewer_caller.run()", icon="viewer.png", shortcut='alt+W')
m_utils.addCommand("KC Shuffle Toggle...", "import kc_shuffle_toggle; kc_shuffle_toggle.run()")
m_utils.addCommand("KC All Toggle...", "import kc_toggle; kc_toggle.run()", icon="callback.png")

#Info sub-menu
m_info = m.addMenu("Info Nuke", icon="info.png")
m_info.addCommand("Show Plugin Path...", "dD_tools.showNukePluginPath()")
m_info.addCommand("Show Loaded Modules...", "dD_tools.showAllModules()")
m_info.addCommand("Show Python Version...", "dD_tools.showPythonVersion()")
m_info.addCommand("Show Knobs (Selected Node)...", "dD_tools.showAllKnobs()")

m.addSeparator()
m.addCommand("About duckyDave...", "dD_tools.about()", icon="dD_48.png")

