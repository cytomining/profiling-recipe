"""
Perform the image-based profiling pipeline to process data
"""
# modified from
# https://github.com/broadinstitute/profiling-resistance-mechanisms/blob/master/0.generate-profiles/scripts/profile_util.py

import os
import pathlib
from utils import (
    create_linking_columns,
    get_pipeline_options,
    concat_dataframes,
)
import pandas as pd
import numpy as np
from pycytominer.cyto_utils.cells import SingleCells
from pycytominer.cyto_utils import get_default_compartments
from pycytominer import (
    annotate,
    normalize,
    feature_select,
    cyto_utils,
)


class RunPipeline(object):
    def __init__(self, pipeline, profile_config):
        self.pipeline = pipeline
        self.profile_config = profile_config
        self.pipeline_options = get_pipeline_options(pipeline=self.pipeline)

        self.pipeline_output = self.pipeline["output_dir"]
        self.output_dir = pathlib.PurePath(".", self.pipeline_output)

        # Check for noncanonical compartments
        self.compartments = list(pipeline["compartments"].split(","))
        canonical_compartments = get_default_compartments()
        self.noncanonical = False
        self.noncanonical_compartments = []

        if not all(np.isin(self.compartments, canonical_compartments)):
            self.noncanonical_compartments = list(
                np.asarray(self.compartments)[
                    ~np.isin(self.compartments, canonical_compartments)
                ]
            )
            self.noncanonical = True

    def pipeline_aggregate(self, batch, plate):
        aggregate_steps = self.pipeline["aggregate"]
        output_dir = pathlib.PurePath(".", self.pipeline_output, batch, plate)
        aggregate_output_file = pathlib.PurePath(output_dir, f"{plate}.csv.gz")

        linking_columns = create_linking_columns(
            self.noncanonical, self.noncanonical_compartments
        )

        aggregate_args = {
            "features": aggregate_steps["features"],
            "operation": aggregate_steps["method"],
        }

        aggregate_plate_column = aggregate_steps["plate_column"]
        aggregate_well_column = aggregate_steps["well_column"]
        strata = [aggregate_plate_column, aggregate_well_column]
        sql_file = f'sqlite:////{os.path.abspath(os.path.join("../../backend", batch, plate, f"{plate}.sqlite"))}'

        if "fields" in aggregate_steps:
            aggregate_fields = aggregate_steps["fields"]
            if type(aggregate_fields) == int:
                aggregate_fields = [aggregate_fields]
            else:
                aggregate_fields = list(map(int, aggregate_fields.split(",")))
        else:
            aggregate_fields = "all"

        if "site_column" in aggregate_steps:
            aggregate_site_column = aggregate_steps["site_column"]
            strata += [aggregate_site_column]

        if "object_feature" in aggregate_steps:
            object_feature = aggregate_steps["object_feature"]
        else:
            object_feature = "Metadata_ObjectNumber"

        ap = SingleCells(
            sql_file,
            strata=strata,
            compartments=self.compartments,
            compartment_linking_cols=linking_columns,
            fields_of_view=aggregate_fields,
            object_feature=object_feature,
        )

        ap.aggregate_profiles(
            output_file=aggregate_output_file,
            compression_options=self.pipeline_options["compression"],
            float_format=self.pipeline_options["float_format"],
            aggregate_args=aggregate_args,
        )

    def pipeline_annotate(self, batch, plate):
        annotate_steps = self.pipeline["annotate"]
        output_dir = pathlib.PurePath(".", self.pipeline_output, batch, plate)
        aggregate_output_file = pathlib.PurePath(output_dir, f"{plate}.csv.gz")
        annotate_output_file = pathlib.PurePath(output_dir, f"{plate}_augmented.csv.gz")

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

        platemap_well_column = self.pipeline["platemap_well_column"]
        annotate_well_column = annotate_steps["well_column"]

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
                compression_options=self.pipeline_options["compression"],
                float_format=self.pipeline_options["float_format"],
                clean_cellprofiler=True,
            )
        else:
            annotate(
                profiles=aggregate_output_file,
                platemap=plate_map_df,
                join_on=[platemap_well_column, annotate_well_column],
                output_file=annotate_output_file,
                compression_options=self.pipeline_options["compression"],
                float_format=self.pipeline_options["float_format"],
                clean_cellprofiler=True,
            )

    def pipeline_normalize(self, batch, plate, steps, samples, suffix=None):
        normalize_steps = steps
        output_dir = pathlib.PurePath(".", self.pipeline_output, batch, plate)
        annotate_output_file = pathlib.PurePath(output_dir, f"{plate}_augmented.csv.gz")
        normalize_output_file = pathlib.PurePath(
            output_dir, f"{plate}_normalized.csv.gz"
        )
        if suffix:
            normalize_output_file = pathlib.PurePath(
                output_dir, f"{plate}_normalized_{suffix}.csv.gz"
            )

        normalization_features = normalize_steps["features"]
        normalization_method = normalize_steps["method"]

        if normalization_features == "infer" and self.noncanonical:
            normalization_features = cyto_utils.infer_cp_features(
                pd.read_csv(annotate_output_file), compartments=self.compartments
            )

        normalize(
            profiles=annotate_output_file,
            features=normalization_features,
            samples=samples,
            method=normalization_method,
            output_file=normalize_output_file,
            compression_options=self.pipeline_options["compression"],
            float_format=self.pipeline_options["float_format"],
        )

    def pipeline_feature_select(self, steps, suffix=None):
        feature_select_steps = steps
        pipeline_output = self.pipeline["output_dir"]

        level = feature_select_steps["level"]
        feature_select_operations = feature_select_steps["operations"]
        feature_select_features = feature_select_steps["features"]

        all_plates_df = pd.DataFrame()

        for batch in self.profile_config:
            batch_df = pd.DataFrame()
            for plate in self.profile_config[batch]:
                output_dir = pathlib.PurePath(".", pipeline_output, batch, plate)
                if suffix:
                    normalize_output_file = pathlib.PurePath(
                        output_dir, f"{plate}_normalized_{suffix}.csv.gz"
                    )
                    feature_select_output_file_plate = pathlib.PurePath(
                        output_dir,
                        f"{plate}_normalized_feature_select_{suffix}_plate.csv.gz",
                    )
                else:
                    normalize_output_file = pathlib.PurePath(
                        output_dir, f"{plate}_normalized.csv.gz"
                    )
                    feature_select_output_file_plate = pathlib.PurePath(
                        output_dir, f"{plate}_normalized_feature_select_plate.csv.gz"
                    )
                if feature_select_features == "infer" and self.noncanonical:
                    feature_select_features = cyto_utils.infer_cp_features(
                        pd.read_csv(normalize_output_file),
                        compartments=self.compartments,
                    )

                df = (
                    pd.read_csv(normalize_output_file)
                    .assign(Metadata_batch=batch)
                    )

                if level == "plate":
                    df = df.drop(columns=["Metadata_batch"])
                    feature_select(
                        profiles=df,
                        features=feature_select_features,
                        operation=feature_select_operations,
                        output_file=feature_select_output_file_plate,
                        compression_options=self.pipeline_options["compression"],
                        float_format=self.pipeline_options["float_format"],
                    )
                elif level == "batch":
                    batch_df = concat_dataframes(batch_df, df)
                elif level == "all":
                    all_plates_df = concat_dataframes(all_plates_df, df)

            if level == "batch":
                fs_df = feature_select(
                    profiles=batch_df,
                    features=feature_select_features,
                    operation=feature_select_operations,
                )
                for plate in self.profile_config[batch]:
                    output_dir = pathlib.PurePath(".", pipeline_output, batch, plate)
                    if suffix:
                        feature_select_output_file_batch = pathlib.PurePath(
                            output_dir,
                            f"{plate}_normalized_feature_select_{suffix}_batch.csv.gz",
                        )
                    else:
                        feature_select_output_file_batch = pathlib.PurePath(
                            output_dir,
                            f"{plate}_normalized_feature_select_batch.csv.gz",
                        )
                    if feature_select_features == "infer" and self.noncanonical:
                        feature_select_features = cyto_utils.infer_cp_features(
                            batch_df, compartments=self.compartments
                        )

                    df = fs_df.query("Metadata_Plate==@plate").reset_index(drop=True)
                    df = df.drop(columns=["Metadata_batch"])

                    cyto_utils.output(
                        output_filename=feature_select_output_file_batch,
                        df=df,
                        compression_options=self.pipeline_options["compression"],
                        float_format=self.pipeline_options["float_format"],
                    )

        if level == "all":
            fs_df = feature_select(
                profiles=all_plates_df,
                features=feature_select_features,
                operation=feature_select_operations,
            )
            for batch in self.profile_config:
                for plate in self.profile_config[batch]:
                    output_dir = pathlib.PurePath(".", pipeline_output, batch, plate)
                    if suffix:
                        feature_select_output_file_all = pathlib.PurePath(
                            output_dir,
                            f"{plate}_normalized_feature_select_{suffix}_all.csv.gz",
                        )
                    else:
                        feature_select_output_file_all = pathlib.PurePath(
                            output_dir, f"{plate}_normalized_feature_select_all.csv.gz"
                        )
                    if feature_select_features == "infer" and self.noncanonical:
                        feature_select_features = cyto_utils.infer_cp_features(
                            all_plates_df, compartments=self.compartments
                        )

                    df = (
                        fs_df.loc[fs_df.Metadata_batch == batch]
                        .query("Metadata_Plate==@plate")
                        .reset_index(drop=True)
                    )

                    df = df.drop(columns=["Metadata_batch"])

                    cyto_utils.output(
                        output_filename=feature_select_output_file_all,
                        df=df,
                        compression_options=self.pipeline_options["compression"],
                        float_format=self.pipeline_options["float_format"],
                    )
