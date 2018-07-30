import unittest
import numpy as np

from cellprofiler.modules import instantiate_module

#
# Constants
#
INPUT_OBJECT_NAME = "UnfilteredNuclei"
AUTO_MEASUREMENT = "Evaluation_Deviation"
MANUAL_MEASUREMENT = "Evaluation_ManualQuality"
MODULE_NAME = "IdentifyPrimaryObjects"
PARAM_NAME1 = "Size of adaptive window"
PARAM_NAME2 = "Size of smoothing filter"


class TestAutomatedEvaluation(unittest.TestCase):
    '''SetUp'''
    def make_instance(self):
        '''Return an instance of of the module'''
        return instantiate_module("BayesianOptimisation")

    '''Test if instance is created'''
    def test_01_can_load(self):
        self.assertFalse(self.make_instance() is None)

    def test_02_create_settings(self):
        module = self.make_instance()

        module.input_object_name.value = INPUT_OBJECT_NAME
        module.count1.value = 2
        module.count2.value = 2
        module.measurements[0].evaluation_measurement.value = AUTO_MEASUREMENT
        module.add_measurement()
        module.measurements[1].evaluation_measurement.value = MANUAL_MEASUREMENT
        module.parameters[0].module_names.value = MODULE_NAME
        module.parameters[0].parameter_names.value = PARAM_NAME1
        module.add_parameter()
        module.parameters[1].module_names.value = MODULE_NAME
        module.parameters[1].parameter_names.value = PARAM_NAME2

        self.assertEqual(module.input_object_name.value, INPUT_OBJECT_NAME)
        self.assertEqual(module.count1, 2)
        self.assertEqual(module.count2, 2)
        self.assertEqual(module.measurements[0].evaluation_measurement.value, AUTO_MEASUREMENT)
        self.assertEqual(module.measurements[1].evaluation_measurement.value, MANUAL_MEASUREMENT)
        self.assertEqual(module.parameters[0].module_names.value, MODULE_NAME)
        self.assertEqual(module.parameters[0].parameter_names.value, PARAM_NAME1)
        self.assertEqual(module.parameters[1].module_names.value, MODULE_NAME)
        self.assertEqual(module.parameters[1].parameter_names.value, PARAM_NAME2)

    '''Test if settings are created'''
    def test_03_settings(self):
        module = self.make_instance()

        module.input_object_name.value = INPUT_OBJECT_NAME
        module.count1.value = 2
        module.count2.value = 2
        module.measurements[0].evaluation_measurement.value = AUTO_MEASUREMENT
        module.add_measurement()
        module.measurements[1].evaluation_measurement.value = MANUAL_MEASUREMENT
        module.parameters[0].module_names.value = MODULE_NAME
        module.parameters[0].parameter_names.value = PARAM_NAME1
        module.add_parameter()
        module.parameters[1].module_names.value = MODULE_NAME
        module.parameters[1].parameter_names.value = PARAM_NAME2

        settings = module.settings()

        self.assertEqual(len(settings), 9)
        self.assertEqual(id(module.input_object_name), id(settings[0]))
        self.assertEqual(id(module.count1), id(settings[1]))
        self.assertEqual(id(module.count2), id(settings[2]))
        self.assertEqual(id(module.measurements[0].evaluation_measurement), id(settings[3]))
        self.assertEqual(id(module.measurements[1].evaluation_measurement), id(settings[4]))
        self.assertEqual(id(module.parameters[0].module_names), id(settings[5]))
        self.assertEqual(id(module.parameters[0].parameter_names), id(settings[6]))
        self.assertEqual(id(module.parameters[1].module_names), id(settings[7]))
        self.assertEqual(id(module.parameters[1].parameter_names), id(settings[8]))

    '''Test elements of run'''
    def test_04_normalise(self):
        module = self.make_instance()

        manual_result1 = np.array([20])
        auto_evaluation_result1 = np.array([30, 0.0, 5, 80])

        y1 = module.normalise_y(manual_result1, auto_evaluation_result1)
        y1 = np.around(y1, decimals=3)

        self.assertEqual(y1, 0.307)

        manual_result2 = np.array([20])
        auto_evaluation_result2 = np.array([20, 20])

        y2 = module.normalise_y(manual_result2, auto_evaluation_result2)
        y2 = np.around(y2, decimals=3)

        self.assertEqual(y2, 0.577)

        manual_result3 = np.array([0])
        auto_evaluation_result3 = np.array([0, 0])

        y3 = module.normalise_y(manual_result3, auto_evaluation_result3)

        self.assertEqual(y3, 0)

        x_raw = np.array([10, 1.0])

        x = module.normalise_x(x_raw)

        self.assertAlmostEqual(x.tolist(), np.array([0.995, 0.1]).tolist())

    # bayesian functionality will be tested separately






