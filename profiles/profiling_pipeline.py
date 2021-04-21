"""
Perform the profiling pipeline (defined in profile.py).
"""

# Copied from
# https://github.com/broadinstitute/profiling-resistance-mechanisms/blob/master/0.generate-profiles/generate-profiles.py

import pathlib
from profile_utils import load_pipeline
from profile import process_profile, feature_selection
import argparse

parser = argparse.ArgumentParser(description="Run the profiling pipeline")
parser.add_argument("--config", help="Config file")

args = parser.parse_args()

pipeline, profile_config = load_pipeline(args.config)

for batch in profile_config:
    for plate in profile_config[batch]:
        print(f"Now processing... batch: {batch}, plate: {plate}")
        process_profile(batch=batch, plate=plate, pipeline=pipeline)

    if pipeline["feature_select"]["perform"]:
        print(f"Performing feature selection for batch: {batch}")
        feature_selection(batch=batch, plates=profile_config[batch], pipeline=pipeline)
