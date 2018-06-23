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


