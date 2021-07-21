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
import plotly.express as px
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
        self.compartments = pipeline["compartments"]
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

        aggregate_plate_column = aggregate_steps["plate_column"]
        aggregate_well_column = aggregate_steps["well_column"]
        strata = [aggregate_plate_column, aggregate_well_column]
        sql_file = f'sqlite:////{os.path.abspath(os.path.join("../../backend", batch, plate, f"{plate}.sqlite"))}'

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
            aggregation_operation=aggregate_steps["method"],
            fields_of_view=aggregate_steps["fields"],
            object_feature=object_feature,
        )

        ap.aggregate_profiles(
            output_file=aggregate_output_file,
            compression_options=self.pipeline_options["compression"],
            float_format=self.pipeline_options["float_format"],
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

        if annotate_steps["external"]["perform"]:
            external_df = pd.read_csv(
                pathlib.PurePath(
                    ".",
                    "metadata",
                    "external_metadata",
                    annotate_steps["external"]["file"],
                ),
                sep="\t",
            )

            if annotate_steps["external"]["merge_column"].startswith("Metadata"):
                external_join_column = [annotate_steps["external"]["merge_column"]]
            else:
                external_join_column = [
                    "Metadata_" + annotate_steps["external"]["merge_column"]
                ]

            annotate(
                profiles=aggregate_output_file,
                platemap=plate_map_df,
                join_on=[platemap_well_column, annotate_well_column],
                external_metadata=external_df,
                external_join_left=external_join_column,
                external_join_right=external_join_column,
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

                df = pd.read_csv(normalize_output_file).assign(Metadata_batch=batch)

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

    def pipeline_quality_control(self, steps):
        quality_control_steps = steps["operations"]
        pipeline_output = self.pipeline["output_dir"]

        summary_column_order = [
            "Batch_Name",
            "Plate_Name",
            "Well_Count",
            "Images_per_site",
            "Sites_per_well_Median",
            "Sites_per_well_mad",
        ]

        qc_dir = pathlib.PurePath(".", "quality_control")
        if not os.path.isdir(pathlib.PurePath(qc_dir)):
            os.mkdir(qc_dir)

        for step in quality_control_steps:
            if step == "summary":
                output_dir = pathlib.PurePath(".", "quality_control", "summary")
                if not os.path.isdir(pathlib.PurePath(output_dir)):
                    os.mkdir(output_dir)
                output_file = pathlib.PurePath(output_dir, "summary.tsv")
                if os.path.isfile(output_file):
                    summary = pd.read_csv(output_file, sep="\t")
                else:
                    summary = pd.DataFrame()
                for batch in self.profile_config:
                    for plate in self.profile_config[batch]:
                        input_file = pathlib.PurePath(
                            ".", "load_data_csv", batch, plate, "load_data.csv.gz"
                        )
                        df = pd.read_csv(input_file).assign(Metadata_batch=batch)

                        site_df = (
                            df.groupby(["Metadata_Row", "Metadata_Col"])
                            .Metadata_Site.count()
                            .reset_index()
                            .Metadata_Site
                        )
                        image_count = len(
                            df.columns[df.columns.str.startswith("FileName")]
                        )

                        summary = summary.append(
                            {
                                "Batch_Name": batch,
                                "Plate_Name": plate,
                                "Well_Count": site_df.count(),
                                "Images_per_site": image_count,
                                "Sites_per_well_Median": site_df.median(),
                                "Sites_per_well_mad": "%.3f" % site_df.mad(),
                            },
                            ignore_index=True,
                        )

                summary["Well_Count"] = summary["Well_Count"].astype(int)
                summary["Images_per_site"] = summary["Images_per_site"].astype(int)
                summary["Sites_per_well_Median"] = summary[
                    "Sites_per_well_Median"
                ].astype(int)

                summary = summary.drop_duplicates(
                    subset=["Batch_Name", "Plate_Name"], keep="last"
                ).sort_values(by=["Batch_Name", "Plate_Name"])

                summary[summary_column_order].to_csv(output_file, sep="\t", index=False)
            elif step == "heatmap":
                output_dir = pathlib.PurePath(".", "quality_control", "heatmap")
                if not os.path.isdir(pathlib.PurePath(output_dir)):
                    os.mkdir(output_dir)
                for batch in self.profile_config:
                    for plate in self.profile_config[batch]:
                        input_file = pathlib.PurePath(
                            ".",
                            pipeline_output,
                            batch,
                            plate,
                            f"{plate}_augmented.csv.gz",
                        )
                        df = (
                            pd.read_csv(input_file)
                            .assign(Metadata_Row=lambda x: x.Metadata_Well.str[0:1])
                            .assign(Metadata_Col=lambda x: x.Metadata_Well.str[1:])
                        )
                        if "Metadata_Object_Count" in df.columns:
                            cell_count_feature = "Metadata_Object_Count"
                        else:
                            cell_count_feature = "Cytoplasm_Number_Object_Number"

                        df = df[["Metadata_Row", "Metadata_Col", cell_count_feature]]
                        df_pivot = df.pivot(
                            "Metadata_Row", "Metadata_Col", cell_count_feature
                        )

                        fig = px.imshow(df_pivot, color_continuous_scale="blues")
                        fig.update_layout(
                            title=f"Plate: {plate}, Feature: {cell_count_feature}",
                            xaxis=dict(title="", side="top"),
                            yaxis=dict(title=""),
                        )
                        fig.update_traces(xgap=1, ygap=1)

                        if not os.path.isdir(pathlib.PurePath(output_dir, batch)):
                            os.mkdir(pathlib.PurePath(output_dir, batch))
                        if not os.path.isdir(
                            pathlib.PurePath(output_dir, batch, plate)
                        ):
                            os.mkdir(pathlib.PurePath(output_dir, batch, plate))

                        output_file = (
                            f"{output_dir}/{batch}/{plate}/{plate}_cell_count.png"
                        )
                        fig.write_image(output_file, width=640, height=480, scale=2)

                        if os.path.isfile(
                            pathlib.PurePath(
                                ".",
                                pipeline_output,
                                batch,
                                plate,
                                f"{plate}_normalized_feature_select_negcon_all.csv.gz",
                            )
                        ):
                            input_file = pathlib.PurePath(
                                ".",
                                pipeline_output,
                                batch,
                                plate,
                                f"{plate}_normalized_feature_select_negcon_all.csv.gz",
                            )
                        elif os.path.isfile(
                            pathlib.PurePath(
                                ".",
                                pipeline_output,
                                batch,
                                plate,
                                f"{plate}_normalized_feature_select_negcon_batch.csv.gz",
                            )
                        ):
                            input_file = pathlib.PurePath(
                                ".",
                                pipeline_output,
                                batch,
                                plate,
                                f"{plate}_normalized_feature_select_negcon_batch.csv.gz",
                            )
                        elif os.path.isfile(
                            pathlib.PurePath(
                                ".",
                                pipeline_output,
                                batch,
                                plate,
                                f"{plate}_normalized_feature_select_negcon_plate.csv.gz",
                            )
                        ):
                            input_file = pathlib.PurePath(
                                ".",
                                pipeline_output,
                                batch,
                                plate,
                                f"{plate}_normalized_feature_select_negcon_plate.csv.gz",
                            )
                        else:
                            continue

                        df = pd.read_csv(input_file)
                        profiles = df[cyto_utils.infer_cp_features(df)]

                        corr_matrix = np.corrcoef(profiles)

                        corr_matrix_df = pd.DataFrame(
                            corr_matrix,
                            columns=list(df.Metadata_Well),
                            index=list(df.Metadata_Well),
                        )

                        fig = px.imshow(
                            corr_matrix_df, color_continuous_scale="BlueRed"
                        )
                        fig.update_layout(
                            title=f"Plate: {plate}, Correlation all vs. all",
                            xaxis=dict(title="Wells"),
                            yaxis=dict(title="Wells"),
                        )
                        output_file = (
                            f"{output_dir}/{batch}/{plate}/{plate}_correlation.png"
                        )
                        fig.write_image(output_file, width=640, height=480, scale=2)

                        corr_df = (
                            corr_matrix_df.stack()
                            .reset_index()
                            .rename(
                                columns={
                                    "level_0": "Well_Row",
                                    "level_1": "Well_Col",
                                    0: "correlation",
                                }
                            )
                            .assign(Row=lambda x: x.Well_Row.str[0:1])
                            .assign(Col=lambda x: x.Well_Row.str[1:])
                        )

                        corr_df["same_row_col"] = corr_df.apply(
                            lambda x: str(x.Row) in str(x.Well_Col)
                            or str(x.Col) in str(x.Well_Col),
                            axis=1,
                        )

                        wells = list(df.Metadata_Well)
                        table_df = pd.DataFrame()

                        for well in wells:
                            signal = list(
                                corr_df.loc[
                                    (corr_df.Well_Row == well) & (corr_df.same_row_col)
                                ]["correlation"]
                            )
                            null = list(
                                corr_df.loc[
                                    (corr_df.Well_Row == well)
                                    & (corr_df.same_row_col == False)
                                ]["correlation"]
                            )

                            perc_95 = np.nanpercentile(null, 95)
                            above_threshold = signal > perc_95
                            value = np.mean(above_threshold.astype(float))

                            table_df = table_df.append(
                                {
                                    "Metadata_Row": well[0:1],
                                    "Metadata_Col": well[1:],
                                    "value": value,
                                },
                                ignore_index=True,
                            )

                        df_pivot = table_df.pivot(
                            "Metadata_Row", "Metadata_Col", "value"
                        )

                        fig = px.imshow(df_pivot, color_continuous_scale="blues")
                        fig.update_layout(
                            title=f"Plate: {plate}, Position effect",
                            xaxis=dict(title="", side="top"),
                            yaxis=dict(title=""),
                        )
                        fig.update_traces(xgap=1, ygap=1)

                        output_file = (
                            f"{output_dir}/{batch}/{plate}/{plate}_position_effect.png"
                        )
                        fig.write_image(output_file, width=640, height=480, scale=2)
