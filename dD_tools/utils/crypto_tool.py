# ----------------------------------------------------------------------------#
#-------------------------------------------------------------------- HEADER --#

"""
@author:
    dfrancois

@description:
    - Find selection's name from object with cryptomatte.

@applications
    - nuke

"""

#------------------------------------------------------------------------------#
#------------------------------------------------------------------- IMPORTS --#

# third-party
import nuke
import re
import json
import os
import sys


# Logging
try:
    import dD_log
except ImportError:
    import logging as dD_log
    dD_log.basicConfig(level=dD_log.DEBUG)

# external
from PySide2.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QLabel,
    QListWidget, QFileDialog, QDesktopWidget, QMainWindow, QFrame, QGroupBox
)
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtCore import Qt, QTimer

# Authorization: always enabled for open-source distribution
USER_IS_AUTHORIZED = True

# Preferences path relative to this module
PREFERENCE_DIR = os.path.dirname(__file__)
PREFERENCE_PATH = os.path.join(PREFERENCE_DIR, "crypto-tool_pref.json")
dD_log.debug(f"Pref_dir: {PREFERENCE_DIR}")
dD_log.debug(f"Pref_path: {PREFERENCE_PATH}")


#----------------------------------------------------------------------------#
#----------------------------------------------------------------- CLASSES --#

setup_window = None

def create_main_window():
    """
    Creates and returns an instance of the main window.
    """
    window = QMainWindow()
    return window


