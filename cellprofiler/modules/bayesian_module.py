# coding=utf-8

#################################
#
# Imports from useful Python libraries
#
#################################

import numpy as np
import sklearn.gaussian_process as gp
from scipy.stats import norm
import matplotlib.pyplot as plt
from copy import deepcopy
from itertools import product
import os

# import pdb
# import pdbi

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
BayesianOptimisation
===================

**BayesianOptimisation** uses Bayesian Optimisation methods on parameters (settings) chosen from modules placed before 
this module in the pipeline. It needs either a ManualEvaluation or AutomatedEvaluation or both modules placed beforehand 
in the pipeline. It can only evaluate and operate on the quality measurements of one object at a time. 

The Bayesian Optimisation will only be executed if required quality thresholds/ranges defined in the evaluation 
module(s) are not met.

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          YES           NO
============ ============ ===============


Requirements
^^^^^^^^^^^^
There must be at least one evaluation module, either **ManualEvaluation** or **AutomatedEvaluation** placed
before this module in order to have evaluation measurements available.
Either only one or both evaluation measurements can be chosen to be taken as quality measure for the optimisation 
procedure.


Technical notes
^^^^^^^^^^^^^^
The max. number of parameters to optimise is currently 4. 
There is a filter set for only making parameters form the IdentifyObjects modules available for optimisation. This 
can be changed by just removing the filter in the get_module_list helper method.


References
^^^^^^^^^^
The basic code for the Bayesian Optimisation procedure was provided by Bjørn Sand Jensen (University of Glasgow) 
-- bjorn.jensen@glasgow.ac.uk -- and altered for the purposes of this module.

"""

#
# Constants
#
NUM_FIXED_SETTINGS = 4
NUM_GROUP1_SETTINGS = 1
NUM_GROUP2_SETTINGS = 4

#
# for testing/ prinout purposes only
#
np.set_printoptions(suppress=True)
# np.set_printoptions(threshold=np.nan)


#
# Create module class which inherits from cellprofiler.module.Module class
#
class BayesianOptimisation(cellprofiler.module.Module):

    #
    # Declare the name for displaying the module, e.g. in menus 
    # Declare the category under which it is stored and grouped in the menu
    # Declare variable revision number which can be used to provide backwards compatibility  if CellProfiler will be
    # released in a new version
    #
    module_name = "BayesianOptimisation"
    category = "Advanced"
    variable_revision_number = 1

    #######################################################################
    # Create and set CellProfiler settings for GUI and Pipeline execution #
    #######################################################################

    #
    # Define the setting's data types and grouped elements
    #
    def create_settings(self):
        module_explanation = [
            "This module uses BayesianOptimisation on parameters (settings) chosen from modules placed before this "
            "module in the pipeline. Step 1: Choose the objects which you have evaluated in the evaluation modules. "
            "The Bayesian module should consider these measures as quality indicators. Step 2: Choose the parameters "
            "(settings) to be adjusted. Bayesian Optimisation will be executed if required quality thresholds/ranges "
            "are not met."]

        #
        # Notes will appear in the notes-box of the module
        #
        self.set_notes([" ".join(module_explanation)])

        #
        # Object identified in upstream IndentifyObjects module; accessible via ObjectNameSubscriber
        #
        self.input_object_name = cellprofiler.setting.ObjectNameSubscriber(
            "Input object name", cellprofiler.setting.NONE,
            doc="These are the objects that the module operates on.")

        #
        # The number of evaluation modules as input for BayesianModule;
        # necessary for prepare_settings method
        #
        self.count1 = cellprofiler.setting.cellprofiler.setting.Integer(
                'No. of evaluation modules',
                1,
                minval=1,
                maxval=2,
                doc="""\
No. of evaluation modules before BayesianModule."""
            )

        #
        # The number of parameters to be adjusted by  BayesianModule;
        # necessary for prepare_settings method
        #
        self.count2 = cellprofiler.setting.cellprofiler.setting.Integer(
            'No. of settings to be adjusted',
            2,
            minval=1,
            maxval=4,
            doc="""\
