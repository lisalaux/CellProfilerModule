function handles = MakeProjection(handles)

% Help for the Make Projection module:
% Category: Pre-processing
%
% This module makes a projection of a set of images (e.g. a Z-stack)
% by averaging the pixel intensities at each pixel position. The first
% time through the pipeline (i.e. for image set 1), the whole set of
% images (as defined by a Load Images module) is used to calculate one
% projected image. Subsequent runs through the pipeline (i.e. for
% image set 2 through the end) produce no new results, but processing
% is not aborted in case other modules are being run for some reason.
% The projection image calculated the first time through the pipeline
% is still available to other modules during subsequent runs through
% the pipeline.
%
% How it works:
% This module works by averaging together all of the images.
%
% SAVING IMAGES: The image produced by this
% module can be easily saved using the Save Images module, using the
% name you assign.
%
% See also CORRECTILLUMDIVIDEALLMEAN.

% CellProfiler is distributed under the GNU General Public License.
% See the accompanying file LICENSE for details.
%
% Developed by the Whitehead Institute for Biomedical Research.
% Copyright 2003,2004,2005.
%
% Authors:
%   Anne Carpenter <carpenter@wi.mit.edu>
%   Thouis Jones   <thouis@csail.mit.edu>
%   In Han Kang    <inthek@mit.edu>
%
% $Revision$

% PROGRAMMING NOTE
% HELP:
% The first unbroken block of lines will be extracted as help by
% CellProfiler's 'Help for this analysis module' button as well as Matlab's
% built in 'help' and 'doc' functions at the command line. It will also be
% used to automatically generate a manual page for the module. An example
% image demonstrating the function of the module can also be saved in tif
% format, using the same name as the module, and it will automatically be
% included in the manual page as well.  Follow the convention of: purpose
% of the module, description of the variables and acceptable range for
% each, how it works (technical description), info on which images can be
% saved, and See also CAPITALLETTEROTHERMODULES. The license/author
% information should be separated from the help lines with a blank line so
% that it does not show up in the help displays.  Do not change the
% programming notes in any modules! These are standard across all modules
% for maintenance purposes, so anything module-specific should be kept
% separate.

% PROGRAMMING NOTE
% DRAWNOW:
% The 'drawnow' function allows figure windows to be updated and
% buttons to be pushed (like the pause, cancel, help, and view
% buttons).  The 'drawnow' function is sprinkled throughout the code
% so there are plenty of breaks where the figure windows/buttons can
% be interacted with.  This does theoretically slow the computation
% somewhat, so it might be reasonable to remove most of these lines
% when running jobs on a cluster where speed is important.
drawnow

%%%%%%%%%%%%%%%%
%%% VARIABLES %%%
%%%%%%%%%%%%%%%%
drawnow

% PROGRAMMING NOTE
% VARIABLE BOXES AND TEXT:
% The '%textVAR' lines contain the variable descriptions which are
% displayed in the CellProfiler main window next to each variable box.
% This text will wrap appropriately so it can be as long as desired.
% The '%defaultVAR' lines contain the default values which are
% displayed in the variable boxes when the user loads the module.
% The line of code after the textVAR and defaultVAR extracts the value
% that the user has entered from the handles structure and saves it as
% a variable in the workspace of this module with a descriptive
% name. The syntax is important for the %textVAR and %defaultVAR
% lines: be sure there is a space before and after the equals sign and
% also that the capitalization is as shown.
% CellProfiler uses VariableRevisionNumbers to help programmers notify
% users when something significant has changed about the variables.
% For example, if you have switched the position of two variables,
% loading a pipeline made with the old version of the module will not
% behave as expected when using the new version of the module, because
% the settings (variables) will be mixed up. The line should use this
% syntax, with a two digit number for the VariableRevisionNumber:
% '%%%VariableRevisionNumber = 01'  If the module does not have this
% line, the VariableRevisionNumber is assumed to be 00.  This number
% need only be incremented when a change made to the modules will affect
% a user's previously saved settings. There is a revision number at
% the end of the license info at the top of the m-file for revisions
% that do not affect the user's previously saved settings files.

