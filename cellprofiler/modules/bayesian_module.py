# coding=utf-8

#################################
#
# Imports from useful Python libraries
#
#################################

import numpy
import scipy.ndimage
import GPy
import GPyOpt
from numpy.random import seed
import matplotlib

import pdb
import pdbi

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
BayesianOptmisation Module
===================

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          NO           YES
============ ============ ===============


"""


class BayesianOptimisation(cellprofiler.module.Module):
    module_name = "BayesianOptimisation"
    category = "Advanced"
    variable_revision_number = 1

    def create_settings(self):
        module_explanation = [
            "This module uses BayesianOptimisation on parameters (settings) chosen from modules placed before this "
            "module in the pipeline. Step 1: Place Manual or Automated Evaluation modules before Bayesian "
            "Optimisation. Step 2: Choose the objects which you have evaluatied in the evaluation modules. The "
            "Bayesian module should consider these measures as quality"
            "indicators. Bayesian Optimisation will be executed if required quality thresholds/ranges are not met."]

        self.set_notes([" ".join(module_explanation)])

        self.input_object_name = cellprofiler.setting.ObjectNameSubscriber(
            "Input object name", cellprofiler.setting.NONE,
            doc="These are the objects that the module operates on.")

        self.measurements = []

        self.add_measurement(can_delete=False)

        self.add_measurement_button = cellprofiler.setting.DoSomething(
            "", "Add another measurement", self.add_measurement)

        self.spacer = cellprofiler.setting.Divider(line=True)

        self.parameters = []
        self.add_parameter(can_remove=False)
        self.add_param_button = cellprofiler.setting.DoSomething("", "Add parameter", self.add_parameter)
        self.refresh_button = cellprofiler.setting.DoSomething("", "Refresh", self.refreshGUI)

    def add_measurement(self, can_delete=True):
        '''Add another measurement to the filter list'''
        group = cellprofiler.setting.SettingsGroup()

        group.append(
            "evaluation_measurement",
            cellprofiler.setting.Measurement(
                "Select measurements for evaluation",
                self.input_object_name.get_value,
                "Evaluation_Deviation",
                doc="""\
See the **Measurements** modules help pages for more information on the
features measured."""

            )
        )

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

    def add_parameter(self, can_remove=True):
        '''Add parameter to the collection
        '''

        group = cellprofiler.setting.SettingsGroup()

        if can_remove:
            group.append("divider", cellprofiler.setting.Divider(line=False))

        group.append("module_names", cellprofiler.setting.Choice(
            "Select module",
            choices=[""],
            choices_fn=self.get_module_list,
            doc="""\
BlaBlaBla
"""
        ))

        group.append("parameter_names", cellprofiler.setting.Choice(
            "Select parameter",
            choices=[""],
            choices_fn=self.get_settings_from_modules,
            doc="""\
BlaBlaBla
"""
        ))

        if can_remove:
            group.append("remover",
                         cellprofiler.setting.RemoveSettingButton("", "Remove parameter", self.parameters, group))
        self.parameters.append(group)

        # needs to update settings after button click! function call too slow?
        # need counter for max count of 8

    def settings(self):
        result = []
        result += [self.input_object_name]
        result += [m.evaluation_measurement for m in self.measurements]
        result += [mod.module_names for mod in self.parameters]
        result += [param.parameter_names for param in self.parameters]
        return result

    def visible_settings(self):
        result = []
        result += [self.input_object_name]
        for mod in self.measurements:
            result += mod.visible_settings()
        result += [self.add_measurement_button, self.spacer]
        for param in self.parameters:
            result += param.visible_settings()
        result += [self.add_param_button]
        result += [self.refresh_button]
        return result


    #
    # CellProfiler calls "run" on each image set in your pipeline.
    #
    def run(self, workspace):

        workspace_measurements = workspace.measurements

        pipeline = workspace.get_pipeline()

        optimisation_on = False

        evaluation_results = []

        #
        # determine whether optimisation is needed or not
        #
        for m in self.measurements:

            evaluation_results = workspace_measurements.get_current_measurement(self.input_object_name.value,
                                                                               m.evaluation_measurement.value_text)

            print(evaluation_results)

            evaluation_results += evaluation_results

            for e in evaluation_results:
                if float(e) > 0.0:
                    optimisation_on = True

        if optimisation_on:
            #
            # get modules and their settings
            #
            number_of_params = self.parameters.__len__()
            print("Number of params: {}".format(number_of_params))

            target_setting_module_list = []
            target_setting_names_list = []
            target_setting_values_list = []

            for module in self.parameters:
                name_list = module.module_names.value_text.split(" #")
                number = int(name_list[1])
                target_module = pipeline.module(number)

                print(target_module.module_name)
                target_setting_module_list += [number]

                set_list = module.parameter_names.value_text.split(": ")
                target_setting_name = set_list[0]

                for setting in target_module.settings():
                    if setting.get_text() == target_setting_name:
                        print("Setting name: "+setting.get_text())
                        target_setting_names_list += [setting.get_text()]
                        print("Old setting value: "+setting.get_value())
                        target_setting_values_list += [setting.get_value()]

            #
            # do the bayesian optimisation with a new function that takes the 3 lists and alters the values_list
            #
            new_target_settings = self.bayesian_optimisation(evaluation_results, target_setting_module_list,
                                                             target_setting_names_list, target_setting_values_list)

            #
            # modify modules with new setting values
            #
            for i in range(number_of_params):
                target_module = pipeline.module(target_setting_module_list[i])
                for setting in target_module.settings():
                    if setting.get_text() == target_setting_names_list[i]:
                        print("Setting name: "+setting.get_text())
                        setting.set_value(new_target_settings[i])
                        pipeline.edit_module(target_setting_module_list[i], is_image_set_modification=False)
                        print("New setting value: "+setting.get_value())

            # pipeline re-runs automatically from where module has been changed; modules therefore need to be in order!
            # problem: pipeline runs only so many times as it has modules in total
            # --> need to find a way to re-set count
            start_module = pipeline.module(5)
            workspace.set_module(start_module)

        else:
            print("no optimisation")

    #
    # Return a list of all pipeline modules
    #
    def get_module_list(self, pipeline):
        modules = pipeline.modules()
        module_list = []
        for module in modules:
            module_list.append("{} #{}".format(module.module_name, module.get_module_num()))
        return module_list

    #
    # Return a list of settings from the chosen modules
    #
    def get_settings_from_modules(self, pipeline):
        setting_list = []
        modules = pipeline.modules()
        mod_name_list = []

        for parameter in self.parameters:
            name_list = parameter.module_names.value_text.split(" ")
            name = name_list[0]
            mod_name_list += [name]

        for module in modules:
            if module.module_name in mod_name_list:
                for setting in module.visible_settings():
                    setting_list.append("{}: {}".format(setting.get_text(), setting.get_value()))

        return setting_list

    #
    # Necessary to refresh the dropdown menus in GUI
    #
    def refreshGUI(self):
        print("GUI refreshed")

    #
    # Apply bayesian optimisation to adjust settings for next pipeline run
    #
    def bayesian_optimisation(self, evaluation_results, module_list, names_list, values_list):
        # do the optimisation and return new values in values_list
        new_values = values_list
        new_values[0] = "Gaussian Filter"
        new_values[1] = "Two classes"

        return new_values
