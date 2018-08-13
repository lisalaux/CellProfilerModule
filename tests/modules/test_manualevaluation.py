import unittest
import numpy as np
from scipy.ndimage import label, distance_transform_edt

import cellprofiler.pipeline as cpp
import cellprofiler.measurement as cpmeas
import cellprofiler.image as cpi
import cellprofiler.object as cpo
import cellprofiler.workspace as cpw
from cellprofiler.modules import instantiate_module

#
# Constants
#
INPUT_IMAGE_NAME = "inputImage"
OUTPUT_IMAGE_NAME = "outputImage"
INPUT_OBJECT_NAME = "UnfilteredNuclei"
OTHER_OBJECT_NAME = "Cytoplasm"
NEW_MEASUREMENT = 'Evaluation_ManualQuality'


class TestManualEvaluation(unittest.TestCase):
    '''SetUp'''
    def make_instance(self):
        '''Return an instance of of the module'''
        return instantiate_module("ManualEvaluation")

    '''Test if instance is created'''
    def test_01_can_load(self):
        self.assertFalse(self.make_instance() is None)

    '''Test if settings values are created correctly'''
    def test_02_create_settings(self):
        module = self.make_instance()
        module.accuracy_threshold.value = 8
        module.image_name.value = INPUT_IMAGE_NAME
        module.line_mode.value = "Inner"
        module.output_image_name.value = OUTPUT_IMAGE_NAME
        module.outlines[0].objects_name.value = INPUT_OBJECT_NAME
        module.outlines[0].color.value = "gray"
        module.add_outline()
        module.outlines[1].objects_name.value = OTHER_OBJECT_NAME
        module.outlines[1].color.value = "red"

        self.assertEqual(module.accuracy_threshold.value, 8)
        self.assertEqual(module.image_name.value, INPUT_IMAGE_NAME)
        self.assertEqual(module.line_mode.value, "Inner")
        self.assertEqual(module.output_image_name.value, OUTPUT_IMAGE_NAME)
        self.assertEqual(module.outlines[0].objects_name.value, INPUT_OBJECT_NAME)
        self.assertEqual(module.outlines[0].color.value, "gray")
        self.assertEqual(module.outlines[1].objects_name.value, OTHER_OBJECT_NAME)
        self.assertEqual(module.outlines[1].color.value, "red")

    '''Test if settings are correct'''
    def test_03_settings(self):
        module = self.make_instance()
        module.accuracy_threshold.value = 8
        module.image_name.value = INPUT_IMAGE_NAME
        module.line_mode.value = "Inner"
        module.output_image_name.value = OUTPUT_IMAGE_NAME
        module.outlines[0].objects_name.value = INPUT_OBJECT_NAME
        module.outlines[0].color.value = "gray"
        module.add_outline()
        module.outlines[1].objects_name.value = OTHER_OBJECT_NAME
        module.outlines[1].color.value = "red"

        settings = module.settings()
        self.assertEqual(len(settings), 8)
        self.assertEqual(id(module.accuracy_threshold), id(settings[0]))
        self.assertEqual(id(module.image_name), id(settings[1]))
        self.assertEqual(id(module.output_image_name), id(settings[2]))
        self.assertEqual(id(module.line_mode), id(settings[3]))
        self.assertEqual(id(module.outlines[0].color), id(settings[4]))
        self.assertEqual(id(module.outlines[0].objects_name), id(settings[5]))
        self.assertEqual(id(module.outlines[1].color), id(settings[6]))
        self.assertEqual(id(module.outlines[1].objects_name), id(settings[7]))

    '''Test if new measurement is created after run'''
    def test_04_run(self):
        module = self.make_instance()
        module.accuracy_threshold.value = 8
        module.image_name.value = INPUT_IMAGE_NAME
        module.line_mode.value = "Inner"
        module.output_image_name.value = OUTPUT_IMAGE_NAME
        module.outlines[0].objects_name.value = INPUT_OBJECT_NAME
        module.outlines[0].color.value = "gray"

        module.module_num = 1
        pipeline = cpp.Pipeline()
        pipeline.add_module(module)

        # Make Image Set
        r = np.random.RandomState()
        r.seed(20)
        pixel_data = r.uniform(size=(88, 66)).astype(np.float32)
        mask = r.uniform(size=pixel_data.shape) > .5
        input_image = cpi.Image(pixel_data, mask)

        image_set_list = cpi.ImageSetList()
        image_set = image_set_list.get_image_set(1)
        image_set.add(INPUT_IMAGE_NAME, input_image)

        #
        # Create an object set and some objects for the set (randomly)
        # Pick a bunch of random points, dilate them using the distance
        # transform and then label the result
        #
        object_set = cpo.ObjectSet()
        r = np.random.RandomState()
        r.seed(12)
        bimg = np.ones((100, 100), bool)
        bimg[r.randint(0, 100, 50), r.randint(0, 100, 50)] = False
        labels, count = label(distance_transform_edt(bimg) <= 5)

        objects = cpo.Objects()
        objects.segmented = labels
        object_set.add_objects(objects, INPUT_OBJECT_NAME)

        #
        # Add measurements
        #
        measurements = cpmeas.Measurements()

        #
        # Make the workspace
        #
        workspace = cpw.Workspace(pipeline, module, image_set, object_set,
                                  measurements, None)

        #
        # Run the workspace (note: calling run method itself not possible due to user interaction request;
        # some algorithms were replicated instead
        #
        base_image, dimensions = module.base_image(workspace)

        #
        # get the object outlines as pixel data
        #
        pixel_data = module.run_color(workspace, base_image.copy())

        # create new output image with the object outlines
        output_image = cpi.Image(pixel_data, dimensions=dimensions)

        # add new image with object outlines to workspace image set
        workspace.image_set.add(module.output_image_name.value, output_image)

        image = workspace.image_set.get_image(module.image_name.value)

        # set the input image as the parent image of the output image
        output_image.parent_image = image

        #
        # SKIP CALLING THE INTERACTION HANDLER AS NOT APPROPRIATE FOR THE TESTS
        #

        # set result instead
        result = 9

        deviation = []

        if int(result) < int(module.accuracy_threshold.value):
            dev = int(module.accuracy_threshold.value) - int(result)
            p_dev = (dev * 100) / int(module.accuracy_threshold.value)
            deviation += [p_dev]

        else:
            deviation += [0]

        dev_array = np.array(deviation)

        # Add measurement for deviations to workspace measurements to make it available to Bayesian Module
        # note: first object chosen is leading object where measurements are saved

        workspace.add_measurement(module.outlines[0].objects_name.value, NEW_MEASUREMENT, dev_array)

        #
        # Check output
        #
        values = measurements.get_measurement(INPUT_OBJECT_NAME, NEW_MEASUREMENT)
        self.assertEqual(values, np.array([[0]]))
