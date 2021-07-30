#!/bin/bash
# Execute this in the top level folder of the data repo

if [ ! -d "./audit/" ]; then
	mkdir -p audit
	mkdir -p batchfiles
	mkdir -p config_files
	mkdir -p gct
	mkdir -p load_data_csv
	mkdir -p log
	mkdir -p metadata
	mkdir -p pipelines
	mkdir -p profiles
	mkdir -p quality_control
	mkdir -p single_cell

	echo "# Audits" >> audit/README.md
	echo "# Batchfiles" >> batchfiles/README.md
	echo "# Config files" >> config_files/README.md
	echo "# GCT files" >> gct/README.md
	echo "# LoadData CSVs" >> load_data_csv/README.md
	echo "# Logs" >> log/README.md
	echo "# Metadata" >> metadata/README.md
	echo "# Pipelines" >> pipelines/README.md
	echo "# Profiles" >> profiles/README.md
	echo "# Quality Control" >> quality_control/README.md
	echo "# Single-cell data" >> single_cell/README.md
fi
