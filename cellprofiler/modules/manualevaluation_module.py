# coding=utf-8

"""
ManualEvaluation
===================

**ManualEvaluation** gives the user the opportunity to manually evaluate the quality of identified objects
(eg nuclei, cytoplasm, adhesions).

It needs to be placed after IdentifyObjects modules.
The first object chosen in this module will be treated as the main object on which the quality measurement
will be saved. Further supporting object outlines can be chosen for display.
Their quality will not be measured or rated.

============ ============ ===============
Supports 2D? Supports 3D? Respects masks?
============ ============ ===============
YES          YES           NO
============ ============ ===============

"""

import numpy
import skimage.color
import skimage.segmentation
import skimage.util

import cellprofiler.image
import cellprofiler.module
import cellprofiler.setting
import cellprofiler.measurement
import cellprofiler.object
import cellprofiler.preferences
import cellprofiler.gui
import cellprofiler.gui.figure


#
# Constants
#
CATEGORY = 'Evaluation'
QUALITY = 'ManualQuality'
FEATURE_NAME = 'Evaluation_ManualQuality'

COLORS = {"White": (1, 1, 1),
          "Black": (0, 0, 0),
          "Red": (1, 0, 0),
          "Green": (0, 1, 0),
          "Blue": (0, 0, 1),
          "Yellow": (1, 1, 0)}

COLOR_ORDER = ["Red", "Green", "Blue", "Yellow", "White", "Black"]


