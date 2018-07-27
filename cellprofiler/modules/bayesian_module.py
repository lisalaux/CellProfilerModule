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
BayesianOptimisation
===================

**BayesianOptimisation** uses Bayesian Optimisation methods on parameters (settings) chosen from modules placed before 
this module in the pipeline. It needs either a ManualEvaluation or AutomatedEvaluation or both modules placed beforehand 
in the pipeline. It can only evaluate and operate on the quality of one object at a time. 

The Bayesian Optimisation will only be executed if required quality thresholds/ranges defined in the evaluation 
module(s) are not met.

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          YES           NO
============ ============ ===============

"""


class BayesianOptimisation(cellprofiler.module.Module):
    module_name = "BayesianOptimisation"
    category = "Advanced"
    variable_revision_number = 1

    #######################################################################
    # Create and set CellProfiler settings for GUI and Pipeline execution #
    #######################################################################

    def create_settings(self):
        module_explanation = [
            "This module uses BayesianOptimisation on parameters (settings) chosen from modules placed before this "
            "module in the pipeline. Step 1: Choose the objects which you have evaluated in the evaluation modules. "
            "The Bayesian module should consider these measures as quality indicators. Step 2: Choose the parameters "
            "(settings) to be adjusted. Bayesian Optimisation will be executed if required quality thresholds/ranges "
            "are not met. The chosen modules with corresponding settings need to be in order! (first module appearing"
            "in the pipeline needs to be chosen first)"]

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

    #
    # add the quality measurements which should be considered by B.O.
    # add a remove-button for all measurements except a mandatory one
    #
    def add_measurement(self, can_delete=True):
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

    #
    # add parameters grouped with corresponding modules
    # add a remove-button for all parameters except a mandatory one
    #
    def add_parameter(self, can_remove=True):

        group = cellprofiler.setting.SettingsGroup()

        if can_remove:
            group.append("divider", cellprofiler.setting.Divider(line=False))

        group.append("module_names", cellprofiler.setting.Choice(
            "Select module",
            choices=[""],
            choices_fn=self.get_module_list,
            doc="""\
This is the module where Bayesian Optimisation will adjust settings
"""
        ))

        group.append("parameter_names", cellprofiler.setting.Choice(
            "Select parameter",
            choices=[""],
            choices_fn=self.get_settings_from_modules,
            doc="""\