No. of settings that should be adjusted by BayesianModule."""
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

        self.spacer = cellprofiler.setting.Divider(line=True)

        #
        # The maximum number of iterations for the Bayesian Optimisation
        #
        self.max_iter = cellprofiler.setting.cellprofiler.setting.Integer(
            'Max. iterations for Bayesian Optimisation',
            150,
            minval=2,
            maxval=1000,
            doc="""\
Define the maximum number of iterations the Bayesian Optimisation should run. The minimum number is 2, 
recommended iterations are 20 - 200, depending on the problem to be solved. """
        )

        self.spacer4 = cellprofiler.setting.Divider(line=True)

        self.parameters = []

        #
        # Add first parameter which cannot be deleted; there must be at least one
        #
        self.add_parameter(can_remove=False)

        #
        # Button for adding additional parameters; calls add_parameter helper function
        #
        self.add_param_button = cellprofiler.setting.DoSomething("", "Add parameter", self.add_parameter)

        self.spacer2 = cellprofiler.setting.Divider(line=True)

        #
        # Button for refreshing the GUI; calls refreshGUI helper function
        # This is necessary as the choices_fn function does not work without
        # refreshing the GUI if new groups were added
        #
        self.refresh_button = cellprofiler.setting.DoSomething("", "Refresh GUI", self.refreshGUI)

        self.spacer3 = cellprofiler.setting.Divider(line=True)

        #
        # Button for deleting existing files storing values from previous runs
        #
        self.delete_button = cellprofiler.setting.DoSomething(
            "",
            "Delete previous Data",
            self.delete_data,
            doc="""\
If there is previously gathered data saved in a file you can choose to delete it."""
        )

    #
    # helper function:
    # add the quality measurements which should be considered by B.O.
    # add a remove-button for all measurements except a mandatory one
    #
    def add_measurement(self, can_delete=True):
        group = cellprofiler.setting.SettingsGroup()

        #
        # Dropdown selection for measurements taken for the object
        #
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

    #
    # helper function:
    # add parameters grouped with corresponding modules
    # add a remove-button for all parameters except a mandatory one
    #
    def add_parameter(self, can_remove=True):

        group = cellprofiler.setting.SettingsGroup()

        if can_remove:
            group.append("divider", cellprofiler.setting.Divider(line=False))

        #
        # Dropdown selection for modules (IdentifyObjects modules)
        #
        group.append("module_names", cellprofiler.setting.Choice(
            "Select module",
            choices=[""],
            choices_fn=self.get_module_list,
            doc="""\
This is the module where Bayesian Optimisation will adjust settings
"""
        ))

        #
        # Dropdown selection for parameters of the selected modules
        #
        group.append("parameter_names", cellprofiler.setting.Choice(
            "Select parameter",
            choices=[""],
            choices_fn=self.get_settings_from_modules,
            doc="""\
These are the settings to be adjusted by Bayesian Optimisation
"""
        ))

        #
        # The parameters will be adjusted within this range
        #
        group.append(
            "range",
            cellprofiler.setting.FloatRange(
                'Set min and max boundaries for variation',
                (1.00, 100.00),
                minval=00.00,
                maxval=1000.00,
                doc="""\
The Bayesian Optimisation will vary the parameter within this range of candidates. Please note that the lower
bound is inclusive, the upper bound is exclusive."""
            )
        )

        #
        # The parameters will be adjusted within this range
        #
        group.append(
            "steps",
            cellprofiler.setting.Float(
                'Set steps between boundaries',
                0.1,
                minval=00.00,
                maxval=10.00,
                doc="""\