%%% Reads the current module number, because this is needed to find
%%% the variable values that the user entered.
CurrentModule = handles.Current.CurrentModuleNumber;
CurrentModuleNum = str2double(CurrentModule);

%textVAR01 = What did you call the images to be averaged to make the projection?
%defaultVAR01 = OrigBlue
ImageName = char(handles.Settings.VariableValues{CurrentModuleNum,1});

%textVAR02 = What do you want to call the resulting projection image?
%defaultVAR02 = ProjectedBlue
ProjectedImageName = char(handles.Settings.VariableValues{CurrentModuleNum,2});

%textVAR03 = Are the images you want to use to make the projection to be loaded straight from a Load Images module (L), or are they being produced by the pipeline (P)? If you choose L, the module will calculate the single, averaged projection image the first time through the pipeline by loading every image of the type specified in the Load Images module. It is then acceptable to use the resulting image later in the pipeline. If you choose P, the module will allow the pipeline to cycle through all of the image sets.  With this option, the module does not need to follow a Load Images module; it is acceptable to make the single, averaged projection from images resulting from other image processing steps in the pipeline. However, the resulting projection image will not be available until the last image set has been processed, so it cannot be used in subsequent modules.
%defaultVAR03 = L
SourceIsLoadedOrPipeline = char(handles.Settings.VariableValues{CurrentModuleNum,3});

%textVAR04 = If the incoming images are binary and you want to dilate each object in the final projection image, enter the radius (roughly equal to the original radius of the objects). Otherwise, enter 0. Note that if you are using a small image set, there will be spaces in the projection image that contain no objects and median filtering is unlikely to work well. 
%defaultVAR04 = 0
DilateObjects = char(handles.Settings.VariableValues{CurrentModuleNum,4});

%%%VariableRevisionNumber = 2

%%%%%%%%%%%%%%%%%%%%%
%%% IMAGE ANALYSIS %%%
%%%%%%%%%%%%%%%%%%%%%
drawnow

% PROGRAMMING NOTE
% TO TEMPORARILY SHOW IMAGES DURING DEBUGGING:
% figure, imshow(BlurredImage, []), title('BlurredImage')
% TO TEMPORARILY SAVE IMAGES DURING DEBUGGING:
% imwrite(BlurredImage, FileName, FileFormat);
% Note that you may have to alter the format of the image before
% saving.  If the image is not saved correctly, for example, try
% adding the uint8 command:
% imwrite(uint8(BlurredImage), FileName, FileFormat);
% To routinely save images produced by this module, see the help in
% the SaveImages module.

