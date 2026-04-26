#-------------------------------------------------------------
# Useful functions
# Python Scripting For Nuke
# (C) 2022-2025 - Xavier Bourque
#-------------------------------------------------------------

import nuke
import sys                                   # import sys module
import os                                    # Import the os module (standard with Python)
from webbrowser import open as openUrl       # Import the open() function of the webbrowser module and rename it openUrl()


#-------------------------------------------------------------
# About box
#-------------------------------------------------------------
def about():
    try:
        from PySide2 import QtCore, QtGui, QtWidgets

        class AboutDialog(QtWidgets.QDialog):
            def __init__(self):
                super(AboutDialog, self).__init__()
                self.setWindowTitle("About dD Tools")
                self.setMinimumWidth(380)
                self.setMinimumHeight(420)

                layout = QtWidgets.QVBoxLayout()
                layout.setSpacing(10)
                layout.setContentsMargins(20, 20, 20, 20)

                # Title
                title = QtWidgets.QLabel("<font size='5' color='#e8a020'><b>dD Tools</b></font>")
                title.setAlignment(QtCore.Qt.AlignCenter)
                layout.addWidget(title)

                # Subtitle / motto
                subtitle = QtWidgets.QLabel("<font size='3' color='#aaaaaa'><i>Building Together Through Collaboration</i></font>")
                subtitle.setAlignment(QtCore.Qt.AlignCenter)
                layout.addWidget(subtitle)

                layout.addSpacing(8)

                # Separator
                line = QtWidgets.QFrame()
                line.setFrameShape(QtWidgets.QFrame.HLine)
                line.setFrameShadow(QtWidgets.QFrame.Sunken)
                line.setStyleSheet("color: #444444;")
                layout.addWidget(line)

                layout.addSpacing(8)

                # Info
                info_html = (
                    "<font size='3'>"
                    "<b>Author:</b> David Francois<br>"
                    "<b>Release:</b> 2026<br>"
                    "<b>Compatibility:</b> Nuke 12-14"
                    "</font>"
                )
                info_label = QtWidgets.QLabel(info_html)
                info_label.setAlignment(QtCore.Qt.AlignLeft)
                layout.addWidget(info_label)

                layout.addSpacing(10)

                # Description
                desc = QtWidgets.QLabel(
                    "<font size='3'>A personal collection of tools to streamline<br>"
                    "the compositing workflow in Nuke.<br><br>"
                    "Feel free to reach out!</font>"
                )
                desc.setWordWrap(True)
                desc.setAlignment(QtCore.Qt.AlignLeft)
                layout.addWidget(desc)

                layout.addSpacing(10)

                # Support section
                support_label = QtWidgets.QLabel("<font size='3' color='#e8a020'><b>Support My Work:</b></font>")
                layout.addWidget(support_label)

                coffee_btn = QtWidgets.QPushButton("Buy me a coffee")
                coffee_btn.setStyleSheet(
                    "QPushButton { background-color: #e8a020; color: #1a1a1a; border-radius: 4px; padding: 6px; font-weight: bold; }"
                    "QPushButton:hover { background-color: #f0b030; }"
                )
                coffee_btn.clicked.connect(self.open_coffee)
                layout.addWidget(coffee_btn)

                layout.addSpacing(10)

                # Connect section
                connect_label = QtWidgets.QLabel("<font size='3' color='#e8a020'><b>Connect:</b></font>")
                layout.addWidget(connect_label)

                linkedin_btn = QtWidgets.QPushButton("David Francois on LinkedIn")
                linkedin_btn.setStyleSheet(
                    "QPushButton { background-color: #e8a020; color: #1a1a1a; border-radius: 4px; padding: 6px; font-weight: bold; }"
                    "QPushButton:hover { background-color: #f0b030; }"
                )
                linkedin_btn.clicked.connect(self.open_linkedin)
                layout.addWidget(linkedin_btn)

                layout.addStretch()

                close_btn = QtWidgets.QPushButton("Close")
                close_btn.setStyleSheet(
                    "QPushButton { background-color: #555555; color: #ffffff; border-radius: 4px; padding: 6px; }"
                    "QPushButton:hover { background-color: #666666; }"
                )
                close_btn.clicked.connect(self.accept)
                layout.addWidget(close_btn)

                self.setLayout(layout)
                self.setStyleSheet("QDialog { background-color: #2a2a2a; color: #dddddd; }")

            def open_coffee(self):
                import webbrowser
                webbrowser.open('https://buymeacoffee.com/ddavidfranc')

            def open_linkedin(self):
                import webbrowser
                webbrowser.open('https://www.linkedin.com/in/davidfrancois/')

        dialog = AboutDialog()
        dialog.exec_()

    except Exception as e:
        import traceback
        traceback.print_exc()
        nuke.message("dD Tools\n\nBuilding Together Through Collaboration\n\nDavid Francois - 2026")
                                   



#-------------------------------------------------------------
# Show path to Nuke's Executable
#-------------------------------------------------------------
def showNukeExecutable():                    # Define the showNukeExecutable() function.                         
  nuke.message(sys.executable)               # Use the message() function from the nuke module to display the executable variable from the sys module
                                             

#-------------------------------------------------------------
# Show contents of NUKE_TEMP_DIR environment variable
#-------------------------------------------------------------
def showNukeTempDir():                       # Define the showNukeTempDir() function.
  nuke.message(os.environ['NUKE_TEMP_DIR'])  # Use the message() function from the nuke module
                                             # to display the value matching the key 'NUKE_TEMP_DIR' from dict environ from module os.