These are the settings to be adjusted by Bayesian Optimisation
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
                        print("Manual evaluation causes opt_on")

            elif m.evaluation_measurement.value_text == "Evaluation_Deviation":
                auto_evaluation_results = workspace_measurements.get_current_measurement(
                    self.input_object_name.value, m.evaluation_measurement.value_text)
                for e in auto_evaluation_results:
                    if float(e) > 0.0:
                        self.optimisation_on = True
                        print("Auto evaluation causes opt_on")

        print("Bayesian Evaluation Results list: ")
        print("Manual: ")
        print(manual_evaluation_result)
        print("Auto: ")
        print(auto_evaluation_results)

        if self.optimisation_on: # may need to change this??? because it would not run BO then for last time
            #
            # get modules and their settings
            #
            number_of_params = self.parameters.__len__()
            print("Number of params: {}".format(number_of_params))

            target_setting_module_list = []     # saves module objects
            target_setting_names_list = []      # saves setting names
            target_setting_values_list = []     # saves setting values of the selected settings in the module
            # the three lists operate with indices; an indices corresponds to a certain module, a setting name in
            # this module and the value of this setting

            for module in self.parameters:
                name_list = module.module_names.value_text.split(" #")
                number = int(name_list[1])
                target_module = pipeline.module(number)

                print(target_module.module_name)
                target_setting_module_list += [number]

                target_setting_name = module.parameter_names.value_text

                for setting in target_module.settings():
                    if setting.get_text() == target_setting_name:
                        print("Setting name: "+setting.get_text())
                        target_setting_names_list += [setting.get_text()]
                        print("Old setting value: "+str(setting.get_value()))
                        target_setting_values_list += [setting.get_value()]

            #
            # do the bayesian optimisation with a new function that takes the 3 lists and alters the values_list
            #
            new_target_settings_array = self.bayesian_optimisation(manual_evaluation_result, auto_evaluation_results,
                                                             target_setting_values_list)

            new_target_settings = new_target_settings_array.flatten()


            print("NEW SETTINGS AFTER BO:")
            print(new_target_settings)

            print("first index:")
            print(new_target_settings[0])
            #if new_target_settings == 0:
                # bo is finished

            # elif new_target_settings != 0:
                # bo is not finished

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
                        print("New setting value: "+str(setting.get_value()))

            # pipeline re-runs automatically from where module has been changed; modules therefore need to be in order!
            # problem: pipeline runs only so many times as it has modules in total
            # --> need to find a way to re-set count
            # start_module = pipeline.module(5)

            # sth with debug-mode on if-statement
            #workspace.set_module(start_module)
            #workspace.set_disposition(cellprofiler.workspace.DISPOSITION_CONTINUE)

            # does not work with gui
            #pipelist = cellprofiler.gui.pipelinelistview.PipelineListView()
            #cellprofiler.gui.pipelinelistview.PipelineListView.set_current_debug_module(pipelist, start_module)




            #
            # if user wants to show the display-window, save data needed for display in workspace.display_data
            #
            if self.show_window:
                # also show quality measures before???
                workspace.display_data.statistics = []
                for i in range(number_of_params):
                    workspace.display_data.statistics.append(
                        (target_setting_names_list[i], target_setting_values_list[i], new_target_settings[i]))

                workspace.display_data.col_labels = ("Setting Name", "Old Value", "New Value")

        else:
            print("no optimisation")

    #
    # if user wants to show the display window during pipeline execution, this method is called by UI thread
    # display the data saved in display_data of workspace
    # used a CP defined figure to plot/display data via matplotlib
    #
    def display(self, workspace, figure):
        if self.optimisation_on:
            figure.set_subplots((1, 1))
            figure.subplot_table(0, 0,
                                 workspace.display_data.statistics,
                                 col_labels=workspace.display_data.col_labels)

        # do sth when optimisation was not needed?

    #
    # Return a list of all pipeline modules
    #
    def get_module_list(self, pipeline):
        modules = pipeline.modules()
        module_list = []
        for module in modules:
            if "Identify" in module.module_name:
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
                    setting_text = setting.get_text()
                    if setting_text not in setting_list:
                        setting_list.append(setting_text)

        return setting_list

    #
    # Necessary to refresh the dropdown menus in GUI
    #
    def refreshGUI(self):
        print("GUI refreshed")

    # def reset_module_counter(self, pipelinelistview):
    #     pipelinelistview.set_current_debug_module()

    def reset_debug(self, pipelinecontroller):
        pipelinecontroller.on_debug_continue()

    #
    # Apply bayesian optimisation to adjust settings for next pipeline run
    #
    # def bayesian_optimisation_1(self, manual_result, auto_evaulation_results, module_list, names_list, values_list):
    #     # do the optimisation and return new values in values_list
    #     print("Old value in BO def: ")
    #     print(values_list[0])
    #
    #     new_values = list(values_list)
    #     # new_values[0] = "Two classes"   # Two or three class thresholding
    #     # new_values[1] = "300"           # Size of adaptive window
    #     new_values[0] = "4"             # Threshold smoothing scale
    #     new_values[1] = "1.2"           # Threshold correction factor
    #
    #     return new_values

    #######################################################################
    # Actual Bayesian optimisation functionality (from Bjørn Sand Jensen) #
    #######################################################################

    def bayesian_optimisation(self, manual_result, auto_evaulation_results, values_list):
        # need to load and write available data to a file to persist it; files contain x and y values
        # TODO for how many parameters is this working? for approx. 8-10 max

        # define the name of the files where x and y values are written to to persist them over the iterations
        x_filename = "x_bo_{}.txt".format(self.get_module_num())
        y_filename = "y_bo_{}.txt".format(self.get_module_num())

        # open or create x_file and write the values of the setting parameters to it
        # TODO the x values need to be normalised as well! (to range 0-1; no discrete values possible at the moment)
        # TODO DO NOT FORGET TO DELETE FILE AFTER BO COMPLETED or should values be persisted??? or is it better to
        # TODO persist the model with pickle (not necessary)
        with open(x_filename, "a+") as x_file:
            for v in values_list:
                x_file.write("{} ".format(v))
            x_file.write("\n")

        # open or create y_file and write the values of the evaluation measurements to it
        with open(y_filename, "a+") as y_file:
            y_normalised = self.normalise_y(manual_result, auto_evaulation_results)
            y_file.write("{}\n".format(y_normalised))

        # load the x and y values into numpy arrays
        # x values are the settings values
        # y values are the evaluation deviation values normalised and averaged to one single y value
        x_raw = np.loadtxt(x_filename)

        print("x_raw:")
        print(x_raw)

        # normalise x values
        x = self.normalise_x(x_raw)

        y = np.loadtxt(y_filename)

        print("y:")
        print(y)

        # initialise the kernel (covariance function9 for the BO model
        # TODO do come up with a "good parameter" for the length_scale, probably 1?
        #
        kernel_init = gp.kernels.ConstantKernel(0.1) * gp.kernels.RBF(length_scale=0.1)  # find suitable length_scale

        # ## Set up the actual iterative optimisation loop
        n_offset_bayesopt = 2
        n_max_iter = 15         # TODO the demo has shown that the BO can optimise in around 15-20 iterations
        n_current_iter = len(np.atleast_1d(y)) # get the number of data available
        y_best_bayesopt = np.zeros(n_max_iter)
        y_best_rnd = np.zeros(n_max_iter)

        # set the random number generator to a known state
        np.random.seed(2 * 345 + 10)

        # The candidates we can choose to query next is the available data in the current dataset
        # ... but it would typically be the full range of values of a parameter in a grid, e.g. [0, 0.1,0.2,0.3,.,1]
        # for CellProfiler, the setting can have a certain value range and it must be chosen out of this
        # When x is normalised, it's between 0 and 1

        # build 2D array with all possible combinations of the candidates
        candidates_1D = np.arange(0, 1.001, 0.001)

        try:
            num_cols = x.shape[1]
        except IndexError:
            num_cols = x.shape[0]

        # assumes 2 or 3 params; PC crashes with 3 params :/
        if num_cols == 2:
            c = list(product(candidates_1D, candidates_1D))
        else:
            c = list(product(candidates_1D, candidates_1D, candidates_1D))

        candidates_bayesopt = np.asanyarray(c)

        # Init the data for the bayes opt procedure by choosing the last entry of x
        x_active_bayesopt = x
        print("x_active_bayesopt:")
        print(x_active_bayesopt)
        y_active_bayesopt = y

        # is this correct to remove all x from the candidates?
        # candidates_bayesopt = np.setdiff1d(candidates, x) # TODO how do I remove it form 2D?
        # Init the data for the random acquisition function by choosing the same random point as for bayes opt
        x_active_rnd = deepcopy(x_active_bayesopt)
        candidates_rnd = deepcopy(candidates_bayesopt)


        # Run the procedure once and then return the new best x when no. of iterations is < than max_iter
        if n_current_iter < n_max_iter: # OR when y already 0?
            print(" Iter: " + str(n_current_iter))

            # Update Bayes opt active set with one point selected via EI
            # (of we have exceeded the initial offset period) TODO meaning we need at least two values?
            if n_current_iter > n_offset_bayesopt:
                print("DOING BO NOW as enough data is available")

                ###################################
                # Bayesian Optimisation Procedure #
                ###################################
                # Define and fit the GP model from scratch (using the kernel_bayesopt_init parameters)
                model_bayesopt = gp.GaussianProcessRegressor(kernel=deepcopy(kernel_init),
                                                             alpha=0.01,
                                                             # alpha = 0.01; i.e. assume low noise level on the user
                                                             # feedback, this should be set in a better way
                                                             n_restarts_optimizer=5,
                                                             optimizer=None,
                                                             normalize_y=True, )
                # fit model with available parameters
                model_bayesopt.fit(x_active_bayesopt, y_active_bayesopt)

                # Find the currently best value (based on the model, not the active data itself as there could be
                # a tiny difference)
                mu_active_bayesopt, sigma_active_bayesopt = model_bayesopt.predict(x_active_bayesopt,
                                                                                   return_std=True)
                ind_loss_optimum = np.argmin(mu_active_bayesopt)
                mu_min_active_bayesopt = mu_active_bayesopt[ind_loss_optimum]

                # Predict the values for all the possible candidates in the candidate set using the fitted
                # model_bayesopt
                mu_candidates, sigma_candidates = model_bayesopt.predict(candidates_bayesopt, return_std=True)

                # Compute the expected improvement for all the candidates
                Z = (mu_min_active_bayesopt - mu_candidates) / sigma_candidates
                ei = (mu_min_active_bayesopt - mu_candidates) * norm.cdf(Z) + sigma_candidates * norm.pdf(Z)
                ei[sigma_candidates == 0.0] = 0.0  # Make sure to account for the case where sigma==0 to avoid
                # numerical issues (would be NaN otherwise)

                # Find the candidate with the largest expected improvement... and choose that one to query/include
                eimax = np.max(ei)  # maximum expected improvement
                iii = np.argwhere(eimax == ei)  # find all points with the same maximum value of ei in case there
                # are more than one (often the case in the beginning)
                iiii = np.random.randint(np.size(iii, axis=0), size=1)  # ... and choose randomly among them
                ind_new_candidate_as_index_in_cand_set = [iii[iiii[0]]]

                # Update the indices of the active and candidate set based on the new chosen observation
                # Note: normally this would involve actually getting the value y from the user and concatenating
                # the dataset, but since we have a existing dataset we simple work with indices and pick out the y
                # from the candidate set
                # TODO what do I need to change here?

                print("THIS WAS RUN")

                x_active_bayesopt = candidates_bayesopt[ind_new_candidate_as_index_in_cand_set]

            else:
                # Skip bayes opt until we reach n_offset_bayesopt and select random points for inclusion
                # (sometimes it is a good idea to include a few random examples)
                # TODO means for CP that pipeline is run again with random x setting value!!!

                print("RANDOMLY choosing as not enough data is available")

                ii = np.random.randint(np.size(candidates_bayesopt, axis=0), size=1)

                x_active_bayesopt = candidates_bayesopt[ii]

            ####################
            # Get the y values #
            ####################
            # TODO for CP, this would mean we need to run the pipeline with the new x settings parameters!!
            # TODO does that mean I break out of the loop now and return the new settings (x) values?
            # TODO THIS IS WHERE I NEED TO GET Y!! Re-Run pipeline
            # TODO probably save the state of the model object with pickle?
            # TODO HOW can I re-run the pipeline in the middle of my optimisation loop anyways?
            # first get the actual x values
            x_new_normalised = x_active_bayesopt
            x_norm = np.linalg.norm(x_raw)
            x_denorm = x_new_normalised * x_norm
            x_new_rounded = np.around(x_denorm, decimals=3)

            # what to do about the random??? I cannot get both!!!!
            print("NEW SETTINGS BEFORE RETURN:")
            print(x_new_rounded)

            return x_new_rounded

            # problem: am I now writing the x values to the file 2 times? no don't think so, I don't write thm here

            # ... iterate until n_max_iter

        ##############
        # Last round #
        ##############
        # TODO needs adjustment!!!!!!! only operates on the gathered data (with indeces)
        # include the random version to show the difference
        elif n_current_iter == n_max_iter:

            for n_it in range(0, n_max_iter):
                # ## Define the current dataset from indices (the active set, i.e. the observations so far)
                x_active_rnd = x_active_bayesopt
                y_active_rnd = y_active_bayesopt

                # The candidate set of parameter settings, i.e. the x values we can possibly query if we choose to do so
                # TODO for CP this would typically be a large grid of feasible parameter settings values
                x_candidates_rnd = candidates_bayesopt

                ###################################
                # Bayesian Optimisation Procedure #
                ###################################
                # Define and fit the GP model from scratch (using the kernel_bayesopt_init parameters)
                model_bayesopt = gp.GaussianProcessRegressor(kernel=deepcopy(kernel_init),
                                                             alpha=0.01,
                                                             # alpha = 0.01; i.e. assume low noise level on the user
                                                             # feedback, this should be set in a better way
                                                             n_restarts_optimizer=5,
                                                             optimizer=None,
                                                             normalize_y=True, )
                # fit model with available parameters
                model_bayesopt.fit(x_active_bayesopt, y_active_bayesopt)

                # Update Bayes opt active set with one point selected via EI
                # (of we have exceeded the initial offset period) TODO meaning we need at least two values?

                # Find the currently best value (based on the model, not the active data itself as there could be
                # a tiny difference)
                mu_active_bayesopt, sigma_active_bayesopt = model_bayesopt.predict(x_active_bayesopt,
                                                                                   return_std=True)
                ind_loss_optimum = np.argmin(mu_active_bayesopt)
                mu_min_active_bayesopt = mu_active_bayesopt[ind_loss_optimum]

                # Predict the values for all the possible candidates in the candidate set using the fitted
                # model_bayesopt
                mu_candidates, sigma_candidates = model_bayesopt.predict(candidates_bayesopt, return_std=True)

                # Compute the expected improvement for all the candidates
                Z = (mu_min_active_bayesopt - mu_candidates) / sigma_candidates
                ei = (mu_min_active_bayesopt - mu_candidates) * norm.cdf(Z) + sigma_candidates * norm.pdf(Z)
                ei[sigma_candidates == 0.0] = 0.0  # Make sure to account for the case where sigma==0 to avoid
                # numerical issues (would be NaN otherwise)

                # Find the candidate with the largest expected improvement... and choose that one to query/include
                eimax = np.max(ei)  # maximum expected improvement # TODO do I need to change this to min?
                iii = np.argwhere(eimax == ei)  # find all points with the same maximum value of ei in case there
                # are more than one (often the case in the beginning)
                iiii = np.random.randint(np.size(iii, axis=0), size=1)  # ... and choose randomly among them
                ind_new_candidate_as_index_in_cand_set = [iii[iiii[0]]]

                # Update the indices of the active and candidate set based on the new chosen observation
                # Note: normally this would involve actually getting the value y from the user and concatenating
                # the dataset, but since we have a existing dataset we simple work with indices and pick out the y
                # from the candidate set
                # TODO what do I need to change here?

                x_active_bayesopt = np.union1d(x_active_bayesopt,
                                                 candidates_bayesopt[ind_new_candidate_as_index_in_cand_set])
                candidates_bayesopt = np.setdiff1d(candidates_bayesopt,
                                                       candidates_bayesopt[
                                                           ind_new_candidate_as_index_in_cand_set])

                #####################################
                # Random Procedure (for comparison) #
                #####################################
                # ##################### Random procedure, i.e. choose points randomly to be included
                # Update random active set with a randomly chosen x
                ii = np.random.randint(np.size(candidates_rnd, axis=0), size=1)
                x_active_rnd = np.union1d(x_active_rnd, candidates_rnd[ii])
                candidates_rnd = np.setdiff1d(candidates_rnd, candidates_rnd[ii])
                # TODO what does the following mean?
                # actually we should fit a model, model_rnd, here based on the ind_active_rnd set and select the best
                # candidate based on the model...but will give roughly the same results as just picking the max among
                # the included data

                y_best_bayesopt[n_it] = np.min(y[x_active_bayesopt])
                y_best_rnd[n_it] = np.min(y[x_active_rnd])

            ###############################################
            # Analyse results and compute some statistics #
            ###############################################
            # Compute the average best value across the repetitions
            ybest_bayesopt_avg = np.mean(y_best_bayesopt, axis=0)
            ybest_bayesopt_std = np.std(y_best_bayesopt, axis=0) / 2
            ybest_rnd_avg = np.mean(y_best_rnd, axis=0)
            ybest_rnd_std = np.std(ybest_rnd_avg, axis=0) / 2
            ybestOverall = np.min(y)

            # Visualise the convergence of the bayesopt procedure vs the random one in their quest to reach the best
            # possible value in the available set
            # TODO for CellProfiler, visualisation should only be done after Bo hast completely finished?
            plt.plot([0, n_max_iter], [ybestOverall, ybestOverall], "k-", label="Target")
            plt.errorbar(range(np.size(ybest_bayesopt_avg)), ybest_bayesopt_avg, yerr=ybest_bayesopt_std,
                         label="Average BO run  +/- std/2 ")
            plt.errorbar(range(np.size(ybest_rnd_avg)), ybest_rnd_avg, yerr=ybest_rnd_std,
                         label="Average Rnd run +/- std/2")
            plt.legend()
            plt.xlabel("iterations")
            plt.ylabel("identified max value")
            plt.title("convergence")
            plt.show()

            return 0 # what can I return instead to indicate BO is finished??

    #
    # helper function to normalise the manual and auto evaluation results and return a normalised mean value for y
    #
    def normalise_y(self, manual_result, auto_evaulation_results):
        results = np.concatenate([manual_result, auto_evaulation_results])
        norm_results = np.linalg.norm(results)

        if norm_results == 0:
            n_new = results
        else:
            n_new = results / norm_results

        mean_y = np.mean(n_new)

        print(n_new)
        print(mean_y)

        return mean_y

    #
    # helper function to normalise the values of the x array
    #
    def normalise_x(self, x_raw):
        x_norm = np.linalg.norm(x_raw) # can be used to re-transform the values back to normal later
        if x_norm == 0:
            x = x_raw
        else:
            x = x_raw / x_norm

        x_round = np.around(x, decimals=3)

        return x_round



