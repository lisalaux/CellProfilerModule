# coding=utf-8

#################################
#
# Imports from useful Python libraries
#
#################################

import numpy
# import pdb
# import pdbi

#################################
#
# Imports from CellProfiler
#
##################################

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
(eg nuclei, cytoplasm, adhesions). It needs to be placed after both, IdentifyObjects and Measurement modules. 

By choosing an objects and some of its measurements to be evaluated, the module will check whether these measurements
are in a tolerance range provided in the settings. If object measurement values are outside this range, a 
deviation per value will be measured and saved with the object measurements in an numpy array.

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          YES           NO
============ ============ ===============

"""

#
# Constants
#
CATEGORY = 'Evaluation'
DEVIATION = 'Deviation'
FEATURE_NAME = 'Evaluation_Deviation'


class AutomatedEvaluation(cellprofiler.module.Module):
    module_name = "AutomatedEvaluation"
    category = "Advanced"
    variable_revision_number = 1

    #######################################################################
    # Create and set CellProfiler settings for GUI and Pipeline execution #
    #######################################################################

    def create_settings(self):
        super(AutomatedEvaluation, self).create_settings()

        module_explanation = [
            "Module used to automatically evaluate the quality of identified objects (eg nuclei, adhesions). "
            "Needs to be placed after IdentifyObjects and Measurement modules. Choose the measurements to be evaluated"
            "and set a tolerance range for their values. If objects are outside this range, a deviation will be "
            "measured and saved with the object."]

        self.set_notes([" ".join(module_explanation)])

        self.input_object_name = cellprofiler.setting.ObjectNameSubscriber(
            "Input object name", cellprofiler.setting.NONE,
            doc="These are the objects that the module operates on.")

        self.measurements = []

        self.add_measurement(can_delete=False)

        self.add_measurement_button = cellprofiler.setting.DoSomething(
            "", "Add another measurement", self.add_measurement)

    #
    # add measurements grouped with corresponding quality ranges
    # add a remove-button for all measurements except a mandatory one
    #
    def add_measurement(self, can_delete=True):
        group = cellprofiler.setting.SettingsGroup()

        group.append(
            "measurement",
            cellprofiler.setting.Measurement(
                "Select the quality measurement",
                self.input_object_name.get_value,
                "AreaShape_Area",
                doc="""\
See the **Measurements** modules help pages for more information on the
features measured."""

            )
        )

        group.append(
            "range",
            cellprofiler.setting.FloatRange(
                'Set tolerance range',
                (00.00, 100.00),
                minval=00.00,
                maxval=1000.00,
                doc="""\
Blabla"""
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

    def settings(self):
        super(AutomatedEvaluation, self).settings()

        result = [self.input_object_name]
        for measurement in self.measurements:
            result += [measurement.measurement, measurement.range]
        return result

    def visible_settings(self):
        super(AutomatedEvaluation, self).visible_settings()

        result = [self.input_object_name]
        for measure in self.measurements:
            result += measure.visible_settings()
        result += [self.add_measurement_button]
        return result

    ####################################################################
    # Run method will be exectued in a worker thread of the pipeline #
    ####################################################################
    #
    # CellProfiler calls "run" on each image set in your pipeline.
    #
    def run(self, workspace):

        # Get the measurements object for the current run
        workspace_measurements = workspace.measurements

        deviations = []

        # take the selected object's measurements and corresponding ranges one by one and compare it to the thresholds
        for m in self.measurements:

            p_dev = 0

            # this gives back an array with the measurements per object in the image set
            measurement_values = workspace_measurements.get_current_measurement(self.input_object_name.value_text,
                                                                                m.measurement.value_text)

            print(measurement_values)

            # loop through all entries of the array to determine whether they are within the quality range or not;
            # if not, determine the deviation and save the deviation values
            for v in measurement_values:
                if v >= m.range.min and v <= m.range.max:
                    print("passed")
                else:
                    print("not passed")

                    if v < m.range.min:
                        deviation = m.range.min - v
                        p_dev += (deviation*100)/m.range.min
                        print("p_dev:")
                        print(p_dev)
                    else:
                        deviation = v - m.range.max
                        p_dev += (deviation * 100) / m.range.max
                        print("p_dev:")
                        print(p_dev)

            deviations += [p_dev]
            print("deviations:")
            print(deviations)

        dev_array = numpy.array(deviations)
        # print(dev_array)

        # Add measurement for deviations to workspace measurements to make it available to Bayesian Module
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
    # Return the feature names if the object_name and category match to GUI
    #
    def get_measurements(self, pipeline, object_name, category):
        if (object_name == self.input_object_name and category == CATEGORY):
            return [DEVIATION]

        return []