#-------------------------------------------------------------
# Show Python version
#-------------------------------------------------------------
def showPythonVersion():
  v1 = str(sys.version_info[0])
  v2 = str(sys.version_info[1])
  v3 = str(sys.version_info[2])
  msg = 'Python version: ' + v1 + '.' + v2 + '.' + v3
  nuke.message(msg)


#-------------------------------------------------------------
# Open Nuke Python documentation in a webbrowser
#-------------------------------------------------------------

def showGuide(guide):
  nukeVer = str(nuke.NUKE_VERSION_MAJOR) + str(nuke.NUKE_VERSION_MINOR)
  if guide == "api_ref":
      openUrl("https://learn.foundry.com/nuke/developers/122/pythonreference/")
  elif guide == "python_dev":
      openUrl("https://learn.foundry.com/nuke/developers/" + nukeVer + "/pythondevguide/index.html")
  elif guide == "panels":
      openUrl("https://learn.foundry.com/nuke/developers/" + nukeVer + "/pythondevguide/custom_panels.html")
  elif guide == "callbacks":
      openUrl("https://learn.foundry.com/nuke/developers/" + nukeVer + "/pythondevguide/callbacks.html")
  elif guide == "nukescripts":
      openUrl("https://learn.foundry.com/nuke/developers/" + nukeVer + "/pythondevguide/_autosummary/nukescripts.html")
  elif guide == "knobs":
      openUrl("https://learn.foundry.com/nuke/developers/" + nukeVer + "/ndkdevguide/knobs-and-handles/knobtypes.html")
  elif guide == "xavier_cheatsheet":
      openUrl("https://docs.google.com/spreadsheets/d/1I28KDOVjAwA95ksRF4X9AMzgYURLLtWHAWGoAPXN32U/edit?usp=sharing")


#-------------------------------------------------------------
# Show all directories in Nuke's pluginPath
#-------------------------------------------------------------
def showNukePluginPath():                    #Define the showNukePluginPath() function
  n = nuke.pluginPath()                      #Get a list of all directories in the nuke plugin path
  t = '\n'.join(n)                           #Convert the list to a string, add a new line ('\n') after each item from the list 
  p = nuke.Panel('Plugin paths')             #Create a nuke panel with window title 'Plugin Paths' and store it's memory location in variable 'p'.
  p.addNotepad('Plugin Paths:', t)           #Add a notepad knob in our panel with the label 'File Paths' and put the contents of variable 't' in it.
  p.setWidth(1600)                           #Make the panel 1600px wide
  p.show()                                   #Show the panel to the user

#-------------------------------------------------------------
# Show all currently loaded Python modules
#-------------------------------------------------------------
def showAllModules():                        #Define showAllModules() function
  l = []                                     #Create an empty list, store in variable msg
  d = sys.modules                            #Store dict 'modules' from module 'sys' in variable 'd'.
  for i in d:                                #For every key in dict d...
    l.append(str(i) + ':' + str(d[i]))       #Create a string with the key and value, append to list msg

  l.sort()                                   #Sort list msg
  msg = '\n'.join(l)                         #Convert list l to string, add a new line after each list item. Store in var msg.

  p = nuke.Panel('Python Modules')           #Create a nuke panel with window title 'Python Modules' and store panel object in variable 'p'.
  p.addNotepad('Python Modules:', msg)       #Add a notepad knob in our panel with the label 'Python Modules' and put the contents of variable 'msg' in it.
  p.setWidth(1600)                           #Make the panel 1600px wide
  p.show()                                   #Show the panel to the user

#-------------------------------------------------------------
# Show all knobs for currently selected node
#-------------------------------------------------------------
def showAllKnobs():                                      #Define function showAllKnobs()
  ls = []                                                #Store an empty list in variable ls
  sn = nuke.selectedNode()                               #Store the selected node object in variable sn
  kl = sn.knobs()                                        #Store a list of all knobs in variable kl
  for i in kl:                                           #For every item in knob list kl...
    lb = sn[i].label()                                   #Put the label in variable lb
    nm = sn[i].name()                                    #Put the knob name in variable nm
    if lb is '':                                         #If label is empty...
      if sn[i].visible() is False:                       #And if the knob is invisible...
        lb = 'INVISIBLE'                                 #Then store the string 'INVISIBLE' in variable lb
      else:                                              #Else, if the knob is visible...
        lb = nm                                          #Then store the name of the knob in variable lb
    cl = sn[i].Class()                                   #Store the knob's class in variable cl
    
    ls.append(nm + ' / ' + lb + ' / ' + cl)              #Create a string with name, label and class then append it to list 'ls'
    ls = list(dict.fromkeys(ls))                         #Remove duplicates by converting from list to dict to list
    ls.sort()                                            #Sort the list
    msg = '\n'.join(ls) 
    msg = 'NAME / LABEL / CLASS\n' + msg                 #Convert the list to a string, add a new line after each list item
    
  p = nuke.Panel('All Knobs In Node ' + sn.name())       #Create a nuke panel and store the panel object in variable p
  p.addNotepad('Knobs:', msg)                            #Add a notepad knob to the panel
  p.setWidth(1600)                                       #Set panel width to 1600 px
  p.show()                                               #Show the panel





#-------------------------------------------------------------
# Label selected nodes
#-------------------------------------------------------------
def labelSelected():                               #Define labelSelected() function
    if not nuke.selectedNodes():                   #If no nodes are selected, then...
        nuke.message("No node(s) selected.")       #Display a message to the user with the message() function of the nuke module.
        return                                     #Exit the function

    l = nuke.getInput('Label')                     #Open a dialog box to the user to get the new label and store it in variable l.
    for n in nuke.selectedNodes():                 #Loop through every item in the list of node addresses returned by nuke.selectedNodes()
        n['label'].setValue(l)                     #Set the value of the label knob to the contents of variable l
 