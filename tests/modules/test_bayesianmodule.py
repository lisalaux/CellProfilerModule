import unittest
import numpy as np

import cellprofiler.pipeline
from cellprofiler.modules import instantiate_module

#
# Constants
#
INPUT_OBJECT_NAME = "UnfilteredNuclei"
AUTO_MEASUREMENT = "Evaluation_Deviation"
MANUAL_MEASUREMENT = "Evaluation_ManualQuality"
MODULE_NAME1 = "IdentifyPrimaryObjects"
MODULE_NAME2 = "Smooth"
PARAM_NAME1 = "Size of adaptive window"
PARAM_NAME2 = "Size of smoothing filter"


class TestBayesianOptimisation(unittest.TestCase):
    '''SetUp'''
    def make_instance(self):
        '''Return an instance of of the module'''
        return instantiate_module("BayesianOptimisation")

    '''Test if instance is created'''
    def test_01_can_load(self):
        self.assertFalse(self.make_instance() is None)

    '''Test if settings values are created correctly'''
    def test_02_create_settings(self):
        module = self.make_instance()

        module.input_object_name.value = INPUT_OBJECT_NAME
        module.count1.value = 2
        module.count2.value = 2
        module.weighting_manual.value = 50
        module.weighting_auto.value = 50
        module.measurements[0].evaluation_measurement.value = AUTO_MEASUREMENT
        module.add_measurement()
        module.measurements[1].evaluation_measurement.value = MANUAL_MEASUREMENT
        module.max_iter.value = 150
        module.length_scale.value = 0.1
        module.alpha.value = 0.01
        module.parameters[0].module_names.value = MODULE_NAME1
        module.parameters[0].parameter_names.value = PARAM_NAME1
        module.parameters[0].range.value = (10, 500)
        module.parameters[0].steps = 10
        module.add_parameter()
        module.parameters[1].module_names.value = MODULE_NAME2
        module.parameters[1].parameter_names.value = PARAM_NAME2
        module.parameters[1].range.value = (0.1, 10.5)
        module.parameters[1].steps = 0.1

        self.assertEqual(module.input_object_name.value, INPUT_OBJECT_NAME)
        self.assertEqual(module.count1.value, 2)
        self.assertEqual(module.count2.value, 2)
        self.assertEqual(module.weighting_manual.value, 50)
        self.assertEqual(module.weighting_auto.value, 50)
        self.assertEqual(module.measurements[0].evaluation_measurement.value, AUTO_MEASUREMENT)
        self.assertEqual(module.measurements[1].evaluation_measurement.value, MANUAL_MEASUREMENT)
        self.assertEqual(module.max_iter.value, 150)
        self.assertEqual(module.length_scale.value, 0.1)
        self.assertEqual(module.alpha.value, 0.01)
        self.assertEqual(module.parameters[0].module_names.value, MODULE_NAME1)
        self.assertEqual(module.parameters[0].parameter_names.value, PARAM_NAME1)
        self.assertEqual(module.parameters[0].range.value, (10, 500))
        self.assertEqual(module.parameters[0].steps, 10)
        self.assertEqual(module.parameters[1].module_names.value, MODULE_NAME2)
        self.assertEqual(module.parameters[1].parameter_names.value, PARAM_NAME2)
        self.assertEqual(module.parameters[1].range.value, (0.1, 10.5))
        self.assertEqual(module.parameters[1].steps, 0.1)

    '''Test if settings are created'''
    def test_03_settings(self):
        module = self.make_instance()

        module.input_object_name.value = INPUT_OBJECT_NAME
        module.count1.value = 2
        module.count2.value = 2
        module.weighting_manual.value = 50
        module.weighting_auto.value = 50
        module.measurements[0].evaluation_measurement.value = AUTO_MEASUREMENT
        module.add_measurement()
        module.measurements[1].evaluation_measurement.value = MANUAL_MEASUREMENT
        module.max_iter.value = 150
        module.length_scale.value = 0.1
        module.alpha.value = 0.01
        module.parameters[0].module_names.value = MODULE_NAME1
        module.parameters[0].parameter_names.value = PARAM_NAME1
        module.parameters[0].range.value = (10, 500)
        module.parameters[0].steps = 10
        module.add_parameter()
        module.parameters[1].module_names.value = MODULE_NAME2
        module.parameters[1].parameter_names.value = PARAM_NAME2
        module.parameters[1].range.value = (0.1, 10.5)
        module.parameters[1].steps = 0.1

        settings = module.settings()

        self.assertEqual(len(settings), 19)
        self.assertEqual(id(module.input_object_name), id(settings[0]))
        self.assertEqual(id(module.count1), id(settings[1]))
        self.assertEqual(id(module.count2), id(settings[2]))
        self.assertEqual(id(module.weighting_manual), id(settings[3]))
        self.assertEqual(id(module.weighting_auto), id(settings[4]))
        self.assertEqual(id(module.measurements[0].evaluation_measurement), id(settings[5]))
        self.assertEqual(id(module.measurements[1].evaluation_measurement), id(settings[6]))
        self.assertEqual(id(module.max_iter), id(settings[7]))
        self.assertEqual(id(module.length_scale), id(settings[8]))
        self.assertEqual(id(module.alpha), id(settings[9]))
        self.assertEqual(id(module.parameters[0].module_names), id(settings[10]))
        self.assertEqual(id(module.parameters[0].parameter_names), id(settings[11]))
        self.assertEqual(id(module.parameters[0].range), id(settings[12]))
        self.assertEqual(id(module.parameters[0].steps), id(settings[13]))
        self.assertEqual(id(module.parameters[1].module_names), id(settings[14]))
        self.assertEqual(id(module.parameters[1].parameter_names), id(settings[15]))
        self.assertEqual(id(module.parameters[1].range), id(settings[16]))
        self.assertEqual(id(module.parameters[1].steps), id(settings[17]))

    '''Test normalisation of y'''
    def test_04_normalise_y(self):
        module = self.make_instance()

        module.input_object_name.value = INPUT_OBJECT_NAME
        module.count1.value = 2
        module.count2.value = 2
        module.weighting_manual.value = 50
        module.weighting_auto.value = 50
        module.measurements[0].evaluation_measurement.value = AUTO_MEASUREMENT
        module.add_measurement()
        module.measurements[1].evaluation_measurement.value = MANUAL_MEASUREMENT
        module.max_iter.value = 150
        module.length_scale.value = 0.1
        module.alpha.value = 0.01
        module.parameters[0].module_names.value = MODULE_NAME1
        module.parameters[0].parameter_names.value = PARAM_NAME1
        module.parameters[0].range.value = (10, 500)
        module.parameters[0].steps = 10
        module.add_parameter()
        module.parameters[1].module_names.value = MODULE_NAME2
        module.parameters[1].parameter_names.value = PARAM_NAME2
        module.parameters[1].range.value = (0.1, 10.5)
        module.parameters[1].steps = 0.1

        manual_result1 = np.array([20])
        auto_evaluation_result1 = np.array([30, 0.0, 5, 80])

        y1 = module.normalise_y(manual_result1, auto_evaluation_result1,
                                module.weighting_manual.value, module.weighting_auto.value)
        y1 = np.around(y1, decimals=3)

        self.assertEqual(y1, 0.244)

        manual_result2 = np.array([20])
        auto_evaluation_result2 = np.array([20, 20])

        y2 = module.normalise_y(manual_result2, auto_evaluation_result2,
                                module.weighting_manual.value, module.weighting_auto.value)
        y2 = np.around(y2, decimals=3)

        self.assertEqual(y2, 0.2)

        manual_result3 = np.array([0])
        auto_evaluation_result3 = np.array([0, 0])

        y3 = module.normalise_y(manual_result3, auto_evaluation_result3,
                                module.weighting_manual.value, module.weighting_auto.value)
        self.assertEqual(y3, 0)

        manual_result4 = []
        auto_evaluation_result4 = np.array([30, 60])

        y4 = module.normalise_y(manual_result4, auto_evaluation_result4,
                                module.weighting_manual.value, module.weighting_auto.value)
        self.assertEqual(y4, 0.45)

        manual_result5 = np.array([60])
        auto_evaluation_result5 = []

        y5 = module.normalise_y(manual_result5, auto_evaluation_result5,
                                module.weighting_manual.value, module.weighting_auto.value)
        self.assertEqual(y5, 0.6)

    '''Test helper function to get modules in pipeline'''
    def test_05_get_module_list(self):
        module1 = instantiate_module("IdentifyPrimaryObjects")
        module1.module_num = 1
        module2 = instantiate_module("Smooth")
        module2.module_num = 2
        module3 = instantiate_module("Resize")
        module3.module_num = 3
        module4 = self.make_instance()
        module4.module_num = 4

        pipeline = cellprofiler.pipeline.Pipeline()

        pipeline.add_module(module1)
        pipeline.add_module(module2)
        pipeline.add_module(module3)
        pipeline.add_module(module4)

        module_list = module4.get_module_list(pipeline)

        self.assertEqual(len(module_list), 4)
        self.assertEqual(module_list[0], "IdentifyPrimaryObjects #1")
        self.assertEqual(module_list[1], "Smooth #2")
        self.assertEqual(module_list[2], "Resize #3")
        self.assertEqual(module_list[3], "BayesianOptimisation #4")

    '''Test helper function to get settings from modules chosen in BO module'''
    def test_06_get_settings_list(self):
        module1 = instantiate_module("IdentifyPrimaryObjects")
        module1.module_num = 1
        module2 = instantiate_module("Smooth")
        module2.module_num = 2
        module3 = instantiate_module("Resize")
        module3.module_num = 3
        module4 = self.make_instance()
        module4.module_num = 4
        module4.parameters[0].module_names.value = "IdentifyPrimaryObjects #1"
        module4.add_parameter()
        module4.parameters[1].module_names.value = "Smooth #2"
        module4.add_parameter()
        module4.parameters[2].module_names.value = "Resize #3"
        module4.add_parameter()
        module4.parameters[3].module_names.value = "BayesianOptimisation #4"

        pipeline = cellprofiler.pipeline.Pipeline()

        pipeline.add_module(module1)
        pipeline.add_module(module2)
        pipeline.add_module(module3)
        pipeline.add_module(module4)

        settings_list = module4.get_settings_from_modules(pipeline)

        self.assertTrue("Use advanced settings?" in settings_list)
        self.assertTrue("Select smoothing method" in settings_list)
        self.assertTrue("Resizing factor" in settings_list)
        self.assertTrue("No. of settings to be adjusted" in settings_list)












