"""
Perform the profiling pipeline (defined in profile.py).
"""

# Copied from
# https://github.com/broadinstitute/profiling-resistance-mechanisms/blob/master/0.generate-profiles/generate-profiles.py

import pathlib
from profile_utils import load_pipeline
from profile import process_profile
import argparse

parser = argparse.ArgumentParser(description='Run the profiling pipeline')
parser.add_argument('--config', help='Config file')

args = parser.parse_args()

pipeline, profile_config = load_pipeline(args.config)

for batch in profile_config:
    for plate, cell in profile_config[batch]:
        print(f'Now processing... batch: {batch}, plate: {plate}')
        process_profile(batch=batch, plate=plate, cell=cell, pipeline=pipeline)
