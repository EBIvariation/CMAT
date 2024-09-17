[![Build Status](https://github.com/EBIvariation/CMAT/actions/workflows/tests.yml/badge.svg)](https://github.com/EBIvariation/CMAT/actions)
[![Coverage Status](https://coveralls.io/repos/github/EBIvariation/CMAT/badge.svg?branch=master)](https://coveralls.io/github/EBIvariation/CMAT?branch=master)

# CMAT: ClinVar Mapping and Annotation Toolkit

CMAT is a software toolkit and curation protocol for parsing and enriching ClinVar's XML data.
To learn more about what is available in ClinVar, please refer to their [website](https://www.ncbi.nlm.nih.gov/clinvar/).

For instructions on how to process ClinVar data for the Open Targets platform, see [here](docs/open-targets).

## Install

The code requires Python 3.8+, and you will also need Nextflow 21.10+ to run the pipelines. Refer to [Nextflow documentation](https://www.nextflow.io/docs/latest/getstarted.html) for specifics on installing Nextflow on your system.

To install CMAT, first either clone the repository or download the latest released version from [here](https://github.com/EBIvariation/CMAT/releases):
```bash
git clone git@github.com:EBIvariation/CMAT.git
# OR
wget -O CMAT.zip https://github.com/EBIvariation/CMAT/archive/refs/tags/v3.0.3.zip
unzip CMAT.zip
```

Then install the library and its dependencies as follows (e.g. in a virtual environment):
```bash
cd CMAT
pip install -r requirements.txt
python setup.py install
```

You then need to set the `PYTHON_BIN` variable in the [Nextflow config](pipelines/nextflow.config), which will allow the
Nextflow processes to access the correct Python executable.

Finally, the instructions in this readme use the following environment variables as a convenience, they are not needed for the pipelines to run.
```bash
# Path to directory where source code is downloaded
export CODE_ROOT=
# Path to ontology mapping file (the provided path points to the version included in this repo)
export LATEST_MAPPINGS=${CODE_ROOT}/mappings/latest_mappings.tsv
```

If this is your first time running the pipelines with a specific target ontology (i.e. you don't have a latest mappings file to use),
you can use an empty TSV file containing just the header `#ontology=<code>`, where `<code>` is taken from [this list](https://www.ebi.ac.uk/ols4/ontologies) of supportable ontologies.
This file will be filled with automated and manually curated mappings as processing continues.

To confirm everything is set up properly, you can run the annotation pipeline on the small dataset included with the tests.
It should take a couple minutes to run and generate a file `annotated_clinvar.xml.gz` in the test directory.
```bash
mkdir testdir && cd testdir
nextflow run ${CODE_ROOT}/pipelines/annotation_pipeline.nf \
  --output_dir . \
  --clinvar ${CODE_ROOT}/tests/output_generation/resources/end2end/input.xml.gz \
  --mappings ${LATEST_MAPPINGS}
```

### Conda

You can also install CMAT using Conda.
For example the following installs CMAT in a new environment called `cmat`, activates the environment, and prints usage:
```bash
conda create -n cmat -c conda-forge -c bioconda cmat
conda activate cmat
cmat
```

Note that with conda installation you can't invoke the pipelines directly via Nextflow, so you will need to use the corresponding `cmat` commands - e.g. `cmat annotate` instead of `nextflow run annotation_pipeline.nf`.
All the same command line options apply.

## Run

CMAT includes a main annotation pipeline (which also performs consequence and gene mapping), as well as two pipelines to help manage trait mapping curation.
It can also be used as a standard Python library.

### Annotation pipeline

This will annotate variants with genes and functional consequences, and annotate traits with ontology terms using an existing mappings file.
It outputs the results as an annotated XML file.

```bash
# Directory to run annotation pipeline
export ANNOTATION_ROOT=

# Create directories for data processing
mkdir -p ${ANNOTATION_ROOT}
cd ${ANNOTATION_ROOT}
mkdir -p gene_mapping logs

# Run the nextflow pipeline, resuming execution of previous attempt if possible.
# For conda, use instead: cmat annotate
nextflow run ${CODE_ROOT}/pipelines/annotation_pipeline.nf \
  --output_dir ${ANNOTATION_ROOT} \
  --mappings ${LATEST_MAPPINGS} \
  -resume
```
You can use the `--include_transcripts` flag to also include transcript annotations with the functional consequences.

By default, the pipeline will download and annotate the latest ClinVar RCV XML dump from [FTP](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/). If you want to run it on an existing XML file, you can pass it via the `--clinvar` flag.

### Trait curation

These are processes to update the trait mappings used by the annotation pipeline and should be performed regularly to ensure new ClinVar data is mapped appropriately.

A complete protocol for trait curation can be found [here](docs/manual-curation), though it may require adaptation for your use case.
A minimum set of steps to run the curation is provided in the sections below.

#### Automatic mappings and curation spreadsheet generation

```bash
# Directory to run trait curation pipelines
export CURATION_ROOT=

# Path to previous curator comments to be included in spreadsheet.
# If this is the first round of curation, you can use an empty file.
export CURATOR_COMMENTS=

# Create directories for data processing
mkdir -p ${CURATION_ROOT}
cd ${CURATION_ROOT}

# Run the nextflow pipeline, resuming execution of previous attempt if possible.
# For conda, use instead: cmat generate-curation
nextflow run ${CODE_ROOT}/pipelines/generate_curation_spreadsheet.nf \
  --curation_root ${CURATION_ROOT} \
  --mappings ${LATEST_MAPPINGS} \
  --comments ${CURATOR_COMMENTS} \
  -resume
```

By default, the pipeline will download and map the latest ClinVar RCV XML dump from [FTP](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/). If you want to run it on an existing XML file, you can pass it via the `--clinvar` flag.

To create the curation spreadsheet, first make your own copy of the [template](https://docs.google.com/spreadsheets/d/1GWAQAZjOpzsIkdCu0CSRDoehZEUB3VjZYYiHWp9Tn7Q/edit?usp=sharing).
Then paste the contents of `${CURATION_ROOT}/google_sheets_table.tsv` into it, starting with column H “ClinVar label”.

#### Manual curation

This is done manually using the spreadsheet, ideally with a curator and at least one reviewer.
The written protocol can be found [here](docs/manual-curation/step2-manual-curation.md).

#### Curation spreadsheet export

Once the manual curation is completed, the new mappings need to be incorporated into the set of latest mappings to be used for future annotation and trait curation.

Download the spreadsheet as a CSV file, making sure that all the data is visible before doing so (i.e., no filters are applied). Save the data to a file `${CURATION_ROOT}/finished_curation_spreadsheet.csv`.

```bash
cd ${CURATION_ROOT}

# Run the nextflow pipeline, resuming execution of previous attempt if possible.
# For conda, use instead: cmat export-curation
nextflow run ${CODE_ROOT}/pipelines/export_curation_spreadsheet.nf \
  --input_csv ${CURATION_ROOT}/finished_curation_spreadsheet.csv \
  --curation_root ${CURATION_ROOT} \
  --mappings ${LATEST_MAPPINGS} \
  -resume
```

### Library usage

CMAT can also be used as a normal Python library, for example:

```python
from cmat.clinvar_xml_io import ClinVarDataset

for record in ClinVarDataset('/path/to/clinvar.xml.gz'):
    s = f'{record.accession}: '
    if record.measure and record.measure.has_complete_coordinates:
        s += record.measure.vcf_full_coords
    s += ' => '
    s += ', '.join(trait.preferred_or_other_valid_name for trait in record.traits_with_valid_names)

    # e.g. RCV001842692: 3_38633214_G_C => Cardiac arrhythmia
    print(s)
```

## Citation

If you find CMAT useful, you can cite the following:

> Shen et al., CMAT: ClinVar Mapping and Annotation Toolkit. _Bioinformatics Advances_, 2024. [doi:10.1093/bioadv/vbae018](https://doi.org/10.1093/bioadv/vbae018)
