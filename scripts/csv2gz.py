#!/usr/bin/env python
import pycytominer
import sys

input_filename = sys.argv[1]

output_filename = input_filename + ".gz"

df = pycytominer.cyto_utils.load.load_profiles(input_filename)

df = pycytominer.cyto_utils.output(
    df, output_filename, compression="gzip", float_format="%.3g"
)
