# copied from
# https://github.com/broadinstitute/profiling-resistance-mechanisms/blob/master/0.generate-profiles/scripts/profile_util.py

import yaml
import os
import pathlib
from pycytominer.cyto_utils import get_default_linking_cols
import pandas as pd


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


def create_directories(batch, plate, pipeline):
    pipeline_output = pipeline["output_dir"]
    output_dir = pathlib.PurePath(".", pipeline_output, batch, plate)

    if not os.path.isdir(pathlib.PurePath(".", pipeline_output, batch)):
        os.mkdir(pathlib.PurePath(".", pipeline_output, batch))

    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)


def create_gct_directories(batch):
    output_dir = pathlib.PurePath(".", "gct", batch)

    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)


def create_linking_columns(noncanonical, noncanonical_compartments):
    linking_columns = get_default_linking_cols()

    if noncanonical:
        for comp in noncanonical_compartments:
            linking_columns[comp] = {"cytoplasm": "ObjectNumber"}
            linking_columns["cytoplasm"][
                comp
            ] = f"Cytoplasm_Parent_{comp.capitalize()}"  # This will not work if the feature name uses CamelCase.

    return linking_columns


def get_pipeline_options(pipeline):
    pipeline_options = dict()
    pipeline_options["compression"] = process_pipeline(
        pipeline["options"], option="compression"
    )
    pipeline_options["float_format"] = process_pipeline(
        pipeline["options"], option="float_format"
    )
    pipeline_options["sample"] = process_pipeline(pipeline["options"], option="samples")

    return pipeline_options


def concat_dataframes(main_df, df):
    if main_df.shape[0] == 0:
        main_df = df.copy()
    else:
        frame = [main_df, df]
        main_df = pd.concat(frame, ignore_index=True)

    return main_df