if strncmpi(SourceIsLoadedOrPipeline, 'L',1) == 1
    if handles.Current.SetBeingAnalyzed == 1
        %%% The first time the module is run, the projection image is calculated.
        %%% Obtains the screen size and determines where the wait bar
        %%% will be displayed.
        ScreenSize = get(0,'ScreenSize');
        ScreenHeight = ScreenSize(4);
        PotentialBottom = [0, (ScreenHeight-720)];
        BottomOfMsgBox = max(PotentialBottom);
        PositionMsgBox = [500 BottomOfMsgBox 350 100];
        %%% Retrieves the path where the images are stored from the handles
        %%% structure.
        fieldname = ['Pathname', ImageName];
        try Pathname = handles.Pipeline.(fieldname);
        catch error('Image processing was canceled because the Make Projection module uses all the images in a set to calculate the projection image. Therefore, the entire image set to be projected must exist prior to processing the first image set through the pipeline. In other words, the Make Projection module must be run straight from a LoadImages module rather than following an image analysis module. One solution is to use the Make Projection module in Pipeline mode (P). Another option is to process the entire batch of images using the image analysis modules preceding this module and save the resulting images to the hard drive, then start a new stage of processing from this Make Projection module onward.')
        end
        %%% Retrieves the list of filenames where the images are stored from the
        %%% handles structure.
        fieldname = ['FileList', ImageName];
        FileList = handles.Pipeline.(fieldname);
        %%% Calculates the projection image.
        %%% Image file is read differently if it is a .dib image.
        TotalImage = CPimread(fullfile(Pathname, char(FileList(1))), handles);
        %%% Does some error checking on the first image in the set.
        %%% Checks that the original image is two-dimensional (i.e. not a color
        %%% image), which would disrupt several of the image functions.
        if ndims(TotalImage) ~= 2
            error('Image processing was canceled because the Make Projection module requires input images that are two-dimensional (i.e. X vs Y), but the first image loaded does not fit this requirement.  This may be because the image is a color image.')
        end
        %%% Waitbar shows the percentage of image sets remaining.
        WaitbarHandle = waitbar(0,'');
        set(WaitbarHandle, 'Position', PositionMsgBox)
        drawnow
        TimeStart = clock;
        NumberOfImages = length(FileList);
        for i=2:length(FileList)
            TotalImage = TotalImage + CPimread(fullfile(Pathname, char(FileList(i))), handles);
            CurrentTime = clock;
            TimeSoFar = etime(CurrentTime,TimeStart);
            TimePerSet = TimeSoFar/i;
            ImagesRemaining = NumberOfImages - i;
            TimeRemaining = round(TimePerSet*ImagesRemaining);
            WaitbarText = {'Calculating the projection image for the Make Projection module.'; ['Seconds remaining: ', num2str(TimeRemaining),]};
            WaitbarText = char(WaitbarText);
            waitbar(i/NumberOfImages, WaitbarHandle, WaitbarText)
            drawnow
        end
        if length(FileList) == 1
            CurrentTime = clock;
            TimeSoFar = etime(CurrentTime,TimeStart);
        end
        WaitbarText = {'Calculations of the projection image are finished for the Make Projection module.';['Seconds consumed: ',num2str(TimeSoFar),]};
        WaitbarText = char(WaitbarText);
        waitbar(i/NumberOfImages, WaitbarHandle, WaitbarText)
        ProjectedImage = TotalImage / length(FileList);
    end
    %%% Indicate that the projection image is ready.
    ReadyFlag = 'ProjectedImageReady';

elseif strncmpi(SourceIsLoadedOrPipeline, 'P',1) == 1
    %%% In Pipeline (cycling) mode, each time through the image sets, the
    %%% image is added to the existing cumulative image.
    %%% Reads (opens) the image you want to analyze and assigns it to a
    %%% variable.
    fieldname = ['', ImageName];
    %%% Performs certain error-checking and initializing functions the
    %%% first time throught the image set.
    if handles.Current.SetBeingAnalyzed == 1
        %%% Checks whether the image to be analyzed exists in the handles structure.
        if isfield(handles.Pipeline, ImageName)==0,
            %%% If the image is not there, an error message is produced.  The error
            %%% is not displayed: The error function halts the current function and
            %%% returns control to the calling function (the analyze all images
            %%% button callback.)  That callback recognizes that an error was
            %%% produced because of its try/catch loop and breaks out of the image
            %%% analysis loop without attempting further modules.
            error(['Image processing was canceled because the Make Projection module could not find the input image.  It was supposed to be named ', ImageName, ' but an image with that name does not exist.  Perhaps there is a typo in the name.'])
        end
        %%% Retrieves the current image.
        OrigImage = handles.Pipeline.(fieldname);
        %%% Creates the empty variable so it can be retrieved later without
        %%% causing an error on the first image set.
        handles.Pipeline.(ProjectedImageName) = zeros(size(OrigImage));
    end
    %%% Retrieves the current image.
    OrigImage = handles.Pipeline.(fieldname);
    %%% Checks that the original image is two-dimensional (i.e. not a color
    %%% image), which would disrupt several of the image functions.
    if ndims(OrigImage) ~= 2
        error('Image processing was canceled because the Make Projection module requires an input image that is two-dimensional (i.e. X vs Y), but the image loaded does not fit this requirement.  This may be because the image is a color image.')
    end
    %%% Retrieves the existing projection image, as accumulated so far.
    ProjectedImage = handles.Pipeline.(ProjectedImageName);
    %%% Adds the current image to it.
    ProjectedImage = ProjectedImage + OrigImage;
    %%% If the last image set has just been processed, indicate that the
    %%% projection image is ready.
    if handles.Current.SetBeingAnalyzed == handles.Current.NumberOfImageSets
	%%% Divides by the total number of images in order to average.
	ProjectedImage = ProjectedImage/handles.Current.NumberOfImageSets;
        ReadyFlag = 'ProjectedImageReady';
        %%% The following line is somewhat temporary so we can retrieve
        %%% this image if necessary (pre-dilation).
 	FinalRawProjectedImage = ProjectedImage;
    else ReadyFlag = 'ProjectedImageNotReady';
    end