class MainUI(QWidget):
    def __init__(self, parent=None, show_window=True):
        super(MainUI, self).__init__(parent, Qt.WindowStaysOnTopHint)
        self.click_timer = QTimer()
        self.click_timer.setSingleShot(True)
        self.is_double_click = False
        # Attribute initialization
        self.preferences_path = PREFERENCE_PATH

        self.keywords = []
        self.symbols = []
        self.character_names = []
        self.node_state = {}
        self.excluded_words = []
        self.singular_dict = {}

        # UI field initialization
        self.keywords_edit = None
        self.symbols_edit = None
        self.exclude_words_edit = None
        self.uniform_text_checkbox = None
        self.singularize_checkbox = None
        self.clear_twin_words_checkbox = None
        self.remove_duplicates_checkbox = None
        self.remove_character_checkbox = None
        self.remove_character_edit = None
        self.sort_alphabetically_checkbox = None

        # UI setup
        self.initUI()

        # Connectors
        self.enable_exclude_words_checkbox.stateChanged.connect(self.toggle_exclude_words_edit)

        # Load preferences after initialization
        self.load_preferences()

        if show_window:
            self.show()


    def check_box(self, checked=False):
        widget = QtWidgets.QCheckBox()
        widget.setChecked(bool(checked))
        return widget

    def button(self, label):
        widget = QtWidgets.QPushButton()
        widget.setText(label)
        return widget

    def initUI(self):
        """
        Initializes the user interface.
        """
        main_layout = QVBoxLayout()



        # Main title
        main_layout.addWidget(self.create_title("CryptoTool"))

        # SECTION : Explanation
        # Separator line
        line_explanation = QFrame()
        line_explanation.setFrameShape(QFrame.HLine)
        line_explanation.setFrameShadow(QFrame.Sunken)
        line_explanation.setStyleSheet("color: #555555;")
        main_layout.addWidget(line_explanation)

        # Explanation label
        explanation_label = QLabel()
        explanation_label.setText(
            '<p style="font-size: 11px; color: #A2A1A1; font-style: italic; text-align: justify;">'
            'This panel allows you to clean and simplify <b>Cryptomatte</b> selections:<br><br>'
            '<ul style="margin-left: -15px;">'
            '<li>Filter out numbers, isolated capital letters, unwanted words or symbols</li>'
            '<li>Convert names to singular form using a customizable dictionary</li>'
            '<li>Remove repeated or duplicated words (twins)</li>'
            '<li>Reorder, exclude, or rename layers more clearly</li>'
            '<li>Dynamically display the cleaned selection in the node\'s label</li>'
            '</ul>'
            '</p>'

        )
        explanation_label.setWordWrap(True)
        main_layout.addWidget(explanation_label)

        # Bottom separator line
        line_explanation_bottom = QFrame()
        line_explanation_bottom.setFrameShape(QFrame.HLine)
        line_explanation_bottom.setFrameShadow(QFrame.Sunken)
        line_explanation_bottom.setStyleSheet("color: #555555;")
        main_layout.addWidget(line_explanation_bottom)

        # SECTION 2 : Preferences Options
        self.remove_digits_checkbox = self.check_box()
        self.remove_digits_checkbox.setText("Clear numbers")

        self.remove_uppercase_checkbox = self.check_box()
        self.remove_uppercase_checkbox.setText("Clear caps 'alone'")

        self.enable_exclude_words_checkbox = self.check_box()
        self.enable_exclude_words_checkbox.setText("Exclusion words")
        self.exclude_words_edit = QLineEdit()
        self.exclude_words_edit.setPlaceholderText("Words to remove (up, down,Alt, upper,... )")

        self.clear_symbols_checkbox = self.check_box()
        self.clear_symbols_checkbox.setText("Clear symbols")
        self.clear_symbols_edit = QLineEdit()
        self.clear_symbols_edit.setPlaceholderText("Symbols to remove (ex: -_:.)")

        self.uniform_text_checkbox = self.check_box()
        self.uniform_text_checkbox.setText("Standardize text")

        self.singularize_checkbox = self.check_box()
        self.singularize_checkbox.setText("Format to singular")
        self.singular_edit = QLineEdit()


        self.clear_twin_words_checkbox = self.check_box()
        self.clear_twin_words_checkbox.setText("Clear Twins words")

        self.remove_duplicates_checkbox = self.check_box()
        self.remove_duplicates_checkbox.setText("Clear duplicates words")

        self.remove_character_checkbox = self.check_box()
        self.remove_character_checkbox.setText("Clear character's names")

        self.remove_character_edit = QLineEdit()

        self.sort_alphabetically_checkbox = self.check_box()
        self.sort_alphabetically_checkbox.setText("Sort alphabetically")

        main_layout.addWidget(self.create_group_box(
            "Preferences Options",
            [
                self.remove_digits_checkbox,
                self.remove_uppercase_checkbox,
                self.enable_exclude_words_checkbox,
                self.exclude_words_edit,
                self.clear_symbols_checkbox,
                self.clear_symbols_edit,
                self.uniform_text_checkbox,
                self.singularize_checkbox,
                self.singular_edit,
                self.clear_twin_words_checkbox,
                self.remove_duplicates_checkbox,
                self.remove_character_checkbox,
                self.remove_character_edit,
                self.sort_alphabetically_checkbox,
            ]
        ))

        # SECTION 3 : Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()

        self.extract_names_button = self.button("Get View / Get short (double click)")
        self.extract_names_button.clicked.connect(self.on_extract_button_clicked)
        self.extract_names_button.mouseDoubleClickEvent = self.on_extract_button_double_clicked

        actions_layout.addWidget(self.extract_names_button)
        self.channel_list_widget = QListWidget()
        self.info_label = QLabel("Select 0 / Duplicate 0 / Out 0")

        actions_layout.addWidget(self.info_label)
        actions_layout.addWidget(self.channel_list_widget)

        actions_group.setLayout(actions_layout)
        main_layout.addWidget(actions_group)

        self.save_button = self.button('Save Preferences')
        self.save_button.clicked.connect(self.save_preferences)
        main_layout.addWidget(self.save_button)

        self.load_preferences_button = self.button('Load Preferences')
        self.load_preferences_button.clicked.connect(self.load_preferences_from_file)
        main_layout.addWidget(self.load_preferences_button)

        # SECTION 4 : Credits
        main_layout.addWidget(self.create_credits())

        # Final configuration
        self.setLayout(main_layout)
        self.setWindowTitle("Preferences")
        self.setGeometry(300, 300, 500, 800)

    def create_title(self, text):
        """
        Creates a formatted title for the main window.
        """
        title_label = QLabel(
            '<p align="center" style="font-size: 18px; font-weight: bold; color: #FCB132; margin: 0;">'
            'Crypto <span style="color: #FFFFFF;">Tool</span>'
            '</p>'
        )
        return title_label

    def create_group_box(self, title, widgets_list):
        """
        Creates a QGroupBox with a title and a list of widgets.
        """
        group_box = QGroupBox(title)
        layout = QVBoxLayout()
        for widget in widgets_list:
            layout.addWidget(widget)
        group_box.setLayout(layout)
        return group_box

    def create_checkbox(self, text):
        """
        Creates a checkbox with the given text.
        """
        checkbox = widgets.check_box(False)
        checkbox.setText(text)
        return checkbox

    def create_credits(self):
        """
        Creates the credits section.
        """
        credits_label = QLabel(
            '<p align="center" style="font-size: 11px;">'
            '<a href="https://github.com/Duckydav" style="text-decoration:none; color:#A2A1A1">'
            'Crypto<b><font color="#545454"> Tool</font></b> v02 &copy; 2024</a>'
            '<span style="color:#888888;"> | </span>'
            '<a href="https://www.linkedin.com/in/davidfrancois/" style="text-decoration:none; color:#888888;">DavidF</a>'
            '<span style="color:#888888;"> | </span>'
            '<a href="https://your-doc-link.com" style="text-decoration:none; color:#FCB132;">help</a>'
            '</p>'
        )
        credits_label.setOpenExternalLinks(True)
        credits_label.setStyleSheet("font-size: 12px; color: #bbbbbb;")
        return credits_label

    def toggle_exclude_words_edit(self, state):
        """
        Enables or disables the excluded words edit field.
        """
        isEnabled = state == Qt.Checked
        self.exclude_words_edit.setEnabled(isEnabled)

        if isEnabled:
            self.exclude_words_edit.setText(', '.join(self.excluded_words))
        else:
            self.exclude_words_edit.setText("")

    def on_extract_button_clicked(self):
        pass

    def on_extract_button_double_clicked(self, event):
        pass

    def on_extract_button_clicked(self):
        if not self.is_double_click:
            self.click_timer.timeout.connect(self.single_extract_click_action)
            self.click_timer.start(175)
        self.is_double_click = False

    def on_extract_button_double_clicked(self, event):
        self.is_double_click = True
        self.click_timer.stop()
        self.double_extract_click_action()

    def on_get_button_clicked(self):
        if not self.is_double_click:
            self.click_timer.timeout.connect(self.single_get_click_action)
            self.click_timer.start(250)
        self.is_double_click = False

    def on_get_button_double_clicked(self, event):
        self.is_double_click = True
        self.click_timer.stop()
        self.double_get_click_action()

    def single_extract_click_action(self):
        self.click_timer.timeout.disconnect(self.single_extract_click_action)
        self.extract_and_display_names()

    def double_extract_click_action(self):
        self.extract_short_word_and_view()

    def single_get_click_action(self):
        self.click_timer.timeout.disconnect(self.single_get_click_action)
        self.get_select()

    def double_get_click_action(self):
        self.get_select_short()

    def extract_and_display_names(self):
        try:
            selected_nodes = [node for node in nuke.selectedNodes() if node.Class() == "Cryptomatte"]
            if not selected_nodes:
                raise ValueError("Please select at least one Cryptomatte")

            for selected_node in selected_nodes:
                self.process_single_node(selected_node)

        except ValueError as e:
            dD_log.warning(str(e))

    def process_single_node(self, selected_node):
        try:
            node_name = selected_node.name()
            if node_name not in self.node_state:
                self.node_state[node_name] = {
                    'last_processed_matte_list': [],
                    'extracted_word_groups': [],
                    'current_word_index': 0,
                    'group_size': 0
                }

            node_state = self.node_state[node_name]

            self.extract_and_display_names_for_node(selected_node)

            if not node_state['last_processed_matte_list']:
                return

            group_size = node_state['group_size']
            num_groups = len(node_state['extracted_word_groups'])

            if num_groups == 0 or group_size == 0:
                nuke.message("Error: No word group or group size is zero.")
                return

            words_to_display = node_state['last_processed_matte_list']

            self.channel_list_widget.clear()
            for word in words_to_display:
                self.channel_list_widget.addItem(word)

            _, crypto_name = self.get_cryptoname(selected_node)
            self.update_node_label(selected_node, words_to_display, crypto_name, italic=False, max_per_line=2)

        except Exception as e:
            nuke.message("An error has occurred : %s" % e)

    def extract_short_word_and_view(self):
        try:
            selected_nodes = [node for node in nuke.selectedNodes() if node.Class() == "Cryptomatte"]
            if not selected_nodes:
                raise ValueError("Please select at least one Cryptomatte")

            for selected_node in selected_nodes:
                self.process_short_view_node(selected_node)

        except ValueError as e:
            dD_log.warning(str(e))

    def process_short_view_node(self, selected_node):
        try:
            node_name = selected_node.name()
            if node_name not in self.node_state:
                self.node_state[node_name] = {
                    'last_processed_matte_list': [],
                    'extracted_word_groups': [],
                    'current_word_index': 0,
                    'group_size': 0
                }

            node_state = self.node_state[node_name]

            if not node_state['last_processed_matte_list']:
                self.extract_and_display_names_for_node(selected_node)

            if not node_state['extracted_word_groups']:
                return

            group_size = node_state['group_size']
            num_groups = len(node_state['extracted_word_groups'])

            if num_groups == 0 or group_size == 0:
                nuke.message("Error: No word group or group size is zero.")
                return

            words_to_display = []

            # Ensure we have enough groups to display a complete set
            for i in range(group_size):
                group_index = (node_state['current_word_index'] + i) % num_groups
                if len(node_state['extracted_word_groups'][group_index]) == 0:
                    continue
                word_index = (node_state['current_word_index'] // num_groups) % len(
                    node_state['extracted_word_groups'][group_index])
                words_to_display.append(node_state['extracted_word_groups'][group_index][word_index])

            # Advance the word index
            node_state['current_word_index'] = (node_state['current_word_index'] + 1) % (
                    num_groups * max(len(group) for group in node_state['extracted_word_groups'] if len(group) > 0))

            self.channel_list_widget.clear()
            for word in words_to_display:
                self.channel_list_widget.addItem(word)

            _, crypto_name = self.get_cryptoname(selected_node)
            self.update_node_label(selected_node, words_to_display, crypto_name, italic=True, max_per_line=3)

        except Exception as e:
            nuke.message("An error has occurred : %s" % e)

    def update_node_label(self, node, matte_list, crypto_name, italic=False, max_per_line=3):
        try:
            # Group words into lines of `max_per_line` words per line
            lines = ['   '.join(matte_list[i:i + max_per_line]) for i in range(0, len(matte_list), max_per_line)]
            formatted_list = '\n'.join(lines)

            # Format the label depending on the italic option
            if italic:
                new_label = "<i><sub>%s</sub></i>" % formatted_list
            else:
                new_label = "<sub>%s</sub>" % formatted_list

            # Update the node label
            node['label'].setValue(new_label)
        except Exception as e:
            dD_log.error(f"Failed to update label for node {node.name()}: {e}")

    def get_select(self):
        self.extract_and_display_names()

    def get_select_short(self):
        self.extract_short_word_and_view()

    def clear_duplicates_list(self, names_list):
        """
        Removes global duplicates from a list of words, preserving order.
        """
        if self.remove_duplicates_checkbox.isChecked():
            seen = set()
            unique = []
            for name in names_list:
                if name not in seen:
                    seen.add(name)
                    unique.append(name)
            return unique
        return names_list

    def extract_and_display_names_for_node(self, selected_node):
        node_name = selected_node.name()
        if node_name not in self.node_state:
            self.node_state[node_name] = {
                'last_processed_matte_list': [],
                'extracted_word_groups': [],
                'current_word_index': 0,
                'group_size': 0
            }

        node_state = self.node_state[node_name]

        try:
            if selected_node.Class() != "Cryptomatte":
                raise ValueError("Please select a Cryptomatte node")

            _, crypto_name = self.get_cryptoname(selected_node)
            selected_mattes = self.get_selected_mattes(selected_node)
            self.character_names = [name.lower() for name in self.character_names]

            processed_matte_list = []

            for matte in selected_mattes:
                name = self.extract_name_from_path(matte)
                name = self.clear_numbers(name)
                name = self.clear_cap(name)
                name = self.exclude_words(name)
                name = self.clear_symbols(name)
                name = self.standardize_text(name)
                name = self.singularize(name)
                name = self.clear_twin_words(name)
                name = self.clear_character_names(name, crypto_name)

                processed_matte_list.append(name)

            unique_processed_matte_list = self.clear_duplicates_list(processed_matte_list)

            self.channel_list_widget.clear()
            self.extracted_words = []
            self.extracted_word_groups = []

            for name in unique_processed_matte_list:
                self.channel_list_widget.addItem(name)
                words = re.findall(r'[A-Z][a-z]*', name)
                self.extracted_words.extend(words)
                self.extracted_word_groups.append(words)

            node_state['last_processed_matte_list'] = unique_processed_matte_list
            node_state['extracted_word_groups'] = self.extracted_word_groups
            node_state['group_size'] = len(unique_processed_matte_list)
            node_state['current_word_index'] = 0

            after_clean = len(unique_processed_matte_list)
            count_info = "Crypto %s: Select %d, Twin %d, Out %d" % (
                crypto_name if crypto_name else 'Unknown',
                len(processed_matte_list),
                len(processed_matte_list) - after_clean,
                after_clean
            )
            self.info_label.setText(count_info)

            # Update the node label
            self.update_node_label(selected_node, unique_processed_matte_list, crypto_name)

            dD_log.debug(f"processed_matte_list: {processed_matte_list}")
            dD_log.debug(f"unique_processed_matte_list (after clear_duplicates): {unique_processed_matte_list}")


        except Exception as e:
            nuke.message("An error has occurred : %s" % e)

    # Retrieve the Cryptomatte Matte List
    def get_selected_mattes(self, node):
        if node.Class() == "Cryptomatte":
            matteList = node['matteList'].value()
            if not matteList:
                return []
            # Split handling commas or newlines
            return [m.strip() for m in re.split(r'[,\n]+', matteList) if m.strip()]
        return []

    # Extracts a name from a given path using keywords and symbols.
    def extract_name_from_path(self, path):
        """
        By default returns the name as-is (useful for matteList entries like "Leaf_04_Geo")
        """
        dD_log.debug(f"Path: {path}")
        return path


    # Removes digits from a name
    def clear_numbers(self, name):
        if self.remove_digits_checkbox.isChecked():
            name = re.sub(r'\d+', '', name)
        return name

    # Removes isolated capital letters
    def clear_cap(self, name):
        if self.remove_uppercase_checkbox.isChecked():
            name = re.sub(r'(^|_)[A-Z](_|$)', '_', name)
            name = re.sub(r'(?<=[a-z])[A-Z](?=[^a-zA-Z]|$)', '', name)
        return name

    # Excludes certain words from preferences
    def exclude_words(self, name):
        exclude_words = [word.strip() for word in self.exclude_words_edit.text().split(',') if word.strip()]
        for exclude_word in exclude_words:
            pattern = re.escape(exclude_word)
            name = re.sub(pattern, '', name)
        return name

    def clear_symbols(self, name):
        if self.clear_symbols_checkbox.isChecked():
            symbols_text = self.clear_symbols_edit.text()
            if symbols_text:
                # Escape each symbol to avoid regex errors
                pattern = "[" + re.escape(symbols_text) + "]"
                name = re.sub(pattern, '', name)
        return name

    # Enables or disables the exclude word edit field
    def toggle_exclude_words_edit(self, state):
        isEnabled = state == Qt.Checked
        self.exclude_words_edit.setEnabled(isEnabled)

        if isEnabled:
            self.exclude_words_edit.setText(', '.join(self.excluded_words))
        else:
            self.exclude_words_edit.setText("")

    # Standardizes text by capitalizing words and separating attached words.
    def standardize_text(self, name):
        def adjust_case(s):
            return s.capitalize() if s.isupper() else s[0].upper() + s[1:] if s else s

        def separate_attached_words(s):
            return re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', s).split()

        if self.uniform_text_checkbox.isChecked():
            segments = re.split('([^a-zA-Z0-9]+)', name)

            name_parts_processed = []
            for part in segments:
                if part.isalpha():
                    for subpart in separate_attached_words(part):
                        name_parts_processed.append(adjust_case(subpart))
                else:
                    name_parts_processed.append(part)
            name = ''.join(name_parts_processed)
        return name




    # Transforms nouns into their singular form

    def singularize(self, name):
        if self.singularize_checkbox.isChecked():
            singular_dict = {k.lower(): v for k, v in self.singular_dict.items()}

            def is_camel_case(word):
                return bool(re.search(r'[a-z][A-Z]', word))  # e.g.: RockTree, VineSkeleton

            def to_singular(word):
                if not word or is_camel_case(word):
                    return word  # ignore CamelCase composites

                word_lower = word.lower()

                if word_lower in singular_dict:
                    return singular_dict[word_lower].capitalize()

                if word_lower.endswith('s') and word_lower[:-1] not in singular_dict.values():
                    return word[:-1].capitalize()

                return word.capitalize()

            parts = re.split('([^a-zA-Z0-9]+)', name)
            name = ''.join(to_singular(part) if part.isalpha() else part for part in parts)

        return name

    def clear_twin_words(self, name):
        """
        Removes word repetitions within a single string (e.g.: RockRockTree -> RockTree).
        Does not modify commas or external separators.
        """
        if self.clear_twin_words_checkbox.isChecked():
            return re.sub(r'\b(\w+)\1+\b', r'\1', name)
        return name

    def clear_duplicates(self, names_list):
        if self.remove_duplicates_checkbox.isChecked():
            stripped_names = [name.strip() for name in names_list if name.strip()]
            unique = list(dict.fromkeys(stripped_names))
            dD_log.debug("CLEAR DUPLICATES")
            dD_log.debug(f"   Input : {names_list}")
            dD_log.debug(f"   Stripped: {stripped_names}")
            dD_log.debug(f"   Unique : {unique}")
            return unique
        return names_list

    # Removes character's names in the words
    def clear_character_names(self, name, crypto_name):
        if self.remove_character_checkbox.isChecked() and crypto_name in ["material", "object", "asset"]:
            with open(self.preferences_path, 'r') as file:
                preferences = json.load(file)
                character_names = preferences.get("character_names", [])

            segments = re.split(r'([A-Z][a-z]*|[_:])', name)
            filtered_segments = []

            character_names_set = set(character_names)
            character_names_set.update([n.capitalize() for n in character_names])

            for segment in segments:
                if segment not in character_names_set or segment == name:
                    filtered_segments.append(segment)

            name = ''.join(filtered_segments)
            name = re.sub(r'_+', '_', name).strip('_')

        return name

    # Sorts a list of names alphabetically
    def sort_names(self, names_list):
        if self.sort_alphabetically_checkbox.isChecked():
            return sorted(names_list)
        return names_list

    # Retrieves the name of the selected Cryptomatte.
    def get_cryptoname(self, selected_node):
        if selected_node.Class() != "Cryptomatte":
            return None, "!!!Select a Cryptomatte!!!"

        try:
            layer_selection = selected_node['cryptoLayerChoice'].getValue()
            raw_layer = ["cryptoasset", "identifier_object", "user___materialid"][int(layer_selection)]

            # Simplified display name
            display_layer = {
                "cryptoasset": "Asset",
                "identifier_object": "Object",
                "user___materialid": "Material"
            }.get(raw_layer, raw_layer)  # fallback if unknown

            return raw_layer, display_layer

        except Exception as e:
            return None, "Error: %s" % e

    # Updates the label of a Cryptomatte node with the list of previously processed mattes.
    def matteListFromPref(self):
        if hasattr(self, 'last_processed_matte_list') and self.last_processed_matte_list:
            try:
                selected_node = nuke.selectedNode()
                if selected_node.Class() == "Cryptomatte":
                    _, crypto_name = self.get_cryptoname(selected_node)

                    words_in_lines = ['   '.join(self.last_processed_matte_list[i:i + 2]) for i in
                                      range(0, len(self.last_processed_matte_list), 2)]
                    formatted_list = '\n'.join(words_in_lines)

                    new_label = "%s\n<sub>" % crypto_name + formatted_list.strip() + "</sub>"
                    selected_node['label'].setValue(new_label)

                    input_node = selected_node.input(0)
                    if input_node:
                        x_diff = selected_node['xpos'].value() - input_node['xpos'].value()
                        if not (
                                -50 <= x_diff <= 50):  # Check if x position difference is outside +/-50 tolerance
                            offset_y_position = input_node.ypos() + (input_node.screenHeight() // 2) - (
                                        selected_node.ypos() + (selected_node.screenHeight() // 2))
                            selected_node.setXYpos(selected_node.xpos(), int(selected_node.ypos() + offset_y_position))

            except ValueError:
                nuke.message("Please select a Cryptomatte.")
            except Exception as e:
                nuke.message("An error has occurred : %s" % e)

    # Loads user preferences from the preferences JSON file
    def load_preferences(self):
        if not os.path.exists(self.preferences_path):
            dD_log.info(f"Preferences file does not exist at: {self.preferences_path}")
            return

        try:
            with open(self.preferences_path, 'r') as f:
                preferences = json.load(f)
            self.apply_preferences(preferences)
        except (json.JSONDecodeError, IOError) as e:
            dD_log.warning(f"Error loading preferences: {e}")
            preferences = {}

        self.symbols = preferences.get('symbols', [])
        self.keywords = preferences.get('keywords', [])
        if isinstance(self.keywords, list):
            self.keywords = [keyword.strip() for keyword in self.keywords]
        if isinstance(self.symbols, list):
            self.symbols = [symbol.strip() for symbol in self.symbols]

        self.remove_digits_checkbox.setChecked(preferences.get('remove_digits', True))
        self.remove_uppercase_checkbox.setChecked(preferences.get('remove_uppercase', False))
        self.enable_exclude_words_checkbox.setChecked(preferences.get('enable_exclude_words', False))
        self.clear_symbols_checkbox.setChecked(preferences.get('clear_symbols', False))
        self.clear_symbols_edit.setText(preferences.get('clear_symbols_list', ''))

        self.uniform_text_checkbox.setChecked(preferences.get('uniform_text', False))
        self.singularize_checkbox.setChecked(preferences.get('singularize', False))
        self.singular_edit.setText(json.dumps(preferences.get('singular_dict', {})))
        self.clear_twin_words_checkbox.setChecked(preferences.get('clear_twin_words', False))
        self.remove_duplicates_checkbox.setChecked(preferences.get('remove_duplicates', False))
        self.remove_character_checkbox.setChecked(preferences.get('remove_character', False))
        self.remove_character_edit.setText(', '.join(preferences.get('character_names', [])))
        self.sort_alphabetically_checkbox.setChecked(preferences.get('sort_alphabetically', False))

        self.excluded_words = [word.strip() for word in preferences.get('exclude_words', [])]
        self.character_names = [name.capitalize() for name in preferences.get('character_names', [])]
        self.singular_dict = preferences.get('singular_dict', {})

        if self.enable_exclude_words_checkbox.isChecked():
            self.exclude_words_edit.setText(', '.join(self.excluded_words))
        else:
            self.exclude_words_edit.setText("")

    def load_preferences_from_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Preferences", "",
                                                   "JSON Files (*.json);;All Files (*)",
                                                   options=options)
        if file_name:
            with open(file_name, 'r') as f:
                preferences = json.load(f)
            self.apply_preferences(preferences)

    # Applies the loaded preferences to the application form.
    def apply_preferences(self, preferences):
        self.symbols = [symbol.strip() for symbol in preferences.get('symbols', []) if symbol.strip()]
        self.keywords = [keyword.strip() for keyword in preferences.get('keywords', []) if keyword.strip()]

        if self.keywords_edit:
            self.keywords_edit.setText(', '.join(self.keywords))

        self.remove_digits_checkbox.setChecked(preferences.get('remove_digits', False))
        self.remove_uppercase_checkbox.setChecked(preferences.get('remove_uppercase', False))
        self.enable_exclude_words_checkbox.setChecked(preferences.get('enable_exclude_words', True))
        self.exclude_words_edit.setText(', '.join(preferences.get('exclude_words', [])))
        self.clear_symbols_checkbox.setChecked(preferences.get('clear_symbols', False))
        self.clear_symbols_edit.setText(preferences.get('clear_symbols_list', ''))

        self.uniform_text_checkbox.setChecked(preferences.get('uniform_text', True))
        self.singularize_checkbox.setChecked(preferences.get('singularize', True))
        self.singular_edit.setText(json.dumps(preferences.get('singular_dict', {})))
        self.clear_twin_words_checkbox.setChecked(preferences.get('clear_twin_words', False))
        self.remove_duplicates_checkbox.setChecked(preferences.get('remove_duplicates', False))
        self.remove_character_checkbox.setChecked(preferences.get('remove_character', False))
        self.remove_character_edit.setText(', '.join(preferences.get('character_names', [])))
        self.sort_alphabetically_checkbox.setChecked(preferences.get('sort_alphabetically', False))

        self.excluded_words = [word.strip() for word in preferences.get('exclude_words', []) if word.strip()]
        self.character_names = [name.capitalize() for name in preferences.get('character_names', []) if name.strip()]
        self.singular_dict = preferences.get('singular_dict', {})

        if self.enable_exclude_words_checkbox.isChecked():
            self.exclude_words_edit.setText(', '.join(self.excluded_words))

    # Saves user preferences to Nuke Preferences
    def save_preferences(self):
        prefs = nuke.toNode("preferences")
        group = "CryptoTool"
        if prefs is None:
            dD_log.error("Nuke preferences node not found.")
            return

        # Retrieve the dictionary
        try:
            singular_dict_text = self.singular_edit.text()
            singular_dict = json.loads(singular_dict_text) if singular_dict_text.strip() else {}
        except json.JSONDecodeError:
            singular_dict = {}

        # Write to Nuke preferences
        prefs["%s_remove_digits" % group].setValue(self.remove_digits_checkbox.isChecked())
        prefs["%s_remove_uppercase" % group].setValue(self.remove_uppercase_checkbox.isChecked())
        prefs["%s_enable_exclude_words" % group].setValue(self.enable_exclude_words_checkbox.isChecked())
        prefs["%s_clear_symbols_list" % group].setValue(self.clear_symbols_edit.text())
        prefs["%s_uniform_text" % group].setValue(self.uniform_text_checkbox.isChecked())
        prefs["%s_singularize" % group].setValue(self.singularize_checkbox.isChecked())
        prefs["%s_clear_twin_words" % group].setValue(self.clear_twin_words_checkbox.isChecked())
        prefs["%s_remove_duplicates" % group].setValue(self.remove_duplicates_checkbox.isChecked())
        prefs["%s_remove_character" % group].setValue(self.remove_character_checkbox.isChecked())
        prefs["%s_sort_alphabetically" % group].setValue(self.sort_alphabetically_checkbox.isChecked())

        prefs["%s_exclude_words" % group].setValue(self.exclude_words_edit.text())
        prefs["%s_character_names" % group].setValue(self.remove_character_edit.text())
        prefs["%s_singular_dict" % group].setValue(json.dumps(singular_dict, indent=2))

        dD_log.info("Preferences saved to Nuke Preferences successfully.")


# ----------------------------------------------------------------------------#
setup_window = None
click_timer = QTimer()
click_timer.setSingleShot(True)
is_double_click = False



def setup(show_window=True):
    global setup_window
    from crypto_tool import register_crypto_tool_prefs
    register_crypto_tool_prefs()

    if setup_window is None:
        setup_window = MainUI(show_window=show_window)
    if show_window:
        setup_window.show()



def select_all_cryptomattes():
    all_cryptomattes = [node for node in nuke.allNodes() if node.Class() == "Cryptomatte"]
    for cryptomatte in all_cryptomattes:
        cryptomatte.setSelected(True)

def deselect_all():
    for node in nuke.allNodes():
        node.setSelected(False)

def recenter_node(node):
    """
    [DISABLED] Automatic recentering function disabled to let the user control positioning.
    Calls to this function will have no effect.
    """
    pass

def single_click_action():
    global is_double_click
    global setup_window

    if not is_double_click:
        get_select()
    is_double_click = False

    # Recenter each selected node
    for node in nuke.selectedNodes():
        recenter_node(node)

def single_click_action_all():
    global is_double_click
    if not is_double_click:
        get_select_all()
    is_double_click = False
    recenter_node(node)

def get_select():
    """
    Calls the get_select() method of the main window.
    This method is used to perform the normal selection action.
    """
    global setup_window
    if setup_window is None:
        setup(show_window=False)
    for node in nuke.selectedNodes():
        if node.Class() == "Cryptomatte":
            setup_window.process_single_node(node)
            recenter_node(node)

def get_select_all():
    setup(show_window=False)
    select_all_cryptomattes()
    for node in nuke.selectedNodes():
        if node.Class() == "Cryptomatte" and setup_window:
            setup_window.process_single_node(node)
    deselect_all()

def get_select_short():
    """
    Calls the get_select_short() method of the main window.
    This method is used to perform the short selection action.
    """
    global setup_window
    if setup_window is None:
        setup(show_window=False)
    for node in nuke.selectedNodes():
        if node.Class() == "Cryptomatte":
            setup_window.process_short_view_node(node)
            recenter_node(node)

def get_select_short_all():
    setup(show_window=False)
    select_all_cryptomattes()
    for node in nuke.selectedNodes():
        if node.Class() == "Cryptomatte" and setup_window:
            setup_window.process_short_view_node(node)
            recenter_node(node)
    deselect_all()

def double_click_action():
    get_select_short()
    for node in nuke.selectedNodes():
        recenter_node(node)


def double_click_action_all():
    get_select_short_all()
    for node in nuke.selectedNodes():
        recenter_node(node)


def run():
    global is_double_click
    if click_timer.isActive():
        is_double_click = True
        click_timer.stop()
        double_click_action()
        for node in nuke.selectedNodes():
            recenter_node(node)
    else:
        click_timer.start(250)
        click_timer.timeout.connect(single_click_action)
        for node in nuke.selectedNodes():
            recenter_node(node)

def run_all():
    global is_double_click
    if click_timer.isActive():
        is_double_click = True
        click_timer.stop()
        double_click_action_all()
        for node in nuke.selectedNodes():
            dD_log.debug(f"Centering node (all): {node.name()}")
            recenter_node(node)
    else:
        click_timer.start(250)
        click_timer.timeout.connect(single_click_action_all)
        for node in nuke.selectedNodes():
            dD_log.debug(f"Centering node (all): {node.name()}")
            recenter_node(node)

def some_function_that_recenters_node(selected_node):
    """
    Recenters a selected node relative to its input node, with a tolerance margin of +/-20 units.
    """
    input_node = selected_node.input(0)
    if input_node:
        x_diff = selected_node['xpos'].value() - input_node['xpos'].value()
        if not (-20 <= x_diff <= 20):
            offset_y_position = input_node.ypos() + (input_node.screenHeight() // 2) - (selected_node.ypos() + (selected_node.screenHeight() // 2))
            selected_node.setXYpos(selected_node.xpos(), int(selected_node.ypos() + offset_y_position))

def clear_label():
    """
    Clears the labels of the selected nodes in Nuke.
    """
    for node in nuke.selectedNodes():
        if 'clear' in node.knobs():
            node['label'].setValue('')
            recenter_node(node)

def clear_all_nodes():
    """
    Clears all selected nodes in Nuke.
    Executes the 'clear' command on each node and clears their label.
    """
    for node in nuke.selectedNodes():
        if 'clear' in node.knobs():
            node['clear'].execute()
            node['label'].setValue('')
            recenter_node(node)

def findKeywordMatch(partName, keywords):
    """
    Finds and returns the first keyword that matches a part of the given name.
    If no keyword matches, returns None.

    Args:
    - partName (str): The part of the name to check.
    - keywords (list): The list of keywords to compare.

    Returns:
    - str or None: The matching keyword or None if no match is found.
    """
    return next((keyword for keyword in keywords if keyword.lower() in partName.lower()), None)

def character_name():
    """
    Returns the list of character names in the main window,
    each name capitalized.

    Returns:
    - list: The list of capitalized character names.
    """
    return [name.capitalize() for name in setup_window.character_names]

def register_crypto_tool_prefs():
    prefs = nuke.toNode("preferences")
    if prefs is None:
        dD_log.error("Cannot access preferences node.")
        return

    group = "CryptoTool"

    if not prefs.knob("%s_clear_symbols_list" % group):
        prefs.addKnob(nuke.Tab_Knob("%s_tab" % group, "Crypto Tool"))

        prefs.addKnob(nuke.Boolean_Knob("%s_remove_digits" % group, "Clear numbers"))
        prefs["%s_remove_digits" % group].setValue(True)

        prefs.addKnob(nuke.Boolean_Knob("%s_remove_uppercase" % group, "Clear caps alone"))
        prefs["%s_remove_uppercase" % group].setValue(False)

        prefs.addKnob(nuke.Boolean_Knob("%s_enable_exclude_words" % group, "Use exclusion words"))
        prefs["%s_enable_exclude_words" % group].setValue(False)

        prefs.addKnob(nuke.String_Knob("%s_clear_symbols_list" % group, "Symbols to remove"))
        prefs["%s_clear_symbols_list" % group].setValue("-_:.")

        prefs.addKnob(nuke.Boolean_Knob("%s_uniform_text" % group, "Standardize text"))
        prefs["%s_uniform_text" % group].setValue(True)

        prefs.addKnob(nuke.Boolean_Knob("%s_singularize" % group, "Format to singular"))
        prefs["%s_singularize" % group].setValue(True)

        prefs.addKnob(nuke.Boolean_Knob("%s_clear_twin_words" % group, "Clear Twins words"))
        prefs["%s_clear_twin_words" % group].setValue(False)

        prefs.addKnob(nuke.Boolean_Knob("%s_remove_duplicates" % group, "Clear duplicates words"))
        prefs["%s_remove_duplicates" % group].setValue(False)

        prefs.addKnob(nuke.Boolean_Knob("%s_remove_character" % group, "Clear character names"))
        prefs["%s_remove_character" % group].setValue(False)

        prefs.addKnob(nuke.Boolean_Knob("%s_sort_alphabetically" % group, "Sort alphabetically"))
        prefs["%s_sort_alphabetically" % group].setValue(False)

        prefs.addKnob(nuke.Multiline_Eval_String_Knob("%s_exclude_words" % group, "Words to exclude"))
        prefs.addKnob(nuke.Multiline_Eval_String_Knob("%s_character_names" % group, "Character names"))
        prefs.addKnob(nuke.Multiline_Eval_String_Knob("%s_singular_dict" % group, "Singular dictionary"))


# Initialize without displaying the window on module reload
if __name__ == "__main__":
    setup(show_window=False)
    dD_log.info("setup function executed at module load")
