#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Help module for LayerManager -- opens documentation links.
"""
import webbrowser

from lm_config import HELP_LINK


def open_layermanager_help():
    """Open the LayerManager documentation page."""
    webbrowser.open(HELP_LINK)
