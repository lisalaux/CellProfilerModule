import unittest
import numpy as np
from scipy.ndimage import label, distance_transform_edt

import cellprofiler.pipeline as cpp
import cellprofiler.measurement as cpmeas
import cellprofiler.object as cpo
import cellprofiler.workspace as cpw
from cellprofiler.modules import instantiate_module

#
# Constants
#
INPUT_OBJECT_NAME = "UnfilteredNuclei"
EXISTING_MEASUREMENT = "AreaShape_Solidity"
NEW_MEASUREMENT = "Evaluation_Deviation"


class TestAutomatedEvaluation(unittest.TestCase):
    '''SetUp'''
    def make_instance(self):
        '''Return an instance of of the module'''
        return instantiate_module("AutomatedEvaluation")

    '''Test if instance is created'''
    def test_01_can_load(self):
        self.assertFalse(self.make_instance() is None)

    '''Test if settings are created'''
    def test_02_settings(self):
        module = self.make_instance()
        module.input_object_name.value = INPUT_OBJECT_NAME
        module.measurements[0].measurement.value = EXISTING_MEASUREMENT
        module.measurements[0].range.min = 0.9
        module.measurements[0].range.max = 1.0
        settings = module.settings()
        self.assertEqual(len(settings), 3)
        self.assertEqual(id(module.input_object_name), id(settings[0]))
        self.assertEqual(id(module.measurements[0].measurement), id(settings[1]))
        self.assertEqual(id(module.measurements[0].range), id(settings[2]))

    '''Test if new measurement is created after run'''
    def test_03_run(self):
        module = self.make_instance()
        module.input_object_name.value = INPUT_OBJECT_NAME
        module.measurements[0].measurement.value = EXISTING_MEASUREMENT
        module.measurements[0].range.min = 0.9
        module.measurements[0].range.max = 1.0
        module.module_num = 1
        pipeline = cpp.Pipeline()
        pipeline.add_module(module)


        #
        # Create an object set and some objects for the set (randomly)
        # Pick a bunch of random points, dilate them using the distance
        # transform and then label the result.
        #
        object_set = cpo.ObjectSet()
        r = np.random.RandomState()
        r.seed(20)
        bimg = np.ones((100, 100), bool)
        bimg[r.randint(0, 100, 50), r.randint(0, 100, 50)] = False
        labels, count = label(distance_transform_edt(bimg) <= 5)

        objects = cpo.Objects()
        objects.segmented = labels
        object_set.add_objects(objects, INPUT_OBJECT_NAME)

        #
        # Add pre-existing measurements to objects
        #
        measurements = cpmeas.Measurements()
        count = objects.count
        meas = []
        for i in range(0, count):
            meas += [0.99]
        array_meas = np.array(meas)

        measurements.add_measurement(INPUT_OBJECT_NAME, EXISTING_MEASUREMENT, array_meas)

        #
        # Make the workspace
        #
        workspace = cpw.Workspace(pipeline, module, None, object_set,
                                  measurements, None)

        #
        # Run the workspace
        #
        module.run(workspace)

        #
        # Check output
        #
        values = measurements.get_measurement(INPUT_OBJECT_NAME, NEW_MEASUREMENT)
        self.assertEqual(values, np.array([[0]]))
