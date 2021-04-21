# copied from
# https://github.com/broadinstitute/profiling-resistance-mechanisms/blob/master/0.generate-profiles/scripts/profile_util.py

import yaml


def load_pipeline(config_file):
    profile_config = {}
    with open(config_file, "r") as stream:
        for data in yaml.load_all(stream, Loader=yaml.FullLoader):
            if "pipeline" in data.keys():
                pipeline = data
            else:
                process = data["process"]
                if not process:
                    continue
                batch = data["batch"]
                plates = [str(x["name"]) for x in data["plates"] if x["process"]]
                profile_config[batch] = plates

    return pipeline, profile_config


def process_pipeline(pipeline, option):
    if option == "compression":
        if option in pipeline.keys():
            output = pipeline["compression"]
        else:
            output = "None"

    if option == "samples":
        if option in pipeline.keys():
            output = pipeline["samples"]
        else:
            output = "all"

    if option == "float_format":
        if option in pipeline.keys():
            output = pipeline["float_format"]
        else:
            output = None

    return output