else
    error('Image processing was canceled because you must choose either "L" or "P" in the Make Projection module');
end

%%% Dilates the objects if the user requested.
if strcmp(ReadyFlag, 'ProjectedImageReady') == 1
    %%% This filter acts as if we had dilated each object by a certain
    %%% number of pixels prior to making the projection. It is faster
    %%% to do this convolution when the entire projection is completed
    %%% rather than dilating each object as each image is processed.
    try NumericalDilateObjects = str2num(DilateObjects);
    catch error('In the Make Projection module, you must enter a number for the radius to use to dilate objects. If you do not want to dilate objects enter 0 (zero).')
    end
    if  NumericalDilateObjects ~= 0
%        LogicalStructuringElement = getnhood(strel('disk',NumericalDilateObjects,0));
        StructuringElement = fspecial('gaussian',3*NumericalDilateObjects,NumericalDilateObjects);
        ProjectedImage = filter2(StructuringElement,ProjectedImage,'same');
    end
end

%%%%%%%%%%%%%%%%%%%%%%
%%% DISPLAY RESULTS %%%
%%%%%%%%%%%%%%%%%%%%%%
drawnow

% PROGRAMMING NOTE
% DISPLAYING RESULTS:
% Some calculations produce images that are used only for display or
% for saving to the hard drive, and are not used by downstream
% modules. To speed processing, these calculations are omitted if the
% figure window is closed and the user does not want to save the
% images.
fieldname = ['FigureNumberForModule',CurrentModule];
ThisModuleFigureNumber = handles.Current.(fieldname);
if any(findobj == ThisModuleFigureNumber) == 1;
    % PROGRAMMING NOTE
    % DRAWNOW BEFORE FIGURE COMMAND:
    % The "drawnow" function executes any pending figure window-related
    % commands.  In general, Matlab does not update figure windows until
    % breaks between image analysis modules, or when a few select commands
    % are used. "figure" and "drawnow" are two of the commands that allow
    % Matlab to pause and carry out any pending figure window- related
    % commands (like zooming, or pressing timer pause or cancel buttons or
    % pressing a help button.)  If the drawnow command is not used
    % immediately prior to the figure(ThisModuleFigureNumber) line, then
    % immediately after the figure line executes, the other commands that
    % have been waiting are executed in the other windows.  Then, when
    % Matlab returns to this module and goes to the subplot line, the
    % figure which is active is not necessarily the correct one. This
    % results in strange things like the subplots appearing in the timer
    % window or in the wrong figure window, or in help dialog boxes.
    %%% Sets the width of the figure window to be appropriate (half width and height),
    %%% the first time through the set.
    if handles.Current.SetBeingAnalyzed == handles.Current.StartingImageSet
        originalsize = get(ThisModuleFigureNumber, 'position');
        newsize = originalsize;
        newsize(2) = originalsize(2) + originalsize(4)/2;
        newsize(3) = originalsize(3)/2;
        newsize(4) = originalsize(4)/2;
        set(ThisModuleFigureNumber, 'position', newsize);
        drawnow
    end
    if strncmpi(SourceIsLoadedOrPipeline, 'L',1) == 1
        if handles.Current.SetBeingAnalyzed == handles.Current.StartingImageSet
            %%% The projection image is displayed the first time through
            %%% the set. For subsequent image sets, this figure is not
            %%% updated at all, to prevent the need to load the projection
            %%% image from the handles structure.
            %%% Activates the appropriate figure window.
            figure(ThisModuleFigureNumber);
            imagesc(ProjectedImage);
            title(['Final Projection Image, based on all ', num2str(NumberOfImages), ' images']);
            colormap(gray)
        end
    elseif strncmpi(SourceIsLoadedOrPipeline, 'P',1) == 1
        %%% The accumulated projection image so far is displayed each time through
        %%% the pipeline.
        %%% Activates the appropriate figure window.
        figure(ThisModuleFigureNumber);
        imagesc(ProjectedImage);
        title(['Projection Image so far, based on Image set # 1 - ', num2str(handles.Current.SetBeingAnalyzed)]);
        colormap(gray)
    end
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%% SAVE DATA TO HANDLES STRUCTURE %%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
drawnow

