# coding=utf-8

#################################
#
# Imports from useful Python libraries
#
#################################

import numpy
import scipy.ndimage

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
AutomatedEvaluation Module
===================

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          NO           YES
============ ============ ===============


"""


import pdb
import pdbi


class AutomatedEvaluation(cellprofiler.module.Module):
    module_name = "AutomatedEvaluation"
    category = "Advanced"
    variable_revision_number = 1

    def create_settings(self):
        super(AutomatedEvaluation, self).create_settings()

        module_explanation = [
            "Module used to automatically evaluate quality of identifying objects (eg nuclei, adhesions). "
            "Needs to be placed after IdentifyObjects and Measurement modules"]

        self.set_notes([" ".join(module_explanation)])

        self.input_object_name = cellprofiler.setting.ObjectNameSubscriber(
            text="Input object name",
            doc="These are the objects that the module operates on.")

        self.measurements = []

        #self.measurement_count = cellprofiler.setting.HiddenCount(self.measurements, "Measurement count")

        self.add_measurement(can_delete=False)

        self.add_measurement_button = cellprofiler.setting.DoSomething(
            "", "Add another measurement", self.add_measurement)

    def add_measurement(self, can_delete=True):
        '''Add another measurement to the filter list'''
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
                maxval=100.00,
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


    #
    # CellProfiler calls "run" on each image set in your pipeline.
    #
    def run(self, workspace):

        # Get the measurements object for the current run
        workspace_measurements = workspace.measurements

        pass_thresholds = True

        # take the selected object's measurements one by one and compare it to the thresholds
        for m in self.measurements:

            if not pass_thresholds: # more efficient; breaks when there is one false measurement
                break

            measurement_values = workspace_measurements.get_current_measurement(self.input_object_name.value_text,
                                                                                m.measurement.value_text)
            # this gives back an array with the measurements per object in the image set; this means that
            # if there are 3 objects, array holds 3 measurements, if there's only 1, array holds 1
            print(measurement_values)
            print("*************")

            """loop through all entries of the array to determine whether they pass the quality threshold or not
            """ # !this is a very strict way, would work for nuclei but also adhesions?
            for v in measurement_values:
                print("Measurement name: {}".format(m.measurement.get_value()))
                print("Measurement value: {}".format(v))
                print("Range: {} to {}".format(m.range.min, m.range.max))
                if v >= m.range.min and v <= m.range.max:
                    print("passed")
                else:
                    print("not passed")
                    pass_thresholds = False
                    break
                print("***")

        print(pass_thresholds)

        """Add measurement (boolean value) to workspace measurements to make it available to Bayesian Module
        """
        workspace.add_measurement("Image", "passed", pass_thresholds)


        # test only
        workspace_measurements2 = workspace.measurements

        measurement_values2 = workspace_measurements2.get_current_measurement("Image", "passed")
        print("++++++++")
        print(measurement_values2)



