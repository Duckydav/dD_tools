import nuke
import os

_icon_dir = os.path.join(os.path.dirname(__file__), 'icons')
nuke.pluginAddPath(_icon_dir)

nuke.menu('Nuke').removeItem('dD')

m = nuke.menu('Nuke').addMenu('dD Tools', icon='dD_48.png')

m.addCommand("&Layer Manager...", "import layer_manager; layer_manager.run()",
             icon="layerM.png", shortcut='`')
