"""
Perform the image-based profiling pipeline to process data
"""
# copied from
# https://github.com/broadinstitute/profiling-resistance-mechanisms/blob/master/0.generate-profiles/scripts/profile_util.py

import os
import pathlib
from profile_utils import process_pipeline
import pandas as pd
import numpy as np
from pycytominer.cyto_utils.cells import SingleCells
from pycytominer import (
    annotate,
    normalize,
    feature_select,
    cyto_utils,
)


def process_profile(batch, plate, pipeline):
    # Set output directory information
    pipeline_output = pipeline["output_dir"]
    compartments = list(pipeline["compartments"].split(","))
    output_dir = pathlib.PurePath(".", pipeline_output, batch, plate)

    # Set output file information
    aggregate_out_file = pathlib.PurePath(output_dir, f"{plate}.csv.gz")
    aggregate_output_file = pathlib.PurePath(output_dir, f"{plate}.csv.gz")
    annotate_output_file = pathlib.PurePath(output_dir, f"{plate}_augmented.csv.gz")
    normalize_output_file = pathlib.PurePath(output_dir, f"{plate}_normalized.csv.gz")
    normalize_output_negcon_file = pathlib.PurePath(
        output_dir, f"{plate}_normalized_negcon.csv.gz"
    )
    feature_output_file = pathlib.PurePath(
        output_dir, f"{plate}_normalized_feature_select.csv.gz"
    )
    feature_output_negcon_file = pathlib.PurePath(
        output_dir, f"{plate}_normalized_feature_select_negcon.csv.gz"
    )

    # Load pipeline options
    compression = process_pipeline(pipeline["options"], option="compression")
    float_format = process_pipeline(pipeline["options"], option="float_format")
    samples = process_pipeline(pipeline["options"], option="samples")

    # Check for noncanonical compartments
    canonical_compartments = ["cells", "cytoplasm", "nuclei"]
    noncanonical = False
    noncanonical_compartments = []

    if not all(np.isin(compartments, canonical_compartments)):
        noncanonical_compartments = list(
            np.asarray(compartments)[~np.isin(compartments, canonical_compartments)]
        )
        noncanonical = True

    # Aggregate Profiles

    aggregate_steps = pipeline["aggregate"]

    if aggregate_steps["perform"]:
        aggregate_args = {
            "features": aggregate_steps["features"],
            "operation": aggregate_steps["method"],
        }

        linking_columns = {
            "cytoplasm": {
                "cells": "Cytoplasm_Parent_Cells",
                "nuclei": "Cytoplasm_Parent_Nuclei",
            },
            "cells": {"cytoplasm": "ObjectNumber"},
            "nuclei": {"cytoplasm": "ObjectNumber"},
        }

        aggregate_fields = "all"

        aggregate_plate_column = aggregate_steps["plate_column"]
        aggregate_well_column = aggregate_steps["well_column"]

        sql_file = f'sqlite:////{os.path.abspath(os.path.join("../../backend", batch, plate, f"{plate}.sqlite"))}'

        strata = [aggregate_plate_column, aggregate_well_column]

        if "fields" in aggregate_steps:
            aggregate_fields = aggregate_steps["fields"]
            aggregate_fields = list(map(int, aggregate_fields.split(",")))

        if "site_column" in aggregate_steps:
            aggregate_site_column = aggregate_steps["site_column"]
            strata += [aggregate_site_column]

        if noncanonical:
            for comp in noncanonical_compartments:
                linking_columns[comp] = {"cytoplasm": "ObjectNumber"}
                linking_columns["cytoplasm"][
                    comp
                ] = f"Cytoplasm_Parent_{comp.capitalize()}"  # This will not work if the feature name uses CamelCase.

        if "object_feature" in aggregate_steps:
            object_feature = aggregate_steps["object_feature"]
        else:
            object_feature = "ObjectNumber"

        ap = SingleCells(
            sql_file,
            strata=strata,
            compartments=compartments,
            compartment_linking_cols=linking_columns,
            fields_of_view=aggregate_fields,
            object_feature=object_feature,
        )

        ap.aggregate_profiles(
            output_file=aggregate_out_file,
            compression_options=compression,
            aggregate_args=aggregate_args,
        )

    # Annotate Profiles
    annotate_steps = pipeline["annotate"]
    annotate_well_column = annotate_steps["well_column"]

    if annotate_steps["perform"]:
        annotate_well_column = annotate_steps["well_column"]

        # Load and setup platemap info
        metadata_dir = pathlib.PurePath(".", "metadata", "platemaps", batch)
        barcode_plate_map_file = pathlib.PurePath(metadata_dir, "barcode_platemap.csv")
        barcode_plate_map_df = pd.read_csv(
            barcode_plate_map_file, dtype={"Assay_Plate_Barcode": str}
        )
        plate_map_name = barcode_plate_map_df.query(
            "Assay_Plate_Barcode == @plate"
        ).Plate_Map_Name.values[0]
        plate_map_file = pathlib.PurePath(
            metadata_dir, "platemap", f"{plate_map_name}.txt"
        )
        plate_map_df = pd.read_csv(plate_map_file, sep="\t")
        plate_map_df.columns = [
            f"Metadata_{x}" if not x.startswith("Metadata_") else x
            for x in plate_map_df.columns
        ]
        platemap_well_column = pipeline["platemap_well_column"]

        if annotate_steps["external"]:
            external_df = pd.read_csv(
                pathlib.PurePath(".", "metadata", "moa", annotate_steps["external"]),
                sep="\t",
            )
            annotate(
                profiles=aggregate_output_file,
                platemap=plate_map_df,
                join_on=[platemap_well_column, annotate_well_column],
                external_metadata=external_df,
                external_join_left=["Metadata_broad_sample"],
                external_join_right=["Metadata_broad_sample"],
                output_file=annotate_output_file,
                float_format=float_format,
                compression_options=compression,
                clean_cellprofiler=True,
            )
        else:
            annotate(
                profiles=aggregate_output_file,
                platemap=plate_map_df,
                join_on=[platemap_well_column, annotate_well_column],
                output_file=annotate_output_file,
                float_format=float_format,
                compression_options=compression,
                clean_cellprofiler=True,
            )

    # Normalize Profiles
    normalize_steps = pipeline["normalize"]
    if normalize_steps["perform"]:
        normalization_features = normalize_steps["features"]
        normalization_method = normalize_steps["method"]

        if normalization_features == "infer" and noncanonical:
            normalization_features = cyto_utils.infer_cp_features(
                pd.read_csv(annotate_output_file), compartments=compartments
            )

        normalize(
            profiles=annotate_output_file,
            features=normalization_features,
            samples=samples,
            method=normalization_method,
            output_file=normalize_output_file,
            float_format=float_format,
            compression_options=compression,
        )
        if normalize_steps["negcon"]:
            normalize(
                profiles=annotate_output_file,
                features=normalization_features,
                samples="Metadata_control_type == 'negcon'",
                method=normalization_method,
                output_file=normalize_output_negcon_file,
                float_format=float_format,
                compression_options=compression,
            )

    # Apply feature selection
    feature_select_steps = pipeline["feature_select"]
    if feature_select_steps["perform"]:
        feature_select_operations = feature_select_steps["operations"]
        feature_select_features = feature_select_steps["features"]

        if feature_select_features == "infer" and noncanonical:
            feature_select_features = cyto_utils.infer_cp_features(
                pd.read_csv(normalize_output_file), compartments=compartments
            )

        feature_select(
            profiles=normalize_output_file,
            features=feature_select_features,
            operation=feature_select_operations,
            output_file=feature_output_file,
            float_format=float_format,
            compression_options=compression,
        )
        if feature_select_steps["negcon"]:
            feature_select(
                profiles=normalize_output_negcon_file,
                features=feature_select_features,
                operation=feature_select_operations,
                output_file=feature_output_negcon_file,
                float_format=float_format,
                compression_options=compression,
            )