The variation steps within the chosen range for choosing a candidate set."""
            )
        )

        if can_remove:
            group.append("remover",
                         cellprofiler.setting.RemoveSettingButton("", "Remove parameter", self.parameters, group))

        self.parameters.append(group)

    #
    # setting_values are stored as unicode strings in the pipeline.
    # If the module has settings groups, it needs to be ensured that settings() returns the correct
    # number of settings as saved in the file.
    # To do so, look at the setting values before settings() is called to determine how many to return.
    # Add groups if necessary.
    #
    def prepare_settings(self, setting_values):

        #
        # No. of measurements in measurements group
        #
        count1 = int(setting_values[1])
        #
        # No. of parameters in parameters group
        #
        count2 = int(setting_values[2])

        #
        # Handle adding measurements
        #
        num_settings_1 = (len(setting_values) - NUM_FIXED_SETTINGS - NUM_GROUP2_SETTINGS*count2) / NUM_GROUP1_SETTINGS

        if len(self.measurements) == 0:
            self.add_measurement(False)
        elif len(self.measurements) > num_settings_1:
            del self.measurements[num_settings_1:]
        else:
            for i in range(len(self.measurements), num_settings_1):
                self.add_measurement()

        #
        # Handle adding parameters
        #
        num_settings_2 = (len(setting_values) - NUM_FIXED_SETTINGS - NUM_GROUP1_SETTINGS * count1) / NUM_GROUP2_SETTINGS

        if len(self.parameters) == 0:
            self.add_parameter(False)
        elif len(self.parameters) > num_settings_2:
            del self.parameters[num_settings_2:]
        else:
            for i in range(len(self.parameters), num_settings_2):
                self.add_parameter()

    #  
    # CellProfiler must know about the settings in the module.
    # This method returns the settings in the order that they will be loaded and saved from a pipeline or project file.
    # Accessing setting members of a group of settings requires looping through the group result list
    #
    def settings(self):
        result = [self.input_object_name]
        result += [self.count1]
        result += [self.count2]
        for m in self.measurements:
            result += [m.evaluation_measurement]
        result += [self.max_iter]
        for p in self.parameters:
            result += [p.module_names, p.parameter_names, p.range, p.steps]

        return result

    #  
    # returns what the user should see in the GUI
    # include buttons and dividers which are not added in the settings method
    #
    def visible_settings(self):
        result = [self.input_object_name]
        result += [self.count1]
        for mod in self.measurements:
            result += [mod.evaluation_measurement]
            if hasattr(mod, "remover"):
                result += [mod.remover]
        result += [self.add_measurement_button, self.spacer, self.max_iter, self.spacer4]
        result += [self.count2]
        for param in self.parameters:
            if hasattr(param, "divider"):
                result += [param.divider]
            result += [param.module_names, param.parameter_names, param.range, param.steps]
            if hasattr(param, "remover"):
                result += [param.remover]
        result += [self.add_param_button, self.spacer2, self.refresh_button, self.spacer3, self.delete_button]
        return result

    ###################################################################
    # Run method will be executed in a worker thread of the pipeline #
    ###################################################################

    #
    # CellProfiler calls "run" on each image set in the pipeline
    # The workspace as input parameter contains the state of the analysis so far
    #
    def run(self, workspace):

        workspace_measurements = workspace.measurements

        pipeline = workspace.get_pipeline()

        self.optimisation_on = False

        manual_evaluation_result = []
        auto_evaluation_results = []

        #
        # save the quality measurements and determine whether optimisation is needed or not
        #
        for m in self.measurements:

            if m.evaluation_measurement.value_text == "Evaluation_ManualQuality":
                manual_evaluation_result = workspace_measurements.get_current_measurement(
                    self.input_object_name.value, m.evaluation_measurement.value_text)
                for e in manual_evaluation_result:
                    if float(e) > 0.0:
                        self.optimisation_on = True

            elif m.evaluation_measurement.value_text == "Evaluation_Deviation":
                auto_evaluation_results = workspace_measurements.get_current_measurement(
                    self.input_object_name.value, m.evaluation_measurement.value_text)
                for e in auto_evaluation_results:
                    if float(e) > 0.0:
                        self.optimisation_on = True

        #
        # start optimisation if quality is not satisfying
        #
        if self.optimisation_on:

            #
            # get modules and their settings
            #
            number_of_params = self.parameters.__len__()
            print("Number of params: {}".format(number_of_params))

            # save operational data in lists; the lists operate with indices;
            # an indices corresponds to a certain module, a setting name in this module and the value of this setting
            target_setting_module_list = []     # saves module objects
            target_setting_names_list = []      # saves setting names
            target_setting_values_list = []     # saves setting values of the selected settings in the module
            target_setting_range = []           # saves the ranges in which the setting values shall be manipulated
            target_setting_steps = []           # saves the steps the range can vary


            #
            # get the data for the lists by looping through all settings chosen by the user
            #
            for p in self.parameters:

                #
                # get the module object
                #
                name_list = p.module_names.value_text.split(" #")
                number = int(name_list[1])
                target_module = pipeline.module(number)

                #
                # save module number in module_list
                #
                target_setting_module_list += [number]

                #
                # get the setting name
                #
                target_setting_name = p.parameter_names.value_text

                for setting in target_module.settings():
                    if setting.get_text() == target_setting_name:
                        #
                        # add setting name to Names_list and setting value to values_list
                        #
                        target_setting_names_list += [setting.get_text()]
                        target_setting_values_list += [setting.get_value()]

                #
                # save range and steps into lists; ranges are saved as a tuple
                #
                target_setting_range += [p.range.value]
                target_setting_steps += [float(p.steps.value)]

            #
            # do the bayesian optimisation with a new function that takes the lists and returns new parameters for
            # the settings
            #
            new_target_settings_array, current_y_values = self.bayesian_optimisation(manual_evaluation_result,
                                                                                     auto_evaluation_results,
                                                                                     target_setting_values_list,
                                                                                     target_setting_range,
                                                                                     target_setting_steps,
                                                                                     self.max_iter.get_value())

            print("New_target_setting_array")
            print(new_target_settings_array)

            print("Current y")
            print(current_y_values)

            #
            # indicates that max_interations are reached and B.O. is finished
            #
            if new_target_settings_array is None:
                self.optimisation_on = False

            #
            # adjust the module settings with new x parameters returned form B.O.
            #
            else:
                new_target_settings = new_target_settings_array.flatten()
                current_y_values = current_y_values.flatten()

                #
                # modify modules with new setting values
                #
                for i in range(number_of_params):
                    target_module = pipeline.module(target_setting_module_list[i])
                    for setting in target_module.settings():
                        if setting.get_text() == target_setting_names_list[i]:
                            setting.set_value(new_target_settings[i])

                            #
                            # inform the pipeline about the edit
                            # pipeline re-runs from where the module has been changed
                            #
                            pipeline.edit_module(target_setting_module_list[i], is_image_set_modification=False)

                # problem: pipeline runs only so many times as it has modules in total
                # --> need to find a way to re-set count
                # start_module = pipeline.module(5)

                # sth with debug-mode on if-statement
                # workspace.set_module(start_module)
                # workspace.set_disposition(cellprofiler.workspace.DISPOSITION_CONTINUE)

                # does not work with gui
                # pipelist = cellprofiler.gui.pipelinelistview.PipelineListView()
                # cellprofiler.gui.pipelinelistview.PipelineListView.set_current_debug_module(pipelist, start_module)

                #
                # if user wants to show the display-window, save data needed for display in workspace.display_data
                #
                if self.show_window:
                    workspace.display_data.statistics = []
                    for i in range(number_of_params):
                        workspace.display_data.statistics.append(
                            (target_setting_names_list[i], target_setting_values_list[i], new_target_settings[i]))

                    workspace.display_data.col_labels = ("Setting Name", "Old Value", "New Value")
                    workspace.display_data.y_values = current_y_values

        else:

            print("no optimisation")

    #
    # if user wants to show the display window during pipeline execution, this method is called by UI thread
    # display the data saved in display_data of workspace
    # used a CP defined figure to plot/display data via matplotlib
    #
    def display(self, workspace, figure):
        #
        # data plotted when BO was run
        #
        if self.optimisation_on:
            #
            # create two subplots
            #
            figure.set_subplots((1, 2))

            #
            # prepare first plot showing a scatter plot with the development of y (quality indicator) over the rounds
            #
            num_y = np.size(workspace.display_data.y_values)

            x_values_axis = np.arange(1, num_y+1)

            figure.subplot_scatter(0, 0,
                                   x_values_axis, workspace.display_data.y_values,
                                   xlabel="Iteration", ylabel="Quality", title="Quality over iterations")

            #
            # prepare second plot showing a table with old and new values
            #
            figure.subplot_table(0, 1,
                                 workspace.display_data.statistics,
                                 col_labels=workspace.display_data.col_labels)

        #
        # information plotted when BO was not run
        #
        else:
            figure.set_subplots((1, 1))
            figure.set_subplot_title("No Optimisation", 0, 0)

    #
    # helper function:
    # Return a list of pipeline modules (only IdentifyObjects modules)
    #
    def get_module_list(self, pipeline):
        modules = pipeline.modules()
        module_list = []
        for module in modules:
            if "Identify" in module.module_name:
                module_list.append("{} #{}".format(module.module_name, module.get_module_num()))
        return module_list

    #
    # helper function:
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
                    setting_text = setting.get_text()
                    if setting_text not in setting_list:
                        setting_list.append(setting_text)

        return setting_list

    #
    # helper function:
    # Necessary to refresh the dropdown menus in GUI
    #
    def refreshGUI(self):
        print("GUI refreshed")

    #
    # helper function:
    # Deletes existing files storing previous values for x and y
    #
    def delete_data(self):
        x_filename = "x_bo_{}.txt".format(self.get_module_num())
        y_filename = "y_bo_{}.txt".format(self.get_module_num())

        os.remove(x_filename)
        os.remove(y_filename)

        print("Data deleted")

    # def reset_module_counter(self, pipelinelistview):
    #     pipelinelistview.set_current_debug_module()

    # def reset_debug(self, pipelinecontroller):
    #     pipelinecontroller.on_debug_continue()

    #######################################################################
    # Actual Bayesian optimisation functionality (from Bjørn Sand Jensen) #
    #######################################################################

    def bayesian_optimisation(self, manual_result, auto_evaulation_results,
                              values_list, setting_range, range_steps, max_iter):
        #
        # need to load and write available data to files to persist it over the iterations; files contain x and y values
        # define the name of the files where x and y values are written to; names store the module number in case
        # BO module is used in more than one place of the pipeline
        #
        x_filename = "x_bo_{}.txt".format(self.get_module_num())
        y_filename = "y_bo_{}.txt".format(self.get_module_num())

        #
        # open or create x_file and write the values of the setting parameters to it
        #
        with open(x_filename, "a+") as x_file:
            for v in values_list:
                x_file.write("{} ".format(v))
            x_file.write("\n")

        #
        # open or create y_file and write the values of the evaluation measurements to it
        # normalise y before writing it to the file
        #
        with open(y_filename, "a+") as y_file:
            y_normalised = self.normalise_y(manual_result, auto_evaulation_results)
            y_file.write("{}\n".format(y_normalised))

        #
        # load the x and y values into numpy arrays
        # x values are the settings values
        # y values are the percentaged evaluation deviation values normalised and weighted to one single y value
        #
        x = np.loadtxt(x_filename)
        y = np.loadtxt(y_filename)

        #
        # initialise the kernel (covariance function) for the BO model
        #
        kernel_init = gp.kernels.ConstantKernel(0.1) * gp.kernels.RBF(length_scale=0.1)

        #
        # Set up the actual iterative optimisation loop
        #
        n_offset_bayesopt = 2       # min number of data points to start BO
        n_max_iter = int(max_iter)
        n_current_iter = len(np.atleast_1d(y))  # number of data available

        # TODO set the random number generator to a known state --> not a good idea? will always choose same set and so
        # np.random.seed(2 * 345 + 10)

        ########################################################################
        # create a suitable candidate set matrix based on the user input       #
        # take into account the range and steps a settings should be varied in #
        ########################################################################

        #
        # find out dimensions of x (num_cols)
        #
        try:
            num_cols = x.shape[1]
        except IndexError:
            num_cols = x.shape[0]

        #
        # create a 1D candidate set for each x dimension in the range and with the range steps given by user
        #
        candidate_arrays = []
        for i in range(0, num_cols):
            a = float(setting_range[i][0])
            b = float(setting_range[i][1])
            c = float(range_steps[i])

            candidate = np.arange(a, b, c)
            candidate_arrays += [candidate]

        print("CANDIDATE 1D ARRAYS:")
        print(candidate_arrays)
        print("-" * 50)

        # TODO: building the matrix assumes 2 -4 params; how can I make it more flexible?
        # Is there another way to create the matrix I need?

        #
        # create a matrix for either 2, 3 or 4 parameters with all possible combinations of the 1D-arrays
        #
        if num_cols == 2:
            c = list(product(candidate_arrays[0], candidate_arrays[1]))
        elif num_cols == 3:
            c = list(product(candidate_arrays[0], candidate_arrays[1], candidate_arrays[2]))
        else:
            c = list(product(candidate_arrays[0], candidate_arrays[1], candidate_arrays[2], candidate_arrays[3]))

        unstandardised_candidates_array = np.asanyarray(c)

        print("CANDIDATE MATRIX BEFORE STANDARDISATION:")
        print(unstandardised_candidates_array)
        print("-" * 50)

        #
        # correction of numbers in array: standardisation of matrix entries; important step in Machine Learning
        #

        # 1st step: get mean from each column in matrix
        mean_candidates = np.mean(unstandardised_candidates_array, axis=0)

        # 2nd step: subtract mean from matrix
        cand_1 = unstandardised_candidates_array - mean_candidates

        # 3rd step: calculate standard deviation per column
        st_dev_candidates = np.std(cand_1, axis=0)

        # 4th step: calculate the standardised candidates matrix
        standardised_candidates = cand_1 / st_dev_candidates

        #
        # check how many entries (rows) the matrix has
        #
        num_entries = np.size(standardised_candidates, axis=0)

        print("MATRIX SIZE")
        print(num_entries)
        print("-" * 50)

        #
        # if candidate matrix is too large, take a subset of 10000 randomly chosen entries;
        # this ensures that the matrix has <= 10.000 row entries
        #
        if num_entries > 10000:
            np.take(standardised_candidates, np.random.permutation(standardised_candidates.shape[0]),
                    axis=0, out=standardised_candidates)
            standardised_candidates = standardised_candidates[:10000]

        candidates_bayesopt = deepcopy(standardised_candidates)

        #
        # Init the data for the bayes opt procedure; we need to standardise the current x value set as well!
        #
        x_1 = x - mean_candidates
        standardised_x = x_1 / st_dev_candidates

        x_active_bayesopt = standardised_x

        print("x_active_bayesopt:")
        print(x_active_bayesopt)

        y_active_bayesopt = y

        # #### DOES NOT WORK YET!!!! ######
        #
        # remove the active x from the candidate set
        #
        # candidates_bayesopt = np.setdiff1d(candidates, x) # TODO how do I remove it form 2D?

        #
        # Run the procedure once and then return the new best x when no. of iterations is < than max_iter
        #
        if n_current_iter <= n_max_iter:
            print(" Iter: " + str(n_current_iter))

            #
            # Update Bayes opt active set with one point selected via EI
            # (of we have exceeded the initial offset period)
            #
            if n_current_iter > n_offset_bayesopt:

                ###################################
                # Bayesian Optimisation Procedure #
                ###################################

                print("EXECUTING BAYESIAN OPTIMISATION PROCEDURE")

                #
                # Define and fit the GP model (using the kernel_bayesopt_init parameters)
                #
                model_bayesopt = gp.GaussianProcessRegressor(kernel=deepcopy(kernel_init),
                                                             alpha=0.01, # 0.01; i.e. assume low noise level on the user
                                                             n_restarts_optimizer=5,
                                                             optimizer=None,
                                                             normalize_y=True, )

                #
                # fit model with available active x and y parameters
                #
                model_bayesopt.fit(x_active_bayesopt, y_active_bayesopt)

                #
                # Find the currently best value (based on the model, not the active data itself as there could be
                # a tiny difference)
                #
                mu_active_bayesopt, sigma_active_bayesopt = model_bayesopt.predict(x_active_bayesopt,
                                                                                   return_std=True)
                ind_loss_optimum = np.argmin(mu_active_bayesopt)
                mu_min_active_bayesopt = mu_active_bayesopt[ind_loss_optimum]

                #
                # Predict the values for all the possible candidates in the candidate set using the fitted
                # model_bayesopt
                #
                mu_candidates, sigma_candidates = model_bayesopt.predict(candidates_bayesopt, return_std=True)

                #
                # Compute the expected improvement for all the candidates
                #
                z = (mu_min_active_bayesopt - mu_candidates) / sigma_candidates
                ei = (mu_min_active_bayesopt - mu_candidates) * norm.cdf(z) + sigma_candidates * norm.pdf(z)
                ei[sigma_candidates == 0.0] = 0.0   # Make sure to account for the case where sigma==0 to avoid
                # numerical issues (would be NaN otherwise)

                #
                # Find the candidate with the largest expected improvement... and choose that one to query/include
                #
                eimax = np.max(ei)  # maximum expected improvement
                iii = np.argwhere(eimax == ei)  # find all points with the same maximum value of ei in case there
                # are more than one (often the case in the beginning)
                iiii = np.random.randint(np.size(iii, axis=0), size=1)  # ... and choose randomly among them
                ind_new_candidate_as_index_in_cand_set = [iii[iiii[0]]]

                #
                # get the new suggested x from the candidates
                #
                new_x_standardised = candidates_bayesopt[ind_new_candidate_as_index_in_cand_set]

            #
            # Skip bayes opt until we reach n_offset_bayesopt and select random points for inclusion
            # (sometimes it is a good idea to include a few random examples)
            #
            else:
                print("RANDOMLY choosing as not enough data is available")

                ii = np.random.randint(np.size(candidates_bayesopt, axis=0), size=1)

                new_x_standardised = candidates_bayesopt[ii]

            ###################
            # Return X values #
            ###################

            #
            # now that new setting values X form the candidate set were chosen, they first need to be converted back
            # by de-standardising them with the standard deviation and mean we have calculated earlier
            #

            next_x_meaned = new_x_standardised * st_dev_candidates
            next_x = next_x_meaned + mean_candidates

            #
            # return the X values to adjust the settings and getting a new y value from the user for next BO round
            #

            print("NEW SETTINGS:")
            print(next_x)

            return next_x, y

        #
        # If the max number of iterations is reached, stop B.O.; indicating it with returning 0 and 0 instead of arrays
        #
        else:
            return None, None

    #
    # helper function to normalise the manual and auto evaluation results and return a weighted normalised value for y
    #
    def normalise_y(self, manual_result, auto_evaluation_results):

        if len(manual_result) == 0:
            print("1 called")
            auto = auto_evaluation_results

            result_accumulated = float(np.sum(auto)) / np.size(auto)

            result_norm = float(result_accumulated / 100)

            print(result_accumulated)
            print(result_norm)

        elif len(auto_evaluation_results) == 0:
            print("2 called")
            result_norm = float(manual_result) / 100

            print(result_norm)

        else:
            print("3 called")
            manual = 0.5 * manual_result
            auto = 0.5 * auto_evaluation_results

            result_accumulated = float(np.sum(manual) + np.sum(auto) / np.size(auto))

            result_norm = float(result_accumulated / 100)

            print(result_accumulated)
            print(result_norm)

        return result_norm

        # results = np.concatenate([manual_result, auto_evaluation_results])
        # print("Results:")
        # print(results)
        #
        # norm_results = np.linalg.norm(results)
        #
        # if norm_results == 0:
        #     n_new = results
        # else:
        #     n_new = results / norm_results
        #
        # mean_y = np.mean(n_new)
        #
        # print(n_new)
        # print(mean_y)
        #
        # return mean_y



