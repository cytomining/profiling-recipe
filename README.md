# Image-based Profiling Recipe

# Description
The profiling-recipe is a collection of scripts that primarily use [pycytominer](https://github.com/cytomining/pycytominer) functions to [process single-cell morphological profiles](https://github.com/cytomining/pycytominer/blob/master/media/pipeline.png). The three scripts are 
- `profiling-pipeline.py` - runs the image-based profile processing pipeline
- `csv2gz.py` - compresses `.csv` files
- `create_dirs.sh` - creates the subdirectories to store the output of the processing pipeline

# Getting Started
## Requirements
### Anaconda
We use Anaconda as our package manager. Install Miniconda following the instructions [here](https://docs.conda.io/en/latest/miniconda.html).

### Git LFS
We use Git LFS for storing and versioning large files. It can be installed following the instructions [here](https://git-lfs.github.com/).

### System requirements
If the profiling pipeline is used for aggregating the single cell profiles, we recommend running the pipeline on a system with a memory at least twice the size of the `.sqlite` files. If the pipeline will be used only for running steps that are downstream of aggregation, then it can be run on a local machine.  

## Creating the folder structure
The pipeline requires a particular folder structure which can be created as follows

```bash
PROJECT_NAME="INSERT-PROJECT-NAME"
mkdir -p ~/work/projects/${PROJECT_NAME}/workspace/{backend,software}
```

## Downloading the data
Download the `.sqlite` file, which contains the single cell profiles and the `.csv` file, which contains the well-level aggregated profiles, for all the plates in each batch to the `backend` folder. These two files are created by running the commands in chapter 5.3 of the [profiling handbook](https://cytomining.github.io/profiling-handbook/create-profiles.html#create-database-backend). After downloading the files, the folder structure should look as follows

```bash
backend
├── batch1
│   ├── plate1
│   │   ├── plate1.csv
│   │   └── plate1.sqlite
│   └── plate2
│       ├── plate2.csv
│       └── plate2.sqlite
└── batch2
    ├── plate1
    │   ├── plate1.csv
    │   └── plate1.sqlite
    └── plate2
        ├── plate2.csv
        └── plate2.sqlite
```

*Note: Aggregation may not have been performed already. In that case, only the `.sqlite` file will be available for download.*

## Welding to the data repository (Recommended)
Welding is a process by which the profiling-recipe repository is added to the data repository as a submodule such that the files in the data repository and the scripts in the profiling-recipe that generated those files, are versioned together. Instructions for welding is provided [here](https://github.com/cytomining/profiling-template#readme). We highly recommend welding the profiling-recipe to the data repository. After welding, clone the data repository to the `software` folder, using the command

```bash
cd ~/work/projects/${PROJECT_NAME}/workspace/software
git clone <location of the data repository>.git
cd <name of the data repository>
git submodule update --init --recursive
```

After cloning, the folder structure should look as follows

```bash
software
└── data_repo
    ├── LICENSE
    ├── README.md
    └── profiling-recipe
        ├── LICENSE
        ├── README.md
        ├── config_template.yml
        ├── environment.yml
        ├── profiles
        │   ├── profile.py
        │   ├── profiling_pipeline.py
        │   └── utils.py
        └── scripts
            ├── create_dirs.sh
            └── csv2gz.py
```

### Running the recipe without welding
It is possible to run the pipeline without welding the profiling-recipe repository to the data repository. If run in this manner, the profiling-recipe repository should be cloned to a data directory as a subdirectory. Then the folder structure will look as follows.

```
software
└── data_directory
    ├── LICENSE
    ├── README.md
    └── profiling-recipe
        ├── LICENSE
        ├── README.md
        ├── config_template.yml
        ├── environment.yml
        ├── profiles
        │   ├── profile.py
        │   ├── profiling_pipeline.py
        │   └── utils.py
        └── scripts
            ├── create_dirs.sh
            └── csv2gz.py
```

## Downloading load_data_csv
Generating summary statistics table requires `load_data_csv` files. These files should be downloaded to the `load_data_csv` directory. Make sure the files are gzipped, and the folder structure looks as follows.

```bash
load_data_csv/
├── batch1
│   ├── plate1
│   │   ├── load_data.csv.gz
│   │   └── load_data_with_illum.csv.gz
│   └── plate2
│       ├── load_data.csv.gz
│       └── load_data_with_illum.csv.gz
└── batch2
    ├── plate1
    │   ├── load_data.csv.gz
    │   └── load_data_with_illum.csv.gz
    └── plate2
        ├── load_data.csv.gz
        └── load_data_with_illum.csv.gz
```

# Running the pipeline
The pipeline should be run from the data repository or data directory.

```bash
DATA="INSERT-NAME-OF-DATA-REPO-OR-DIR"
cd ~/work/projects/${PROJECT_NAME}/workspace/software/${DATA}/
```

## Setting up the conda environment
### Copy the environment.yml file
The environment.yml file contains the list of conda packages that are necessary for running the pipeline.

```bash
cp profiling-recipe/environment.yml .
```

### Create the environment

```bash
conda env create --force --file environment.yml
```

### Activate the conda environment

```bash
conda activate profiling
```

## Create the directories
The directories that will contain the output of the pipeline are created as follows

```bash
profiling-recipe/scripts/create_dirs.sh
```

## Metadata, platemap and barcode_platemap files
The pipeline requires `barcode_platemap.csv` and `platemap.txt` to run. An optional `external_metadata.tsv` can also be provided for additional annotation. The following are the descriptions of each of these files

- `barcode_platemap.csv` - contains the mapping between plates and plate maps. There is one such file per batch of data. The file contains two columns whose names are `Assay_Plate_Barcode` and `Plate_Map_Name`, which should not be changed. The name of the file should not be changed either. This file should be a comma-separated `.csv` file.
- `platemap.txt` - contains the mapping between well names and perturbation names. There is one such file per plate map per batch. Two columns are necessary, one with the well names (`A01`, `A02`...) called `well_position` and the other with the perturbation identifier. The name of the perturbation identifier column can be user defined (if changed, change the name in the `config.yml` file). The name of this file can be changed. If changed, also change the name within `barcode_platemap.csv`. This file should be a tab-separated `.txt` file
- `external_metadata.tsv` - contains the mapping between perturbation identifier to other metadata. This file is optional. The perturbation identifier column should have the same name as the column in `platemap.txt`. This file should be a tab-separated `.tsv` file.

The following is an example of the `barcode_platemap.csv` file

```text
Assay_Plate_Barcode,Plate_Map_Name
plate1,platemap
plate2,platemap
```

[Here](https://github.com/jump-cellpainting/JUMP-Target/blob/master/JUMP-Target-1_compound_platemap.tsv) is an example plate map file and [here](https://github.com/jump-cellpainting/JUMP-Target/blob/master/JUMP-Target-1_compound_metadata.tsv) is an example external metadata file. 

These files should be added to the appropriate folder so that the folder structure looks as below

```bash
metadata
├── external_metadata
│   └── external_metadata.tsv
└── platemaps
    ├── batch1
    │   ├── barcode_platemap.csv
    │   └── platemap
    │       └── platemap.txt
    └── batch2
        ├── barcode_platemap.csv
        └── platemap
            └── platemap.txt
```

## Copy the config file
```bash
CONFIG_FILE="INSERT-CONFIG-FILE-NAME"
cd ~/work/projects/${PROJECT_NAME}/workspace/software/${DATA}/
cp profiling-recipe/config_template.yml config_files/${CONFIG_FILE}.yml
```

The config file contains all the parameters that various pycytominer functions, called by the profiling pipeline, require. To run the profiling pipeline with different parameters, multiple config files can be created. Each parameter in the config file is described below. All the necessary changes to the config file must be made before the pipeline can be run.

## Copy aggregated profile
If the first step of the profiling pipeline, `aggregate`, has already been performed (in the `backend` folder, there is a `.csv` file in addition to `.sqlite` file) then the `.csv` file has to be copied to the data repository or data directory. If not, skip to [Running the profiling pipeline](#running-the-profiling-pipeline).

Run the following commands for each batch separately. These commands create a folder for each batch, compress the `.csv` files, and then copy them to the data repository or data directory.

```bash
BATCH="INSERT-BATCH-NAME"
mkdir -p profiles/${BATCH}
find ../../backend/${BATCH}/ -type f -name "*.csv" -exec profiling-recipe/scripts/csv2gz.py {} \;
rsync -arzv --include="*/" --include="*.gz" --exclude "*" ../../backend/${BATCH}/ profiles/${BATCH}/
```

## Running the profiling pipeline

After making the necessary changes to the `config.yml` file, run the profiling pipeline as follows

```bash
python profiling-recipe/profiles/profiling_pipeline.py  --config config_files/${CONFIG_FILE}.yml
```

If there are multiple config files, each one of them can be run one after the other using the above command.

*Note: Each step in the profiling pipeline, uses the output from the previous step as its input. Therefore, make sure that all the necessary input files have been generated before running the steps in the profiling pipeline. It is possible to run only a few steps in the pipeline by keeping only those steps in the config file.*

## Push the profiles to GitHub
If using a data repository, push the newly created profiles to GitHub as follows

```bash
git add *
git commit -m 'add profiles'
git push
```

# Files generated
Running the profiling workflow with all the steps included generates the following files

| Filename                                                  | Description                                                                                          |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `<PLATE>.csv.gz`                                          | Aggregated well-level profiles                                                                       |
| `<PLATE>_augmented.csv.gz`                                | Metadata annotated profiles                                                                          |
| `<PLATE>_normalized.csv.gz`                               | Profiles normalized to the whole plate                                                               |
| `<PLATE>_normalized_negcon.csv.gz `                       | Profiles normalized to the negative control                                                          |
| `<PLATE>_normalized_feature_select_<LEVEL>.csv.gz`        | Whole plate normalized profiles that are feature selected at the `plate`,  `batch` or `all plates` level      |
| `<PLATE>_normalized_feature_select_negcon_<LEVEL>.csv.gz` | Negative control normalized profiles that are feature selected at the `plate`,  `batch` or `all plates` level |
| `summary.tsv`                                             | Summary statistics                                                                                   |
| `<PLATE>_cell_count.png`                                  | Plate cell count                                                                                     |
| `<PLATE>_correlation.png`                                 | Pairwise correlation between all the wells on a plate                                                |
| `<PLATE>_position_effect.png`                             | Percent Matching between each well and other wells in the same row and column                        |
	
# Config file
## Pipeline parameters
These are the parameters that all pipelines will require

### Name of the pipeline
The name of the pipeline helps distinguish the different config files. It is not used by the pipeline itself.

```yaml
pipeline: <PIPELINE NAME>
```

### Output directory
Name of the directory where the profiles will be stored. It is `profiles` by default.

```yaml
output_dir: profiles
```

### Well name column
Name of the well name column in the `aggregated` profiles. It is `Metadata_well_position` by default.

```yaml
platemap_well_column: Metadata_well_position
```

### Compartment names
By default, CellProfiler features are extracted from three compartments, `cells`, `cytoplasm` and `nuclei`.  These compartments are listed in the config file as follows

```yaml
compartments:
  - cells
  - cytoplasm
  - nuclei
```

If other 'non-canonical' compartments are present in the dataset, then those are added to the above list as follows

```yaml
compartments:
  - cells
  - cytoplasm
  - nuclei
  - newcompartment
```

*Note: if the name of the non-canonical compartment is `newcompartment` then the features from that compartment should begin with `Newcompartment` (only the first character should be capitalized). The pipeline will fail if camel case or any other format are used for feature names.*

### Other pipeline options
```yaml
options:
  compression: gzip
  float_format: "%.5g"
  samples: all
```

- `compression` - The compression format for the profile `.csv`s. Default is `gzip` which is currently the only accepted value. 
- `float_format` - The number of significant digits. 
- `samples` - Whether to perform the following operations on all or a subset of samples. Default is  `all` which is currently the only accepted value.

## `aggregate` parameters
These are parameters that are processed by the `pipeline_aggregate()` function that interacts with `pycytominer.cyto_utils.cells.SingleCells()` and aggregates single cell profiles to create well level profiles.

```yaml
aggregate:
  perform: true
  plate_column: Metadata_Plate
  well_column: Metadata_Well
  method: median
  fields: all
```

- `perform` - Whether to perform aggregation. Default is `true`. Set to `false` if this should not be performed.
- `plate_column` - Name of the column with the plate name. Default is `Metadata_Plate`.
- `well_column` - Name of the column with the well names. Default is `Metadata_Well`.
- `method` - How to perform aggregation. Default is `median`. Also accepts `mean`.
- `fields` - Cells from which field of view should be aggregated? Default is `all`. If specific fields of view are to be aggregated (for example 1, 4, 9), it can be done as follows

```yaml
fields:
  - 1
  - 4
  - 9
```

## `annotate` parameters
These are parameters that are processed by the `pipeline_annotate()` function that interacts with `pycytominer.annotate()` and annotates the well level profiles with metadata.

```yaml
annotate:
  perform: true
  well_column: Metadata_Well
  external :
    perform: true
    file: <metadata file name>
    merge_column: <Column to merge on>
```

- `perform` - Whether to perform annotation. Default is `true`. Set to `false` if this should not be performed.
- `well_column` - Column with the well names in the aggregated profiles.
- `external`
	- `perform` - Whether to annotate the profiles with external metadata. Default is `true`. Set to `false` if this should not be performed.
	- `file` - external metadata file which should be in the folder `metadata/external_metadata/`.
	- `merge_column` - Name of the perturbation identifier column that is common to `platemap.txt` and `external_metadata.tsv`.

## `normalize` parameters
These are parameters that are processed by the `pipeline_normalize()` function that interacts with `pycytominer.normalize()` and normalizes all the wells to the whole plate.

```yaml
normalize:
  perform: true
  method: mad_robustize
  features: infer
```

- `perform` - Whether to perform normalization. Default is `true`. Set to `false` if this should not be performed.
- `method` - Which method to use for normalization. Default is `mad_robustize`. Other options are available in pycytominer, such as, `standardize`, `robustize` and `spherize`.
- `features` - Names of the feature measurement columns. Default is `infer`, which infers CellProfiler features from the annotated profiles.

### `normalize_negcon` parameters
These are parameters that are processed by the `pipeline_normalize()` function that interacts with `pycytominer.normalize()` and normalizes all the wells to the negative control.

```yaml
normalize_negcon:
  perform: true
  method: mad_robustize
  features: infer
```

- `perform` - Whether to perform normalization. Default is `true`. Set to `false` if this should not be performed.
- `method` - Which method to use for normalization. Default is `mad_robustize`. Other options are available in pycytominer, such as, `standardize`, `robustize` and `spherize`.
- `features` - Names of the feature measurement columns. Default is `infer`, which infers CellProfiler features from the annotated profiles.

## `feature_select` parameters
These are parameters that are processed by the `pipeline_feature_select()` function that interacts with `pycytominer.feature_select()` and selects features in the whole-plate normalized profiles.

```yaml
feature_select:
  perform: true
  features: infer
  level: plate
  operations:
    - variance_threshold
    - correlation_threshold
    - drop_na_columns
    - blocklist
```

- `perform` - Whether to perform feature selection. Default is `true`. Set to `false` if this should not be performed.
- `features` - Names of the feature measurement columns. Default is `infer`, which infers CellProfiler features from the normalized profiles.
- `level` - Level at which feature selection should be performed. Default is `plate`. Feature selection can also be performed at `batch` and `all` plates level.
- `operations` - List of feature selection operations. `variance_threshold` removes features that have a variance under the thershold across all the wells on a plate. `correlation_threshold` removes redundant features. `drop_na_columns` removes features with `NaN` values. `blocklist` removes features that are a part of the feature blocklist.

### `feature_select_negcon` parameters
These are parameters that are processed by the `pipeline_feature_select()` function that interacts with `pycytominer.feature_select()` and selects features in the profiles normalized to the negative control.

```yaml
feature_select_negcon:
  perform: true
  features: infer
  level: plate
  operations:
    - variance_threshold
    - correlation_threshold
    - drop_na_columns
    - blocklist
```

- `perform` - Whether to perform feature selection. Default is `true`. Set to `false` if this should not be performed.
- `features` - Names of the feature measurement columns. Default is `infer`, which infers CellProfiler features from the normalized profiles.
- `level` - Level at which feature selection should be performed. Default is `plate`. Feature selection can also be performed at `batch` and `all` plates level.
- `operations` - List of feature selection operations. `variance_threshold` removes features that have a variance under the thershold across all the wells on a plate. `correlation_threshold` removes redundant features. `drop_na_columns` removes features with `NaN` values. `blocklist` removes features that are a part of the feature blocklist.

## quality_control parameters
These parameters specify the type of quality control metrics and figures to generate. `summary` generates a table with summary statistics while `heatmap` generates three heatmaps, each showing a different quality control metric.

```yaml
quality_control:
  perform: true
  operations:
    - summary
    - heatmap
```

- `perform` - Whether to generate quality control metrics or figures. Default is `true`. Set to `false` if these should not be generated.
- `operations` - List of different qc metrics of figures to generate.

## batch and parameters
These parameters specify the name of the batch and plate to process. 

```yaml
batch: <BATCH NAME>
plates:
  - name: <PLATE NAME>
    process: true
process: true
```

- `batch` - Name of the batch to be processed.
- `plates` -
	- `name` - Name of the plate to be processed.
	- `process` - Whether to process the plate. Default is `true`. Set to `false` if this plate should not be processed.
- `process` - Whether to process the batch. Default is `true`. Set to `false` if this batch should not be processed.

# Rerunning the pipeline 
- The instructions in this README assumes that the profiling pipeline is being run for the first time within the data repository. It is possible that you are rerunning the pipeline with a new config file in a repository that already contains profiles. In that case, after cloning the data repository, it is important to download the profiling-recipe submodule anddownload the profiles from Git LFS before running the pipeline. This can be done using the following commands

```bash
git submodule update --init --recursive
git lfs pull
```
