# -*- coding: utf-8 -*-

import arcpy

import Tools_script
import importlib

importlib.reload(Tools_script)

from Tools_script import FeatureClassToFeatureLayerSyncClass

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        
        self.label = "Custom toolbox from D.Lukash"
        self.alias = "portalsync"

        # List of tool classes associated with this toolbox
        self.tools = [FeatureClassToFeatureLayerSyncClass]

