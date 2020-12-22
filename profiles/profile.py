"""
Perform the image-based profiling pipeline to process data
"""
# copied from
# https://github.com/broadinstitute/profiling-resistance-mechanisms/blob/master/0.generate-profiles/scripts/profile_util.py

import pathlib
from profile_utils import process_pipeline
import pandas as pd
from pycytominer import (
    annotate,
    normalize,
    feature_select,
    cyto_utils,
)


def process_profile(batch, plate, cell, pipeline):
    # Set output directory information
    pipeline_output = pipeline["output_dir"]
    output_dir = pathlib.PurePath(".", pipeline_output, batch, plate)

    # Set output file information
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

    # Load and setup platemap info
    metadata_dir = pathlib.PurePath(".", "metadata", "platemaps", batch)
    barcode_plate_map_file = pathlib.PurePath(metadata_dir, "barcode_platemap.csv")
    barcode_plate_map_df = pd.read_csv(
        barcode_plate_map_file, dtype={"Assay_Plate_Barcode": str}
    )
    plate_map_name = barcode_plate_map_df.query(
        "Assay_Plate_Barcode == @plate"
    ).Plate_Map_Name.values[0]
    plate_map_file = pathlib.PurePath(metadata_dir, "platemap", f"{plate_map_name}.txt")
    plate_map_df = pd.read_csv(plate_map_file, sep="\t")
    plate_map_df.columns = [
        f"Metadata_{x}" if not x.startswith("Metadata_") else x
        for x in plate_map_df.columns
    ]
    platemap_well_column = pipeline["platemap_well_column"]

    # Annotate Profiles
    annotate_steps = pipeline["annotate"]
    annotate_well_column = annotate_steps["well_column"]
    if annotate_steps["perform"]:
        if annotate_steps["external"]:
            external_df = pd.read_csv(
                pathlib.PurePath(".", "metadata", "moa", annotate_steps["external"]),
                sep="\t",
            )
            anno_df = annotate(
                profiles=aggregate_output_file,
                platemap=plate_map_df,
                join_on=[platemap_well_column, annotate_well_column],
                cell_id=cell,
                external_metadata=external_df,
                external_join_left=["Metadata_broad_sample"],
                external_join_right=["Metadata_broad_sample"],
            )
        else:
            anno_df = annotate(
                profiles=aggregate_output_file,
                platemap=plate_map_df,
                join_on=[platemap_well_column, annotate_well_column],
                cell_id=cell,
            )

    anno_df = anno_df.rename(
        {
            "Image_Metadata_Plate": "Metadata_Plate",
            "Image_Metadata_Well": "Metadata_Well",
        },
        axis="columns",
    ).assign(
        Metadata_Assay_Plate_Barcode=plate,
        Metadata_Plate_Map_Name=barcode_plate_map_df.loc[
            barcode_plate_map_df.Assay_Plate_Barcode == plate, "Plate_Map_Name"
        ].values[0],
    )

    # Reoroder columns
    metadata_cols = cyto_utils.infer_cp_features(anno_df, metadata=True)
    cp_cols = cyto_utils.infer_cp_features(anno_df)
    reindex_cols = metadata_cols + cp_cols
    anno_df = anno_df.reindex(reindex_cols, axis="columns")

    # Output annotated file
    cyto_utils.output(
        df=anno_df,
        output_filename=annotate_output_file,
        float_format=float_format,
        compression=compression,
    )

    # Normalize Profiles
    normalize_steps = pipeline["normalize"]
    normalization_features = normalize_steps["features"]
    normalization_method = normalize_steps["method"]
    if normalize_steps["perform"]:
        normalize(
            profiles=annotate_output_file,
            features=normalization_features,
            samples=samples,
            method=normalization_method,
            output_file=normalize_output_file,
            float_format=float_format,
            compression=compression,
        )
    if normalize_steps["negcon"]:
        normalize(
            profiles=annotate_output_file,
            features=normalization_features,
            samples="Metadata_control_type == 'negcon'",
            method=normalization_method,
            output_file=normalize_output_negcon_file,
            float_format=float_format,
            compression=compression,
        )

    # Apply feature selection
    feature_select_steps = pipeline["feature_select"]
    feature_select_operations = feature_select_steps["operations"]
    feature_select_features = feature_select_steps["features"]
    if feature_select_steps["perform"]:
        feature_select(
            profiles=normalize_output_file,
            features=feature_select_features,
            operation=feature_select_operations,
            output_file=feature_output_file,
            float_format=float_format,
            compression=compression,
        )
    if feature_select_steps["negcon"]:
        feature_select(
            profiles=normalize_output_negcon_file,
            features=feature_select_features,
            operation=feature_select_operations,
            output_file=feature_output_negcon_file,
            float_format=float_format,
            compression=compression,
        )
