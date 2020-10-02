import arcpy
from arcgis import GIS
from arcgis.features import FeatureLayer, FeatureSet

import time
import json
from threading import Thread 

global current_params
global out_fields_desc #descriptio of out fields
global in_fields_desc #descriptio of in fields
global layer_desc #description of in layer 
current_params = [None, None, None]

portal_items = None

from datetime import datetime

class FeatureClassToFeatureLayerSyncClass(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Feature class to Feature Service/layer"
        self.description = ""
        self.canRunInBackground = False



    def getParameterInfo(self):
        """Define parameter definitions"""
        # Input feature class
        
        param_destination = arcpy.Parameter(
            displayName ='Destination feature layer(table) from activated Portal',
            name ='destination_FL',
            datatype ="GPString",
            parameterType ='Required',
            direction = None)

        param_destination.filter.type = "ValueList"
        
        #Populate list from a Portal
        param_destination.filter.list = get_feature_service_list()
               

        input_class_param = arcpy.Parameter(
            displayName ='Input Features',
            name ='in_features',
            datatype = "GPFeatureLayer",
            parameterType ='Required',
            direction ='Input')


           
        field_maping = arcpy.Parameter(
            displayName='Place names of fields from input feature class to the theard column',
            name='maping_fields',
            datatype='GPValueTable',
            parameterType='Required',
            direction='Input',
            category='Matching section',
            enabled=False)

        field_maping.columns = [['GPString', 'Destination field\'s Name'], ['GPString', 'Input field\'s Name']]
        field_maping.filters[1].type = 'ValueList'


        thread_number = arcpy.Parameter(
            displayName='Enter a number of theards that will be appending data in paralelle',
            name='thread_number',
            datatype='Long',
            parameterType='Optional',
            direction='Input')

        thread_number.filter.type = "Range"
        thread_number.filter.list = [1,100]
        thread_number.value = 1

        params = [param_destination, input_class_param,  field_maping, thread_number]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        #When we choose or change feature layer/table we change appiriance of the table.
        global current_params
        global out_fields_desc
        global in_fields_desc
        global layer_desc
        global portal_items


        if not (parameters[0].altered and parameters[0].altered and parameters[0].altered): # Refresh params if tool is reopened but not reloaded
            current_params = [None, None, None]

        if parameters[0].altered and current_params[0] != parameters[0].valueAsText:  

            # Authentification on active portal using Python API (arcpy lib)
            token = arcpy.GetSigninToken()
            portal_url = arcpy.GetActivePortalURL()
            gis = GIS(portal_url, token = token['token'])

            # Get the layer and it's properties
            layer = FeatureLayer(parameters[0].valueAsText)
            properties = layer.properties
            item_type = properties.geometryType


            # Apply filter of feature type to input parameter
            # Form a pairs os types for filter applying

            list_of_types = {
                'Point':"esriGeometryPoint", 
                'Multipoint':"esriGeometryMultipoint", 
                'Polyline':'esriGeometryPolyline', 
                'Polygon':'esriGeometryPolygon'}

            filter_type = [x[0] for x in list_of_types.items() if x[1] == properties.geometryType]
            
            # Define list filter
            parameters[1].filter.list = filter_type

            #Lists to populate fields to a matching table
            values = []
            system_fields = []
            
            # System fields with info about changes + Global and Object ID. Populates automaticaly
            try:
                system_fields.extend([x[1] for x in properties.editFieldsInfo.items()])
            except AttributeError:
                pass
            
            system_fields.append(properties.objectIdField)

            try:
                system_fields.append(properties.globalIdField)
            except AttributeError:
                pass

            # Create a list of fields of utput feature class in table for creating matching schema
            parameters[2].values = [[x.name, ''] for x in layer.properties.fields if not x.name in system_fields]

            # Add a filter to create a dropdown list
            parameters[2].filters[0].list = [x.name for x in layer.properties.fields if not x.name in system_fields]

            #Add input fields to self for feaurute actions
            out_fields_desc = layer.properties
            
          
            #Show matching table ONLY if input and output params is set
            if  parameters[1].value and parameters[0].value:
                parameters[2].enabled = True
            else:
                parameters[2].enabled = False

            current_params[0] = parameters[0].valueAsText



        if parameters[1].altered and current_params[1] != parameters[1].valueAsText:

            description = arcpy.Describe(parameters[1].valueAsText)
            field_count = description.fieldInfo.count

            field_list = []

            for i in range(field_count):
                field_list.append(description.fieldInfo.getFieldName(i))
            
            parameters[2].filters[1].list = field_list

            # Show matching table ONLY if input and output params is set
            if  parameters[1].value and parameters[0].value:
                parameters[2].enabled = True
            else:
                parameters[2].enabled = False

            current_params[1] = parameters[1].valueAsText

            # Save description for feaurute action
            in_fields_desc = arcpy.ListFields(parameters[1].valueAsText)
            layer_desc = description


        if parameters[2].altered and current_params[2] != parameters[2].valueAsText:

            current_params[2] = parameters[2].valueAsText
            

        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""


        global out_fields_desc
        global in_fields_desc
        global layer_desc

        if parameters[1].altered and parameters[0].altered:
            
            #Take a spatial reference of all service
            layer_id = parameters[0].valueAsText.split('/')[-1]
            descr = arcpy.Describe(parameters[0].valueAsText[:-(len(layer_id))])
            wkid = descr.children[int(layer_id)].spatialReference.factoryCode

            # Check if geometry of input and output is similar

            if not layer_desc.hasM == out_fields_desc.hasM:
                parameters[1].setErrorMessage("hasM parameter of input and output must be the same")
            if not layer_desc.hasZ == out_fields_desc.hasZ:
                parameters[1].setErrorMessage("hasZ parameter of input and output must be the same")
            if not layer_desc.spatialReference.factoryCode == wkid:
                parameters[1].setErrorMessage(f"Spatial references of input ({layer_desc.spatialReference.factoryCode}) and output ({wkid}) must be the same")

        
        if parameters[2].altered:


            # Check if 1 field is shoosen 1 time

            fields_list = parameters[2].value

            out_fields = [x[0] for x in fields_list if x[0] != '']
            in_fields = [x[1] for x in fields_list if x[1] != '']

            # out fileds

            if check_list_duplicates(out_fields):
                parameters[2].setErrorMessage("Output fields in maching shema must be unique")
            if check_list_duplicates(in_fields):
                parameters[2].setErrorMessage("Input fields in maching shema must be unique")

            for field_pare in [x for x in fields_list if x[0] and x[1]]:

                out_type = [x.type for x in out_fields_desc.fields if x.name == field_pare[0]][0]
                in_type = [x.type for x in in_fields_desc if x.name == field_pare[1]][0]

                #Check if types of mathred fields is similar
                if not in_type in out_type:
                    parameters[2].setErrorMessage(f'Input field {field_pare[1]} of type {in_type} do not match output field {field_pare[0]} with type {out_type}')

            # System fields with info about changes + Global and Object ID. Populates automaticaly
            system_fields = []
            
            try:
                system_fields.extend([x[1] for x in out_fields_desc.editFieldsInfo.items()])
            except AttributeError:
                pass
            
            system_fields.append(out_fields_desc.objectIdField)

            try:
                system_fields.append(out_fields_desc.globalIdField)
            except AttributeError:
                pass
            
            # Check if we haven't missed a not nullable field
            # Create a list of not nullable fields
            not_nullable_names = [x.name for x in out_fields_desc.fields if not x.nullable and x.name not in system_fields]

            list_diff_dont_checked = list(set(not_nullable_names) - set([x[0] for x in fields_list])) 
            list_diff_dont_matched = list(set(not_nullable_names) - set([x[0] for x in fields_list if x[1]]))

            #Check if not nullabele fields have mached and throw error message if not
            if list_diff_dont_checked:
                parameters[2].setErrorMessage(f'Fields {",".join(list_diff_dont_checked)} can\'t be NULL. Add it and match')

            if list_diff_dont_matched:
                parameters[2].setErrorMessage(f'Fields {",".join(list_diff_dont_matched)} can\'t be NULL. Match it')


        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        arcpy.SetProgressor("default", message = "Accesing to a destinational resouse")


        # Acessing outpud data
        token = arcpy.GetSigninToken()
        portal_url = arcpy.GetActivePortalURL()
        gis = GIS(portal_url, token = token['token'])
        layer = FeatureLayer(parameters[0].valueAsText)


        arcpy.SetProgressorLabel("Prepearing input data")
        #Prepearing input data

        feature_set = arcpy.FeatureSet(parameters[1].valueAsText)
        feature_set_dict =  json.loads(feature_set.JSON)

        # Matching parameter
        matching = parameters[2].value

        # Split features by number of threads
        list_of_lists = chunkIt(feature_set_dict['features'], parameters[3].value)

        # List of threads
        threads = []

        arcpy.SetProgressorLabel("Starting threads")

        # Starting threads
        for feature_list in list_of_lists:
            threads.append(Thread(target=create_and_append, args=[feature_list, arcpy.GetSigninToken(), portal_url, parameters[0].valueAsText, matching]))
            threads[-1].start()

        # Joining all threads

        arcpy.SetProgressorLabel("Executing appendence")

        for thread in threads:
            thread.join()


            #!TODO Переробити перевірку проекції     

        return

#!TODO check for editable and nullable fields

def create_and_append(feature_list = None, token = None, portal_url = None, service_url = None, matching = None):

    token = arcpy.GetSigninToken()
    portal_url = arcpy.GetActivePortalURL()
    gis = GIS(portal_url, token = token['token'])
    layer = FeatureLayer(service_url)

    features_to_append = []


    for feature in feature_list:
        new_feature = {'attributes':{},'geometry':feature['geometry']}
            
        #Find fields and it's value
        for field in matching: 
            new_feature['attributes'][field[0]] = [x[1] for x in feature['attributes'].items() if x[0] == field[1]][0]

        features_to_append.append(new_feature.copy())

        if len(features_to_append) > 500:
            result = layer.edit_features(adds=features_to_append)
            features_to_append = []

    if features_to_append:
        layer.edit_features(adds=features_to_append)




def check_list_duplicates(in_list = None): # Check if there are dublicates in list
    
    if len(in_list) == len(set(in_list)):
        return False
    else:
        return True

def chunkIt(seq, num):  #Func to split list by a parts
    avg = len(seq) / float(num)
    out = []
    last = 0.0

    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg

    return out


def get_feature_service_list(): #functions to get Feature layer list from portal  
        global portal_items    

        # Authentification on active portal using Python API (arcpy lib)
        token = arcpy.GetSigninToken()
        portal_url = arcpy.GetActivePortalURL()
        gis = GIS(portal_url, token = token['token'])

        # Get content of the Portal and get url's of layers and tables

        #content = gis.content
        search_results = gis.content.search(query = '', item_type='Feature Service', max_items = 200)
        
        portal_items = search_results

        layers_list = []

        #Only layers not tables
        
        for itm in search_results:
            try:
                layers_list.extend([x.url for x in itm.layers])
            except TypeError:
                pass
            
        
        return layers_list