% PROGRAMMING NOTE
% HANDLES STRUCTURE:
%       In CellProfiler (and Matlab in general), each independent
% function (module) has its own workspace and is not able to 'see'
% variables produced by other modules. For data or images to be shared
% from one module to the next, they must be saved to what is called
% the 'handles structure'. This is a variable, whose class is
% 'structure', and whose name is handles. The contents of the handles
% structure are printed out at the command line of Matlab using the
% Tech Diagnosis button. The only variables present in the main
% handles structure are handles to figures and gui elements.
% Everything else should be saved in one of the following
% substructures:
%
% handles.Settings:
%       Everything in handles.Settings is stored when the user uses
% the Save pipeline button, and these data are loaded into
% CellProfiler when the user uses the Load pipeline button. This
% substructure contains all necessary information to re-create a
% pipeline, including which modules were used (including variable
% revision numbers), their setting (variables), and the pixel size.
%   Fields currently in handles.Settings: PixelSize, ModuleNames,
% VariableValues, NumbersOfVariables, VariableRevisionNumbers.
%
% handles.Pipeline:
%       This substructure is deleted at the beginning of the
% analysis run (see 'Which substructures are deleted prior to an
% analysis run?' below). handles.Pipeline is for storing data which
% must be retrieved by other modules. This data can be overwritten as
% each image set is processed, or it can be generated once and then
% retrieved during every subsequent image set's processing, or it can
% be saved for each image set by saving it according to which image
% set is being analyzed, depending on how it will be used by other
% modules. Any module which produces or passes on an image needs to
% also pass along the original filename of the image, named after the
% new image name, so that if the SaveImages module attempts to save
% the resulting image, it can be named by appending text to the
% original file name.
%   Example fields in handles.Pipeline: FileListOrigBlue,
% PathnameOrigBlue, FilenameOrigBlue, OrigBlue (which contains the actual image).
%
% handles.Current:
%       This substructure contains information needed for the main
% CellProfiler window display and for the various modules to
% function. It does not contain any module-specific data (which is in
% handles.Pipeline).
%   Example fields in handles.Current: NumberOfModules,
% StartupDirectory, DefaultOutputDirectory, DefaultImageDirectory,
% FilenamesInImageDir, CellProfilerPathname, ImageToolHelp,
% DataToolHelp, FigureNumberForModule01, NumberOfImageSets,
% SetBeingAnalyzed, TimeStarted, CurrentModuleNumber.
%
% handles.Preferences:
%       Everything in handles.Preferences is stored in the file
% CellProfilerPreferences.mat when the user uses the Set Preferences
% button. These preferences are loaded upon launching CellProfiler.
% The PixelSize, DefaultImageDirectory, and DefaultOutputDirectory
% fields can be changed for the current session by the user using edit
% boxes in the main CellProfiler window, which changes their values in
% handles.Current. Therefore, handles.Current is most likely where you
% should retrieve this information if needed within a module.
%   Fields currently in handles.Preferences: PixelSize, FontSize,
% DefaultModuleDirectory, DefaultOutputDirectory,
% DefaultImageDirectory.
%
% handles.Measurements:
%       Everything in handles.Measurements contains data specific to each
% image set analyzed for exporting. It is used by the ExportProjectedImage
% and ExportCellByCell data tools. This substructure is deleted at the
% beginning of the analysis run (see 'Which substructures are deleted
% prior to an analysis run?' below).
%    Note that two types of measurements are typically made: Object
% and Image measurements.  Object measurements have one number for
% every object in the image (e.g. ObjectArea) and image measurements
% have one number for the entire image, which could come from one
% measurement from the entire image (e.g. ImageTotalIntensity), or
% which could be an aggregate measurement based on individual object
% measurements (e.g. ImageMeanArea).  Use the appropriate prefix to
% ensure that your data will be extracted properly. It is likely that
% Subobject will become a new prefix, when measurements will be
% collected for objects contained within other objects.
%       Saving measurements: The data extraction functions of
% CellProfiler are designed to deal with only one "column" of data per
% named measurement field. So, for example, instead of creating a
% field of XY locations stored in pairs, they should be split into a
% field of X locations and a field of Y locations. It is wise to
% include the user's input for 'ObjectName' or 'ImageName' as part of
% the fieldname in the handles structure so that multiple modules can
% be run and their data will not overwrite each other.
%   Example fields in handles.Measurements: ImageCountNuclei,
% ObjectAreaCytoplasm, FilenameOrigBlue, PathnameOrigBlue,
% TimeElapsed.
%
% Which substructures are deleted prior to an analysis run?
%       Anything stored in handles.Measurements or handles.Pipeline
% will be deleted at the beginning of the analysis run, whereas
% anything stored in handles.Settings, handles.Preferences, and
% handles.Current will be retained from one analysis to the next. It
% is important to think about which of these data should be deleted at
% the end of an analysis run because of the way Matlab saves
% variables: For example, a user might process 12 image sets of nuclei
% which results in a set of 12 measurements ("ImageTotalNucArea")
% stored in handles.Measurements. In addition, a processed image of
% nuclei from the last image set is left in the handles structure
% ("SegmNucImg"). Now, if the user uses a different module which
% happens to have the same measurement output name "ImageTotalNucArea"
% to analyze 4 image sets, the 4 measurements will overwrite the first
% 4 measurements of the previous analysis, but the remaining 8
% measurements will still be present. So, the user will end up with 12
% measurements from the 4 sets. Another potential problem is that if,
% in the second analysis run, the user runs only a module which
% depends on the output "SegmNucImg" but does not run a module that
% produces an image by that name, the module will run just fine: it
% will just repeatedly use the processed image of nuclei leftover from
% the last image set, which was left in handles.Pipeline.

%%% If running in non-cycling mode (straight from LoadImages), the
%%% projection image and its flag need only be saved to the handles
%%% structure after the first image set is processed.
if strncmpi(SourceIsLoadedOrPipeline, 'L',1) == 1
    if handles.Current.SetBeingAnalyzed == 1
        %%% Saves the projected image to the handles structure so it can be used by
        %%% subsequent modules.
        handles.Pipeline.(ProjectedImageName) = ProjectedImage;
        %%% Saves the ready flag to the handles structure so it can be used by
        %%% subsequent modules.
        fieldname = [ProjectedImageName,'ReadyFlag'];
        handles.Pipeline.(fieldname) = ReadyFlag;
    end
    %%% If running in cycling mode (Pipeline mode), the projection image and
    %%% its flag are saved to the handles structure after every image set is
    %%% processed.
elseif strncmpi(SourceIsLoadedOrPipeline, 'P',1) == 1
    %%% Saves the projected image to the handles structure so it can be used by
    %%% subsequent modules.
    handles.Pipeline.(ProjectedImageName) = ProjectedImage;
    if strcmp(ReadyFlag, 'ProjectedImageReady') == 1
        %%% This is somewhat temporary, so we can retrieve the image for
        %%% diagnostic purposes.
        handles.Pipeline.(['Raw',ProjectedImageName]) = FinalRawProjectedImage;
    end
    %%% Saves the ready flag to the handles structure so it can be used by
    %%% subsequent modules.
    fieldname = [ProjectedImageName,'ReadyFlag'];
    handles.Pipeline.(fieldname) = ReadyFlag;
end