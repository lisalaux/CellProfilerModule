# coding=utf-8

"""
Author: Lisa Laux, MSc Information Technology, University of Glasgow
Date: August 2018

License: Please note that the CellProfiler Software was released under the BSD 3-Clause License by
the Broad Institute: Copyright © 2003 - 2018 Broad Institute, Inc. All rights reserved. Please refer to
CellProfiler's LICENSE document for details.

"""

#################################
#
# Imports from useful Python libraries
#
#################################

import numpy

#################################
#
# Imports from CellProfiler
#
#################################

import cellprofiler.image
import cellprofiler.module
import cellprofiler.measurement
import cellprofiler.object
import cellprofiler.setting
import cellprofiler.pipeline
import cellprofiler.workspace

__doc__ = """\
AutomatedEvaluation
===================

**AutomatedEvaluation** can be used to automatically evaluate the quality of identified objects
(eg nuclei, cytoplasm, adhesions). 

By choosing an object and some of its measurements to be evaluated, the module will check whether these measurements
are in a tolerance range provided in the settings. If object measurement values are outside this range, a 
percentaged deviation per value will be measured and saved with the object measurements in a numpy array.

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          NO           NO
============ ============ ===============


Requirements
^^^^^^^^^^^^
The module needs to be placed after both, IdentifyObjects and Measurement modules to access the objects and
measurements taken for these objects to evaluate them as input.


Measurements made by this module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Evaluation:**

-  *Evaluation_Deviation*: Array of percentaged deviations of each object to a pre-defined quality range.
        e.g.    the deviation of a measurement with value 0.5 to the min. quality threshold of 0.9 will be 44.4 (%)
                the deviation of a measurement with value 1.1 to the max. quality thresthold of 1.0 will be 10.0 (%)

"""

#
# Constants
#
CATEGORY = 'Evaluation'
DEVIATION = 'Deviation'
FEATURE_NAME = 'Evaluation_Deviation'

NUM_FIXED_SETTINGS = 1
NUM_GROUP_SETTINGS = 2


