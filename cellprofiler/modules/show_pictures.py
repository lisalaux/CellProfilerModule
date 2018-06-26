# coding=utf-8

"""
From OverlayOutlines
===============

"""

import numpy
import skimage.color
import skimage.segmentation
import skimage.util

import cellprofiler.image
import cellprofiler.module
import cellprofiler.setting
import cellprofiler.object

WANTS_COLOR = "Color"

MAX_IMAGE = "Max of image"
MAX_POSSIBLE = "Max possible"

COLORS = {"White": (1, 1, 1),
          "Black": (0, 0, 0),
          "Red": (1, 0, 0),
          "Green": (0, 1, 0),
          "Blue": (0, 0, 1),
          "Yellow": (1, 1, 0)}

COLOR_ORDER = ["Red", "Green", "Blue", "Yellow", "White", "Black"]

FROM_IMAGES = "Image"
FROM_OBJECTS = "Objects"

NUM_FIXED_SETTINGS_V1 = 5
NUM_FIXED_SETTINGS_V2 = 6
NUM_FIXED_SETTINGS_V3 = 6
NUM_FIXED_SETTINGS_V4 = 6
NUM_FIXED_SETTINGS = 6

NUM_OUTLINE_SETTINGS_V2 = 2
NUM_OUTLINE_SETTINGS_V3 = 4
NUM_OUTLINE_SETTINGS_V4 = 2
NUM_OUTLINE_SETTINGS = 2


