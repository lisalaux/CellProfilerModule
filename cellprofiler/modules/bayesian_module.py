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
BayesianOptmisation Module
===================

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          NO           YES
============ ============ ===============


"""

import pdb
import pdbi


class BayesianOptimisation(cellprofiler.module.Module):
    module_name = "BayesianOptimisation"
    category = "Advanced"
    variable_revision_number = 1

    def create_settings(self):
        module_explanation = [
            "This module uses BayesianOptimisation on parameters (settings) chosen from modules placed before this "
            "module in the pipeline. Step 1: Place Manual or Automated Evaluation modules before Bayesian "
            "Optimisation. Step 2: Choose the evaluation modules this Bayesian module should consider as quality "
            "indicators. Bayesian Optimisation will be executed if required quality thresholds are not met."]

        self.set_notes([" ".join(module_explanation)])

        self.modules = []
        self.add_module(can_remove=False)
        self.module_count = cellprofiler.setting.HiddenCount(self.modules)
        self.add_module_button = cellprofiler.setting.DoSomething("", "Add module", self.add_module)

        self.divider = cellprofiler.setting.Divider()

        self.number_of_parameters = cellprofiler.setting.Integer(
            text="Number of parameters",
            value=5,
            minval=1,
            maxval=8,
            doc="""\
BlaBlaBla
"""
        )

        self.parameters = []
        self.add_parameter(can_remove=False)
        self.param_count = cellprofiler.setting.HiddenCount(self.parameters) # may not work because holds both settings and modules
        self.add_param_button = cellprofiler.setting.DoSomething("", "Add parameter", self.add_parameter)
        self.refresh_button = cellprofiler.setting.DoSomething("", "Refresh", self.refreshGUI)

        # parameters is a list of SettingsGroup objects
        # each SettingsGroup holds settings Objects; these objects have names

    def add_module(self, can_remove=True):
        '''Add modules to the collection
        '''

        group = cellprofiler.setting.SettingsGroup()

        group.append("evaluation_module_names", cellprofiler.setting.Choice(
            "Select evaluation module",
            choices=[""],
            choices_fn=self.get_evaluation_module_list,
            doc="""\
       BlaBlaBla
       """
        ))

        if can_remove:
            group.append("remover",
                         cellprofiler.setting.RemoveSettingButton("", "Remove module", self.modules, group))
        self.modules.append(group)

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
        result += [mod.evaluation_module_names for mod in self.modules]
        result += [self.module_count]
        result += [self.number_of_parameters]
        result += [self.param_count]
        result += [mod.module_names for mod in self.parameters]
        result += [param.parameter_names for param in self.parameters]
        return result

    def visible_settings(self):
        result = []
        for mod in self.modules:
            result += mod.visible_settings()
        result += [self.add_module_button]
        result += [self.divider]
        result += [self.number_of_parameters]
        for param in self.parameters:
            result += param.visible_settings()
        result += [self.add_param_button]
        result += [self.refresh_button]
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

    def get_module_list(self, pipeline):
        modules = pipeline.modules()
        module_list = []
        for module in modules:
            module_list.append(str(module.module_name))
        return module_list

    def get_evaluation_module_list(self, pipeline):
        all_modules = pipeline.modules()
        evaluation_module_list = []
        for m in all_modules:
            if "Evaluation" in str(m.module_name):
                evaluation_module_list.append("{} #{}".format(m.module_name, m.get_module_num()))
        return evaluation_module_list

    def get_settings_from_modules(self, pipeline):
        setting_list = []
        modules = pipeline.modules()
        mod_name_list = []
        for parameter in self.parameters:
            mod_name_list += [parameter.module_names]

        names = []

        for m in mod_name_list:
            names += [m.get_value()]

        # for n in names:
        #     print(n)

        for module in modules:
            if module.module_name in names:
                for setting in module.visible_settings():
                    #if any(c.isdigit() for c in str(setting.get_value())):
                        setting_list.append("{}: {}".format(setting.get_text(), setting.get_value()))


        #print("called")
        return setting_list

    def refreshGUI(self):
        print("GUI refreshed")


if __name__ == "__main__":
    pdb.set_trace()
    pipeline = cellprofiler.pipeline.Pipeline()
    pipeline.load("/Users/LisaLaux/Documents/Master_UofG/Master_Project/CellProfiler/ExampleHuman/ExampleHuman.cppipe")
    print("="*5)
    print(pipeline.modules())
    bo = BayesianOptimisation()

