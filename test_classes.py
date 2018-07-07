import cellprofiler.image
import cellprofiler.module
import cellprofiler.measurement
import cellprofiler.object
import cellprofiler.setting
import cellprofiler.pipeline
import cellprofiler.workspace
import pdbi

'''Modifies a setting of another module and updates the pipeline with the new settings'''

if __name__ == "__main__":
    pdbi.set_trace()
    pipeline = cellprofiler.pipeline.Pipeline()
    pipeline.load("/Users/LisaLaux/Documents/Master_UofG/Master_Project/CellProfiler/ExampleHuman/ExampleHuman.cppipe")

    print(pipeline.modules())

    print("=" * 5)

    modules = pipeline.modules()

    for module in modules:
        if module.module_name == "IdentifyPrimaryObjects":
            for setting in module.settings():
                if setting.get_text() == "Threshold correction factor":
                    print(setting.get_value())
                    setting.set_value("1.5")
                    pipeline.edit_module(module.get_module_num(), is_image_set_modification=False) #be careful with flag
                    print(setting.get_value())

    # pipeline.run_group_with_yield() # useful? may achieve that pipeline runs only until this point
    # pipeline.post_run() # might be helpful
    # pipeline.end_run() # ends pipeline run

    # pipeline.save("/Users/LisaLaux/Documents/Master_UofG/Master_Project/CellProfiler/ExampleHuman/ExampleHuman2.cppipe")
    # safes values in unicode?


####################################
# manual evaluation module

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

import wx
import matplotlib
import matplotlib.figure
import matplotlib.backends
import matplotlib.backends.backend_wxagg

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
        base_image, dimensions = self.base_image(workspace)

        # draw the outlines for the objects selected
        pixel_data = self.run_color(workspace, base_image.copy())

        # create new output image with the object outlines
        output_image = cellprofiler.image.Image(pixel_data, dimensions=dimensions)

        # add new image with object outlines to workspace image set
        workspace.image_set.add(self.output_image_name.value, output_image)

        image = workspace.image_set.get_image(self.image_name.value)

        # set the input image as the parent image of the output image
        output_image.parent_image = image

        # if show window is true, display output
        if self.show_window:
            workspace.display_data.pixel_data = pixel_data

            workspace.display_data.image_pixel_data = base_image

            workspace.display_data.dimensions = dimensions

    def run_as_data_tool(self):
        from cellprofiler.gui.editobjectsdlg import EditObjectsDialog
        import wx
        from wx.lib.filebrowsebutton import FileBrowseButton
        from cellprofiler.modules.namesandtypes import ObjectsImageProvider
        from bioformats import load_image

        #
        # Load the images
        #
        base_image = load_image(self.image_name.value)

        output_image = load_image(self.output_image_name.value)

        with RatingDialog(base_image, output_image) as dialog_box:
            result = dialog_box.ShowModal()
            if result != wx.OK:
                return
            labels = dialog_box.labels

    def handle_interaction(self, base_image, output_image):
        from wx import OK

        with RatingDialog(base_image, output_image) as dialog_box:
            result = dialog_box.ShowModal()
            if result != OK:
                return None
            return dialog_box.labels

    #
    # use matplotlib to display results for evaluation
    #
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

    def is_interactive(self):
        return True


class RatingDialog(wx.Dialog):
    """This dialog can be invoked as an objects editor

    EditObjectsDialog takes an optional labels matrix and guide image. If
    no labels matrix is provided, initially, there are no objects. If there
    is no guide image, a black background is displayed.

    The resutls of EditObjectsDialog are available in the "labels" attribute
    if the return code is wx.OK.
    """
    resume_id = wx.NewId()
    cancel_id = wx.NewId()
    epsilon = 5  # maximum pixel distance to a vertex for hit test
    #
    # The object_number for an artist
    #
    K_LABEL = "label"
    #
    # Whether the artist has been edited
    #
    K_EDITED = "edited"
    #
    # Whether the artist is on the outside of the object (True)
    # or is the border of a hole (False)
    #
    K_OUTSIDE = "outside"
    #
    #
    # Show image / hide image button labels
    #
    D_SHOW_IMAGE = "Show image"
    D_HIDE_IMAGE = "Hide image"

    ID_DISPLAY_IMAGE = wx.NewId()

    def __init__(self, base_image, output_image):
        """Initializer

        guide_image - a grayscale or color image to display behind the labels

        orig_labels - a sequence of label matrices, such as is available from
                      Objects.get_labels()

        allow_overlap - true to allow objects to overlap

        title - title to appear on top of the editing axes
        """
        #
        # Get the labels matrix and make a mask of objects to keep from it
        #
        #
        # Display a UI for choosing objects
        #
        frame_size = wx.GetDisplaySize()
        frame_size = [max(frame_size[0], frame_size[1]) / 2] * 2
        style = wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX
        wx.Dialog.__init__(self, None, -1,
                           "",
                           size=frame_size,
                           style=style)

        self.base_image = base_image
        # self.pixel_data = pixel_data
        self.output_image = output_image
        self.build_ui()
        self.display()
        self.Layout()
        self.layout_sash()
        self.Raise()
        self.panel.SetFocus()

    def build_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        self.figure = matplotlib.figure.Figure()

        self.title = "title"

        class CanvasPatch(matplotlib.backends.backend_wxagg.FigureCanvasWxAgg):
            def __init__(self, parent, id, figure):
                matplotlib.backends.backend_wxagg.FigureCanvasWxAgg.__init__(self, parent, id, figure)

            def print_figure(self, *args, **kwargs):
                self.Parent.inside_print = True
                try:
                    super(CanvasPatch, self).print_figure(*args, **kwargs)
                finally:
                    self.Parent.inside_print = False

        self.panel = CanvasPatch(self, -1, self.figure)
        self.toolbar = cellprofiler.gui.figure.NavigationToolbar(self.panel)
        self.sash_parent = wx.Panel(self)
        #
        # Need to reparent the canvas after instantiating the toolbar so
        # the toolbar gets parented to the frame and the panel gets
        # parented to some window that can be shared with the *^$# sash
        # window.
        #
        self.panel.Reparent(self.sash_parent)
        sizer.Add(self.toolbar, 0, wx.EXPAND)
        sizer.Add(self.sash_parent, 1, wx.EXPAND)
        #
        # Make 3 axes
        #
        self.orig_axes = self.figure.add_subplot(1, 1, 1)
        self.orig_axes.set_zorder(1)  # preferentially select on click.
        self.orig_axes._adjustable = 'box-forced'
        self.orig_axes.set_title(
            self.title,
            fontname=cellprofiler.preferences.get_title_font_name(),
            fontsize=cellprofiler.preferences.get_title_font_size())

        ###################################################
        #
        # The buttons on the bottom
        #
        ###################################################
        sub_sizer = wx.WrapSizer(wx.HORIZONTAL)
        #
        # Need padding on top because tool bar is wonky about its height
        #
        sizer.Add(sub_sizer, 0, wx.ALIGN_CENTER)


        ######################################
        #
        # Buttons for resume and cancel
        #
        ######################################
        button_sizer = wx.StdDialogButtonSizer()
        resume_button = wx.Button(self, self.resume_id, "Done")
        button_sizer.AddButton(resume_button)
        sub_sizer.Add(button_sizer, 0, wx.ALIGN_CENTER)

    def display(self):
        orig_objects_name = self.title

        # Set background to None as we've effectively redrawn the display
        self.background = None
        self.Refresh()

    def layout_sash(self):
        wx.LayoutAlgorithm().LayoutWindow(
                self.sash_parent, self.panel)
        self.panel.draw()
        self.panel.Refresh()