class ShowPictures(cellprofiler.module.Module):
    module_name = 'ShowPictures'
    variable_revision_number = 1
    category = "Image Processing"

    def create_settings(self):
        self.module_results = cellprofiler.setting.Choice(
            "Display resuts from",
            choices=[""],
            choices_fn=self.get_identifying_module_list,
            doc="""\
             BlaBlaBla
             """
        )

        self.image_name = cellprofiler.setting.ImageNameSubscriber(
            "Select image on which to display outlines",
            cellprofiler.setting.NONE,
            doc="""\
        *(Used only when a blank image has not been selected)*

        Choose the image to serve as the background for the outlines. You can
        choose from images that were loaded or created by modules previous to
        this one.
        """
        )

        self.line_mode = cellprofiler.setting.Choice(
            "How to outline",
            ["Inner", "Outer", "Thick"],
            value="Thick",
            doc="""\
        Specify how to mark the boundaries around an object:

        -  *Inner:* outline the pixels just inside of objects, leaving
           background pixels untouched.
        -  *Outer:* outline pixels in the background around object boundaries.
           When two objects touch, their boundary is also marked.
        -  *Thick:* any pixel not completely surrounded by pixels of the same
           label is marked as a boundary. This results in boundaries that are 2
           pixels thick.
        """
        )

        self.output_image_name = cellprofiler.setting.ImageNameProvider(
            "Name the output image",
            "OrigOverlay",
            doc="""\
        Enter the name of the output image with the outlines overlaid. This
        image can be selected in later modules (for instance, **SaveImages**).
        """
        )

        self.outlines = []

        self.add_outline()

    def add_outline(self):
        group = cellprofiler.setting.SettingsGroup()

        group.append(
            "objects_name",
            cellprofiler.setting.ObjectNameSubscriber(
                "Select objects to display",
                cellprofiler.setting.NONE,
                doc="Choose the objects whose outlines you would like to display."
            )
        )

        default_color = (COLOR_ORDER[len(self.outlines)] if len(self.outlines) < len(COLOR_ORDER) else COLOR_ORDER[0])

        group.append(
            "color",
            cellprofiler.setting.Color(
                "Select outline color",
                default_color,
                doc="Objects will be outlined in this color."
            )
        )

        self.outlines.append(group)

    def settings(self):
        result = [self.image_name, self.output_image_name,
                  self.line_mode]
        for outline in self.outlines:
            result += [outline.color, outline.objects_name]
        return result

    def visible_settings(self):
        result = [self.module_results]
        result += [self.image_name]
        for outline in self.outlines:
            result += [outline.objects_name]
            result += [outline.color]
        return result

    def run(self, workspace):
        base_image, dimensions = self.base_image(workspace)

        pixel_data = self.run_color(base_image.copy())

        output_image = cellprofiler.image.Image(pixel_data, dimensions=dimensions)

        workspace.image_set.add(self.output_image_name, output_image)

        image = workspace.image_set.get_image(self.image_name.value)

        output_image.parent_image = image

        if self.show_window:
            workspace.display_data.pixel_data = pixel_data

            workspace.display_data.image_pixel_data = base_image

            workspace.display_data.dimensions = dimensions

    def base_image(self, workspace):
        image = workspace.image_set.get_image(self.image_name)

        pixel_data = skimage.img_as_float(image.pixel_data)

        if image.multichannel:
            return pixel_data, image.dimensions

        return skimage.color.gray2rgb(pixel_data), image.dimensions

    def display(self, workspace, figure):
        dimensions = workspace.display_data.dimensions

        figure.set_subplots((2, 1), dimensions=dimensions)

        figure.subplot_imshow_bw(
            0,
            0,
            workspace.display_data.image_pixel_data,
            self.image_name.value
        )

        figure.subplot_imshow(
            1,
            0,
            workspace.display_data.pixel_data,
            self.output_image_name,
            sharexy=figure.subplot(0, 0)
        )

    def run_color(self, workspace, pixel_data):
        for outline in self.outlines:
            objects = workspace.object_set.get_objects(outline.objects_name.value)

            color = tuple(c / 255.0 for c in outline.color.to_rgb())

            pixel_data = self.draw_outlines(pixel_data, objects, color)

        return pixel_data

    def draw_outlines(self, pixel_data, objects, color):
        for labels, _ in objects.get_labels():
            resized_labels = self.resize(pixel_data, labels)

            if objects.volumetric:
                for index, plane in enumerate(resized_labels):
                    pixel_data[index] = skimage.segmentation.mark_boundaries(
                        pixel_data[index],
                        plane,
                        color=color,
                        mode=self.line_mode.lower()
                    )
            else:
                pixel_data = skimage.segmentation.mark_boundaries(
                    pixel_data,
                    resized_labels,
                    color=color,
                    mode=self.line_mode.lower()
                )

        return pixel_data

    def resize(self, pixel_data, labels):
        initial_shape = labels.shape

        final_shape = pixel_data.shape

        if pixel_data.ndim > labels.ndim:  # multichannel
            final_shape = final_shape[:-1]

        adjust = numpy.subtract(final_shape, initial_shape)

        cropped = skimage.util.crop(
            labels,
            [(0, dim_adjust) for dim_adjust in numpy.abs(numpy.minimum(adjust, numpy.zeros_like(adjust)))]
        )

        return numpy.pad(
            cropped,
            [(0, dim_adjust) for dim_adjust in numpy.maximum(adjust, numpy.zeros_like(adjust))],
            mode="constant",
            constant_values=(0)
        )

    def volumetric(self):
        return True

    def get_identifying_module_list(self, pipeline):
        all_modules = pipeline.modules()
        identifying_module_list = []
        for m in all_modules:
            if "Identify" in str(m.module_name):
                identifying_module_list.append(str(m.module_name))
        return identifying_module_list

    # def get_object_name(self, pipeline):
    #     all_modules = pipeline.modules()
    #     object_name = ""
    #
    #     for module in all_modules:
    #         if "Identify" in str(module.module_name):
    #             for setting in module.settings():
    #                 if setting.get_text() == "Name the primary objects to be identified":
    #                     print(setting.get_value())
    #                     object_name = str(setting.get_value())
    #     return object_name
    #
    # def get_image_name(self, pipeline):
    #     all_modules = pipeline.modules()
    #     image_name = ""
    #
    #     for module in all_modules:
    #         if "Identify" in str(module.module_name):
    #             for setting in module.settings():
    #                 if setting.get_text() == "Select the input image":
    #                     print(setting.get_value())
    #                     image_name = str(setting.get_value())
    #     return image_name

