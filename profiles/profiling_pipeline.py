"""
Perform the profiling pipeline (defined in profile.py).
"""

# Modified from
# https://github.com/broadinstitute/profiling-resistance-mechanisms/blob/master/0.generate-profiles/generate-profiles.py

from utils import load_pipeline, create_directories
from profile import RunPipeline
import argparse

parser = argparse.ArgumentParser(description="Run the profiling pipeline")
parser.add_argument("--config", help="Config file")

args = parser.parse_args()

pipeline, profile_config = load_pipeline(config_file=args.config)

run_pipeline = RunPipeline(pipeline=pipeline, profile_config=profile_config)

for batch in profile_config:
    print(f"Now processing... batch: {batch}")
    for plate in profile_config[batch]:
        create_directories(batch=batch, plate=plate, pipeline=pipeline)

        if "aggregate" in pipeline:
            if pipeline["aggregate"]["perform"]:
                print(f"Now aggregating... plate: {plate}")
                run_pipeline.pipeline_aggregate(batch=batch, plate=plate)

        if "annotate" in pipeline:
            if pipeline["annotate"]["perform"]:
                print(f"Now annotating... plate: {plate}")
                run_pipeline.pipeline_annotate(batch=batch, plate=plate)

        if "normalize" in pipeline:
            if pipeline["normalize"]["perform"]:
                print(f"Now normalizing... plate: {plate}")
                run_pipeline.pipeline_normalize(
                    batch=batch, plate=plate, steps=pipeline["normalize"], samples="all"
                )

        if "normalize_negcon" in pipeline:
            if pipeline["normalize_negcon"]["perform"]:
                print(f"Now normalizing to negcon... plate: {plate}")
                run_pipeline.pipeline_normalize(
                    batch=batch,
                    plate=plate,
                    steps=pipeline["normalize_negcon"],
                    samples="Metadata_control_type == 'negcon'",
                    suffix="negcon",
                )

if "feature_select" in pipeline:
    if pipeline["feature_select"]["perform"]:
        print(f"Now feature selecting... level: {pipeline['feature_select']['level']}")
        run_pipeline.pipeline_feature_select(steps=pipeline["feature_select"])

if "feature_select_negcon" in pipeline:
    if pipeline["feature_select_negcon"]["perform"]:
        print(
            f"Now feature selecting negcon profiles... level: {pipeline['feature_select_negcon']['level']}"
        )
        run_pipeline.pipeline_feature_select(
            steps=pipeline["feature_select_negcon"], suffix="negcon"
        )

if "quality_control" in pipeline:
    if pipeline["quality_control"]["perform"]:
        print(f"Now generating output for assessing data quality")
        run_pipeline.pipeline_quality_control(steps=pipeline["quality_control"])