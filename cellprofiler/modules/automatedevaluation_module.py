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
                (0.00, 100.00),
                minval=0.00,
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
        # settings = super(AutomatedEvaluation, self).settings()
        #
        # #settings += [self.measurement_count]
        #
        # for x in self.measurements:
        #     settings += x.pipeline_settings()
        #     settings += [x.range]
        # return settings

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
        #
        # Get the measurements object - we put the measurements we
        # make in here
        #
        # pdb.set_trace()
        measurements = workspace.measurements
        print(measurements)
        for measure in measurements:
            print(measure)



if __name__ == "__main__":
    pdb.set_trace()
    pipeline = cellprofiler.pipeline.Pipeline()
    pipeline.load("/Users/LisaLaux/Documents/Master_UofG/Master_Project/CellProfiler/ExampleHuman/ExampleHuman.cppipe")
    print("="*5)
    print(pipeline.modules())
    ae = AutomatedEvaluation()

