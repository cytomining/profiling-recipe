"""
Perform the profiling pipeline (defined in profile.py).
"""

# Copied from
# https://github.com/broadinstitute/profiling-resistance-mechanisms/blob/master/0.generate-profiles/generate-profiles.py

import pathlib
from profile_utils import load_pipeline
from profile import process_profile

config_file = pathlib.PurePath('.', 'config.yml')

pipeline, profile_config = load_pipeline(config_file)

for batch in profile_config:
    for plate in profile_config[batch]:
        print(f'Now processing... batch: {batch}, plate: {plate}')
        process_profile(batch=batch, plate=plate, pipeline=pipeline)