class ManualEvaluation(cellprofiler.module.Module):
    module_name = 'ManualEvaluation'
    variable_revision_number = 1
    category = "Advanced"

    #######################################################################
    # Create and set CellProfiler settings for GUI and Pipeline execution #
    #######################################################################

    def create_settings(self):

        module_explanation = [
            "Module for manual evaluation of the quality of the identified objects (eg cytoplasm, adhesions). "
            "Needs to be placed after IdentifyObjects modules. Choose the main object to rate the quality for first."
            "You can choose further supporting objects to display. Their qulaity will not be rated."]

        self.set_notes([" ".join(module_explanation)])

        self.accuracy_threshold = cellprofiler.setting.Integer(
            text="Set min quality threshold (1-10)",
            value=8,
            minval=1,
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

    #
    # add objects to outline and color chooser
    # add a remove-button for all outlines except a mandatory one
    #
    def add_outline(self, can_remove=True):
        group = cellprofiler.setting.SettingsGroup()
        if can_remove:
            group.append("divider", cellprofiler.setting.Divider(line=False))

        group.append(
            "objects_name",
            cellprofiler.setting.ObjectNameSubscriber(
                "Select objects to display",
                cellprofiler.setting.NONE,
                doc="Choose the objects whose outlines you would like to display. The first object chosen will be the "
                    "leading object, storing the quality measurement needed for the Bayesian Optimisation."
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


        #
        # interrupt pipeline execution and send interaction request to workspace
        # as run-method is executed in a separate thread, it needs to give control to the UI thread
        # the handle_interaction method will be called and return user input (quality measure)
        #
        result = workspace.interaction_request(self, base_pixel_data, out_pixel_data)

        deviation = []

        print("Result: "+str(result))

        if int(result) < int(self.accuracy_threshold.value):
            print("not passed")
            deviation += [int(self.accuracy_threshold.value) - int(result)]

        else:
            print("passed")
            deviation += [0]

        dev_array = numpy.array(deviation)
        # print(dev_array)

        # Add measurement for deviations to workspace measurements to make it available to Bayesian Module
        # note: first object chosen is leading object where measurements are saved

        workspace.add_measurement(self.outlines[0].objects_name.value, FEATURE_NAME, dev_array)

    #
    # called during run of the pipeline; control is passed to UI
    #
    def handle_interaction(self, base_pixel_data, out_pixel_data):
        #
        # import UI modules (WX and Matplotlib) to show a pop up window for user interaction
        #
        import wx
        import matplotlib.pyplot as plt
        import matplotlib.backends.backend_wxagg
        from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar

        #
        # Make a wx.Dialog. "with" will garbage collect all of the
        # UI resources when the user closes the dialog.
        #
        # This is how the dialog frame is structured:
        #
        # -------- WX Dialog frame ---------
        # |  ----- WX BoxSizer ----------  |
        # |  |  -- Matplotlib canvas -- |  |
        # |  |  |  ----- Toolbar ---- | |  |
        # |  |  |  ----- Figure ----- | |  |
        # |  |  |  |  --- Axes ---- | | |  |
        # |  |  |  |  |           | | | |  |
        # |  |  |  |  | AxesImage | | | |  |
        # |  |  |  |  |           | | | |  |
        # |  |  |  |  ------------- | | |  |
        # |  |  |  ------------------ | |  |
        # |  |  ----------------------- |  |
        # |  |  |-----WX BoxSizer-----| |  |
        # |  |  |  WX Rating Label    | |  |
        # |  |  |     + Buttons       | |  |
        # |  |  | ------------------- | |  |
        # |  |  ----------------------- |  |
        # |  ----------------------------  |
        # ----------------------------------
        #

        with wx.Dialog(None, title="Rate object detection quality", size=(800, 600)) as dlg:
            #
            # default quality value to be returned when no button was pressed is 0
            #
            self.quality = 0

            #
            # A wx.Sizer lets you automatically adjust the size
            # of a window's subwindows.
            #
            dlg.Sizer = wx.BoxSizer(wx.VERTICAL)
            #
            # We draw on the figure
            #
            figure = plt.figure()
            #
            # Define an Axes on the figure
            #
            axes = figure.add_axes((.05, .05, .9, .9))
            #
            # show the original image and overlays
            #
            axes.imshow(base_pixel_data, 'gray', interpolation='none')
            axes.imshow(out_pixel_data, 'gray', interpolation='none', alpha=0.5)
            #
            # canvas which renders the figure
            #
            canvas = matplotlib.backends.backend_wxagg.FigureCanvasWxAgg(dlg, -1, figure)
            #
            # Create a default toolbar for the canvas image
            #
            toolbar = NavigationToolbar(canvas)
            toolbar.Realize()
            #
            # Put the toolbar and the canvas in the dialog
            #
            dlg.Sizer.Add(toolbar, 0, wx.LEFT | wx.EXPAND)
            dlg.Sizer.Add(canvas, 1, wx.EXPAND)
            #
            # add horizontal Sizer to Frame Sizer
            #
            hsizer = wx.BoxSizer(wx.HORIZONTAL)
            dlg.Sizer.Add(hsizer, 2, wx.ALIGN_CENTER)
            #
            # create info label and rating buttons
            #
            info_label = wx.StaticText(dlg, label="Rate the quality of the object detection: ")

            button_1 = wx.Button(dlg, size=(40, -1), label="1")
            button_2 = wx.Button(dlg, size=(40, -1), label="2")
            button_3 = wx.Button(dlg, size=(40, -1), label="3")
            button_4 = wx.Button(dlg, size=(40, -1), label="4")
            button_5 = wx.Button(dlg, size=(40, -1), label="5")
            button_6 = wx.Button(dlg, size=(40, -1), label="6")
            button_7 = wx.Button(dlg, size=(40, -1), label="7")
            button_8 = wx.Button(dlg, size=(40, -1), label="8")
            button_9 = wx.Button(dlg, size=(40, -1), label="9")
            button_10 = wx.Button(dlg, size=(40, -1), label="10")

            #
            # add elements to horizontal sizer
            #
            hsizer.Add(info_label, 0, wx.ALIGN_CENTER)
            hsizer.Add(button_1, 0, wx.ALIGN_CENTER)
            hsizer.Add(button_2, 0, wx.ALIGN_CENTER)
            hsizer.Add(button_3, 0, wx.ALIGN_CENTER)
            hsizer.Add(button_4, 0, wx.ALIGN_CENTER)
            hsizer.Add(button_5, 0, wx.ALIGN_CENTER)
            hsizer.Add(button_6, 0, wx.ALIGN_CENTER)
            hsizer.Add(button_7, 0, wx.ALIGN_CENTER)
            hsizer.Add(button_8, 0, wx.ALIGN_CENTER)
            hsizer.Add(button_9, 0, wx.ALIGN_CENTER)
            hsizer.Add(button_10, 0, wx.ALIGN_CENTER)

            #
            # "on_button" gets called when the button is pressed.
            #
            # button.Bind directs WX to handle a button press event
            # by calling "on_button" with the event.
            #
            # dlg.EndModal tells WX to close the dialog and return control
            # to the caller.
            #
            def on_button(event):
                b = event.GetEventObject().GetLabel()
                self.quality = b
                dlg.EndModal(1)

            button_1.Bind(wx.EVT_BUTTON, on_button)
            button_2.Bind(wx.EVT_BUTTON, on_button)
            button_3.Bind(wx.EVT_BUTTON, on_button)
            button_4.Bind(wx.EVT_BUTTON, on_button)
            button_5.Bind(wx.EVT_BUTTON, on_button)
            button_6.Bind(wx.EVT_BUTTON, on_button)
            button_7.Bind(wx.EVT_BUTTON, on_button)
            button_8.Bind(wx.EVT_BUTTON, on_button)
            button_9.Bind(wx.EVT_BUTTON, on_button)
            button_10.Bind(wx.EVT_BUTTON, on_button)

            #
            # Layout and show the dialog
            #
            dlg.Layout()
            dlg.ShowModal()

            #
            # Return the quality measure set by button press (or window close; default = 0)
            #
            return self.quality

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

    ####################################################################
    # Tell CellProfiler about the measurements produced in this module #
    ####################################################################

    #
    # Provide the measurements for use in the database or a spreadsheet
    #
    def get_measurement_columns(self, pipeline):

        input_object_name = self.outlines[0].objects_name.value

        return [input_object_name, FEATURE_NAME, cellprofiler.measurement.COLTYPE_FLOAT]

    #
    # Return a list of the measurement categories produced by this module if the object_name matches
    #
    def get_categories(self, pipeline, object_name):
        if object_name == self.outlines[0].objects_name:
            return [CATEGORY]

        return []

    #
    # Return the feature names if the object_name and category match to GUI
    #
    def get_measurements(self, pipeline, object_name, category):
        if (object_name == self.outlines[0].objects_name and category == CATEGORY):
            return [QUALITY]

        return []
