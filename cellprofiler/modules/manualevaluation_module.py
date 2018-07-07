# coding=utf-8

"""
From OverlayOutlines
Should be used for manual/partly automated evaluation!
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
import cellprofiler.preferences
import cellprofiler.gui
import cellprofiler.gui.figure

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


class ManualEvaluation(cellprofiler.module.Module):
    module_name = 'ManualEvaluation'
    variable_revision_number = 1
    category = "Advanced"

    def create_settings(self):

        module_explanation = [
            "Module used to manually evaluate quality of identifying objects (eg cytoplasm, adhesions). "
            "Needs to be placed after IdentifyObjects modules"]

        self.set_notes([" ".join(module_explanation)])

        self.accuracy_threshold = cellprofiler.setting.Integer(
            text="Set min quality threshold (1-10)",
            value=8,
            minval=0,
            maxval=10,
            doc="""\
        BlaBlaBla
        """
        )

        self.divider = cellprofiler.setting.Divider()

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
            value="Inner",
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
            "EvaluationOverlay",
            doc="""\
Enter the name of the output image with the outlines overlaid. This
image can be selected in later modules (for instance, **SaveImages**).
"""
        )

        self.spacer = cellprofiler.setting.Divider(line=False)

        self.outlines = []

        self.add_outline(can_remove=False)

        self.add_outline_button = cellprofiler.setting.DoSomething("", "Add another outline", self.add_outline)

    def add_outline(self, can_remove=True):
        group = cellprofiler.setting.SettingsGroup()
        if can_remove:
            group.append("divider", cellprofiler.setting.Divider(line=False))

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

        if can_remove:
            group.append(
                "remover",
                cellprofiler.setting.RemoveSettingButton("", "Remove this outline", self.outlines, group)
            )

        self.outlines.append(group)

    def settings(self):
        result = [self.accuracy_threshold, self.image_name, self.output_image_name,
                  self.line_mode]
        for outline in self.outlines:
            result += [outline.color, outline.objects_name]
        return result

    def visible_settings(self):
        result = [self.accuracy_threshold, self.divider, self.image_name]
        result += [self.output_image_name, self.line_mode, self.spacer]
        for outline in self.outlines:
            result += [outline.objects_name]
            result += [outline.color]
            if hasattr(outline, "remover"):
                result += [outline.remover]
        result += [self.add_outline_button]
        return result

    def run(self, workspace):
        #
        # Get the image pixels from the image set
        #
        base_image, dimensions = self.base_image(workspace)

        #
        # get the object outlines as pixel data
        #
        pixel_data = self.run_color(workspace, base_image.copy())

        # create new output image with the object outlines
        output_image = cellprofiler.image.Image(pixel_data, dimensions=dimensions)

        # add new image with object outlines to workspace image set
        workspace.image_set.add(self.output_image_name.value, output_image)

        image = workspace.image_set.get_image(self.image_name.value)

        # set the input image as the parent image of the output image
        output_image.parent_image = image

        #
        # Call the interaction handler with the images. The interaction
        # handler will be invoked
        #
        base_pixel_data = image.pixel_data
        out_pixel_data = output_image.pixel_data

        result = workspace.interaction_request(self, base_pixel_data, out_pixel_data, workspace)

        print("Result: "+str(result))

        # if show window is true, display output
        if self.show_window:
            workspace.display_data.pixel_data = pixel_data

            workspace.display_data.image_pixel_data = base_image

            workspace.display_data.dimensions = dimensions

    def display(self, workspace, figure):
        dimensions = workspace.display_data.dimensions

        figure.set_subplots((2, 1), dimensions=dimensions)

        # original image
        figure.subplot_imshow_bw(
            0,
            0,
            workspace.display_data.image_pixel_data,
            self.image_name.value
        )

        # image with object outlines
        figure.subplot_imshow(
            1,
            0,
            workspace.display_data.pixel_data,
            self.output_image_name.value,
            sharexy=figure.subplot(0, 0)
        )

    def handle_interaction(self, base_pixel_data, out_pixel_data, workspace):
        #
        # This gets called in the UI thread and we're allowed to import
        # UI modules such as WX or Matplotlib and pop up windows.
        #
        # The documentation for the Python WX widgets is hosted at:
        #
        # http://www.wxpython.org/docs/api/wx-module.html
        #
        # The documentation for Matplotlib is hosted at:
        #
        # http://matplotlib.org/api
        #
        # The Matplotlib examples are often useful because they show the
        # "happy path" - the well-trodden way that people have done things
        # is generally the best choice because it demonstrably works.
        #
        # http://matplotlib.org/examples/index.html
        #
        import wx
        import matplotlib
        import matplotlib.figure
        import matplotlib.lines
        import matplotlib.cm
        import matplotlib.backends.backend_wxagg
        #
        # Make a wx.Dialog. "with" will garbage collect all of the
        # UI resources when the user closes the dialog.
        #
        # This is how our dialog is structured:
        #
        # -------- WX Dialog frame ---------
        # |                                |
        # |  ----- WX BoxSizer ----------  |
        # |  |                          |  |
        # |  |  -- Matplotlib canvas -- |  |
        # |  |  |                     | |  |
        # |  |  |  ---- Figure ------ | |  |
        # |  |  |  |                | | |  |
        # |  |  |  |  --- Axes ---- | | |  |
        # |  |  |  |  |           | | | |  |
        # |  |  |  |  | AxesImage | | | |  |
        # |  |  |  |  |           | | | |  |
        # |  |  |  |  | Line2D    | | | |  |
        # |  |  |  |  ------------- | | |  |
        # |  |  |  |                | | |  |
        # |  |  |  ------------------ | |  |
        # |  |  ----------------------- |  |
        # |  |                          |  |
        # |  |  | WX StdDlgButtonSizer| |  |
        # |  |  |                     | |  |
        # |  |  |  WX Rating Buttons  | |  |
        # |  |  | |                 | | |  |
        # |  |  | ------------------- | |  |
        # |  |  ----------------------- |  |
        # |  ----------------------------  |
        # ----------------------------------
        #

        with wx.Dialog(None, title="Rate images", size=(640, 720)) as dlg:
            #
            # A wx.Sizer lets you automatically adjust the size
            # of a window's subwindows.
            #
            dlg.Sizer = wx.BoxSizer(wx.VERTICAL)
            #
            # We draw on the figure
            #
            figure = matplotlib.figure.Figure()
            #
            # Define an Axes on the figure
            #
            axes = figure.add_axes((.05, .05, .9, .9))


            # image with object outlines
            # axes.imshow(
            #     base_pixel_data, cmap='gray'
            # )
            axes.imshow(
                out_pixel_data
            )

            #
            # The canvas renders the figure
            #
            canvas = matplotlib.backends.backend_wxagg.FigureCanvasWxAgg(
                dlg, -1, figure)
            #
            # Put the canvas in the dialog
            #
            dlg.Sizer.Add(canvas, 1, wx.EXPAND)



            # ###########
            # dimensions = workspace.display_data.dimensions
            #
            # figure.set_subplots((2, 1), dimensions=dimensions)
            #
            # # original image
            # figure.subplot_imshow_bw(
            #     0,
            #     0,
            #     workspace.display_data.image_pixel_data,
            #     self.image_name.value
            # )
            #
            # # image with object outlines
            # figure.subplot_imshow(
            #     1,
            #     0,
            #     workspace.display_data.pixel_data,
            #     self.output_image_name.value,
            #     sharexy=figure.subplot(0, 0)
            # )
            #

            #
            # This is a button sizer and it handles the OK button at the bottom.
            # WX will fill in the appropriate names for buttons in this sizer:
            # wx.ID_OK = OK button
            # wx.ID_CANCEL = Cancel button
            # wx.ID_YES / wx.ID_NO
            #
            button_sizer = wx.StdDialogButtonSizer()
            dlg.Sizer.Add(button_sizer, 0, wx.EXPAND)
            one_button = wx.Button(dlg, name="1")
            # two_button = wx.Button(dlg, name="2")
            button_sizer.AddButton(one_button)
            # button_sizer.AddButton(two_button)
            button_sizer.Realize()

            #
            # "on_button" gets called when the button is pressed.
            #
            # ok_button.Bind directs WX to handle a button press event
            # by calling "on_button" with the event.
            #
            # dlg.EndModal tells WX to close the dialog and return control
            # to the caller.
            #
            def on_button(event):
                quality = 1
                dlg.EndModal(1)

            one_button.Bind(wx.EVT_BUTTON, on_button)
            # two_button.Bind(wx.EVT_BUTTON, on_button)


            #
            # Layout and show the dialog. The WX Layout() method tells
            # WX to use the sizers to place the dialog's controls:
            # the canvas and OK button.
            #
            dlg.Layout()
            dlg.ShowModal()
            #
            # Return the quality measure
            #
            return 1


    #
    # use matplotlib to display results for evaluation
    #


    def base_image(self, workspace):

        image = workspace.image_set.get_image(self.image_name.value)

        pixel_data = skimage.img_as_float(image.pixel_data)

        if image.multichannel:
            return pixel_data, image.dimensions

        return skimage.color.gray2rgb(pixel_data), image.dimensions

    #
    # prepares colors to draw the outlines of the objects selected
    #
    def run_color(self, workspace, pixel_data):
        for outline in self.outlines:
            objects = workspace.object_set.get_objects(outline.objects_name.value)

            color = tuple(c / 255.0 for c in outline.color.to_rgb())

            pixel_data = self.draw_outlines(pixel_data, objects, color)

        return pixel_data

    #
    # draws the outlines of the objects selected
    #
    def draw_outlines(self, pixel_data, objects, color):
        for labels, _ in objects.get_labels():
            resized_labels = self.resize(pixel_data, labels)

            if objects.volumetric:
                for index, plane in enumerate(resized_labels):
                    pixel_data[index] = skimage.segmentation.mark_boundaries(
                        pixel_data[index],
                        plane,
                        color=color,
                        mode=self.line_mode.value.lower()
                    )
            else:
                pixel_data = skimage.segmentation.mark_boundaries(
                    pixel_data,
                    resized_labels,
                    color=color,
                    mode=self.line_mode.value.lower()
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