#
# Create module class which inherits from cellprofiler.module.Module class
#
class AutomatedEvaluation(cellprofiler.module.Module):

    #
    # Declare the name for displaying the module, e.g. in menus 
    # Declare the category under which it is stored and grouped in the menu
    # Declare variable revision number which can be used to provide backwards compatibility  if CellProfiler will be
    # released in a new version
    #
    module_name = "AutomatedEvaluation"
    category = "Advanced"
    variable_revision_number = 1

    #######################################################################
    # Create and set CellProfiler settings for GUI and Pipeline execution #
    #######################################################################

    #
    # Define the setting's data types and grouped elements
    #
    def create_settings(self):
        super(AutomatedEvaluation, self).create_settings()

        module_explanation = [
            "Module used to automatically evaluate the quality of identified objects (eg nuclei, adhesions). "
            "Needs to be placed after IdentifyObjects and Measurement modules. Choose the measurements to be evaluated"
            "and set a tolerance range for their values. If objects are outside this range, a deviation will be "
            "measured and saved with the object."]

        #
        # Notes will appear in the notes-box of the module
        #
        self.set_notes([" ".join(module_explanation)])

        #
        # Object identified in upstream IndentifyObjects module; accessible via ObjectNameSubscriber
        #
        self.input_object_name = cellprofiler.setting.ObjectNameSubscriber(
            "Input object name",
            cellprofiler.setting.NONE,
            doc="""\
These are the objects that the module operates on."""
        )

        #
        # Group of measurements made for the object by a Measurements module
        #
        self.measurements = []

        #
        # Add first measurement which cannot be deleted; there must be at least one
        #
        self.add_measurement(can_delete=False)

        #
        # Button for adding additional measurements; calls add_measurement helper function
        #
        self.add_measurement_button = cellprofiler.setting.DoSomething(
            "", "Add another measurement", self.add_measurement)

    #
    # helper function:
    # adds measurements grouped with corresponding quality ranges
    # adds a remove-button for all measurements except a mandatory one where can_delete = False
    #
    def add_measurement(self, can_delete=True):
        group = cellprofiler.setting.SettingsGroup()

        #
        # Dropdown selection for measurements taken for the object
        #
        group.append(
            "measurement",
            cellprofiler.setting.Measurement(
                "Select the quality measurement",
                self.input_object_name.get_value,
                "AreaShape_Area",
                doc="""\
See the **Measurements** modules help pages for more information
on the features measured."""

            )
        )

        #
        # Range of values which are within the accepted quality thresholds
        #
        group.append(
            "range",
            cellprofiler.setting.FloatRange(
                'Set tolerance range',
                (00.00, 100.00),
                minval=00.00,
                maxval=1000.00,
                doc="""\
Set a tolerance range for the measurement. If values of the measurement are not within the range, a percentaged 
deviation will be calculated"""
            )
        )

        group.append("divider", cellprofiler.setting.Divider())

        self.measurements.append(group)

        if can_delete:
            group.append(
                "remover",
                cellprofiler.setting.RemoveSettingButton(
                    "",
                    "Remove this measurement",
                    self.measurements, group
                )
            )

    #
    # setting_values are stored as unicode strings in the pipeline.
    # If the module has settings groups, it needs to be ensured that settings() returns the correct
    # number of settings as saved in the file.
    # To do so, look at the setting values before settings() is called to determine how many to return.
    # Add groups if necessary.
    #
    def prepare_settings(self, setting_values):
        num_settings = (len(setting_values) - NUM_FIXED_SETTINGS) / NUM_GROUP_SETTINGS
        if len(self.measurements) == 0:
            self.add_measurement(False)
        elif len(self.measurements) > num_settings:
            del self.measurements[num_settings:]
        else:
            for i in range(len(self.measurements), num_settings):
                self.add_measurement()

    #  
    # CellProfiler must know about the settings in the module.
    # This method returns the settings in the order that they will be loaded and saved from a pipeline or project file.
    # Accessing setting members of a group of settings requires looping through the group result list
    #
    def settings(self):
        result = [self.input_object_name]
        for measurement in self.measurements:
            result += [measurement.measurement, measurement.range]
        return result

    #  
    # returns what the user should see in the GUI
    # include buttons and dividers which are not added in the settings method
    #
    def visible_settings(self):
        result = [self.input_object_name]
        for measurement in self.measurements:
            result += [measurement.measurement, measurement.range]
            if hasattr(measurement, "remover"):
                result += [measurement.remover]
            if hasattr(measurement, "divider"):
                result += [measurement.divider]
        result += [self.add_measurement_button]
        return result

    ###################################################################
    # Run method will be executed in a worker thread of the pipeline #
    ###################################################################

    #
    # CellProfiler calls "run" on each image set in the pipeline
    # The workspace as input parameter contains the state of the analysis so far
    #
    def run(self, workspace):

        #
        # Get the measurements object for the current run
        #
        workspace_measurements = workspace.measurements

        #
        # declare array of deviation values
        #
        deviations = []

        #
        # take the selected object's measurements and corresponding ranges one by one and compare it to the thresholds
        #
        for m in self.measurements:

            p_dev = 0  # percentaged deviation of the measurement m

            #
            # get_current_measurement returns an array with the measurements per object
            #
            measurement_values = workspace_measurements.get_current_measurement(self.input_object_name.value_text,
                                                                                m.measurement.value_text)

            # print(measurement_values)

            #
            # loop through all entries of the array to determine whether they are within the quality range or not;
            # if not, determine the deviation to the min or max bound respectively and save the percentaged deviation
            # in deviations
            #
            for v in measurement_values:
                if v >= m.range.min and v <= m.range.max:
                    p_dev += 0
                else:
                    if v < m.range.min:
                        deviation = m.range.min - v
                        p_dev += (deviation*100)/m.range.min
                        # print("p_dev:")
                        # print(p_dev)
                    else:
                        deviation = v - m.range.max
                        p_dev += (deviation * 100) / m.range.max
                        # print("p_dev:")
                        # print(p_dev)

            #
            # calculate the percentaged value in relation to all values in the array to weight it proportionally and add
            # it to deviations
            #
            if len(measurement_values) == 0:
                deviations += [0]
            else:
                deviations += [p_dev/len(measurement_values)]
            # print("deviations:")
            # print(deviations)

        #
        # transform deviations to a numpy array after all separate deviations for different measurements m have been
        # collected
        #
        dev_array = numpy.array(deviations)
        # print(dev_array)

        #
        # Add measurement for deviations to workspace measurements to make it available to downstream modules,
        # e.g. the Bayesian Module
        #
        workspace.add_measurement(self.input_object_name.value, FEATURE_NAME, dev_array)

    ####################################################################
    # Tell CellProfiler about the measurements produced in this module #
    ####################################################################

    #
    # Provide the measurements for use in the database or a spreadsheet
    #
    def get_measurement_columns(self, pipeline):

        input_object_name = self.input_object_name.value

        return [input_object_name, FEATURE_NAME, cellprofiler.measurement.COLTYPE_FLOAT]

    #
    # Return a list of the measurement categories produced by this module if the object_name matches
    #
    def get_categories(self, pipeline, object_name):
        if object_name == self.input_object_name:
            return [CATEGORY]

        return []

    #
    # Return the feature names if the object_name and category match to the GUI for measurement subscribers
    #
    def get_measurements(self, pipeline, object_name, category):
        if object_name == self.input_object_name and category == CATEGORY:
            return [DEVIATION]

        return []





