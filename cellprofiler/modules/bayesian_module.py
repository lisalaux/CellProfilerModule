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
MeasurementTemplate
===================

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          NO           YES
============ ============ ===============


"""

#
# Constants
#
# It's good programming practice to replace things like strings with
# constants if they will appear more than once in your program. That way,
# if someone wants to change the text, that text will change everywhere.
# Also, you can't misspell it by accident.
#
'''This is the measurement template category'''
C_MEASUREMENT_TEMPLATE = "MT"


#
# The module class
#
# Your module should "inherit" from cellprofiler.module.Module.
# This means that your module will use the methods from Module unless
# you re-implement them. You can let Module do most of the work and
# implement only what you need.
#

import pdb
import pdbi


class BayesianOptimisation(cellprofiler.module.Module):
    module_name = "BayesianOptimisation"
    category = "Advanced"
    variable_revision_number = 1

    def create_settings(self):
        module_explanation = [
            "BlaBlaBla"]

        self.set_notes([" ".join(module_explanation)])
        self.number_of_parameters = cellprofiler.setting.Integer(
            text="Number of parameters",
            value=5,
            minval=1,
            maxval=8,
            doc="""\
BlaBlaBla
"""
        )

        self.divider = cellprofiler.setting.Divider()
        self.parameters = []
        self.add_parameter(can_remove=False)
        self.param_count = cellprofiler.setting.HiddenCount(self.parameters)
        self.add_param_button = cellprofiler.setting.DoSomething("", "Add parameter", self.add_parameter)

    def add_parameter(self, can_remove=True):
        '''Add parameter to the collection
        '''
        counter = 1
        group = cellprofiler.setting.SettingsGroup()
        if can_remove:
            group.append("divider", cellprofiler.setting.Divider(line=False))
        group.append("parameter_names", cellprofiler.setting.Choice(
            "Select parameter "+str(counter),
            choices=["None"],
            choices_fn=self.get_settings_from_modules,
            doc="""\
BlaBlaBla
"""
        ))
        if can_remove:
            group.append("remover",
                         cellprofiler.setting.RemoveSettingButton("", "Remove parameters", self.parameters, group))
        self.parameters.append(group)
        counter += 1

        # needs to update settings after button click! function call too slow?
        # need counter for max count of 8

    def settings(self):
        result = [self.param_count, self.number_of_parameters]
        result += [param.parameter_names for param in self.parameters]
        return result

    def visible_settings(self):
        result = []
        result += [self.number_of_parameters]
        for param in self.parameters:
            result += param.visible_settings()
        result += [self.add_param_button, self.divider]
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

    def get_settings_from_modules(self, pipeline):
        setting_list = []
        modules = pipeline.modules()

        print(modules)
        print("*"*20)
        for module in modules:
            if module.module_name == "IdentifyPrimaryObjects" or "FillObjects":
                for setting in module.settings():
                    if any(c.isdigit() for c in str(setting.get_value())):
                        setting_list.append("{}: {}".format(setting.get_text(), setting.get_value()))
        print("called")
        return setting_list


if __name__ == "__main__":
    pdb.set_trace()
    pipeline = cellprofiler.pipeline.Pipeline()
    pipeline.load("/Users/LisaLaux/Documents/Master_UofG/Master_Project/CellProfiler/ExampleHuman/ExampleHuman.cppipe")
    print("="*5)
    print(pipeline.modules())
    bo = BayesianOptimisation()

