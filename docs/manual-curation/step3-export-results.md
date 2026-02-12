# Manual curation, part III, technical: export curation results and submit feedback to ZOOMA

Before running, set up the environment (Open Targets batches only):
* [Common environment](../open-targets/environment.md)
* [Protocol-specific environment](README.md#setting-up-environment)

## Extract curation results from the spreadsheet

Once the manual curation is completed, download the spreadsheet as a CSV file, making sure that all the data is visible before doing so (i.e., no filters are applied). Save the data to a file `${CURATION_RELEASE_ROOT}/finished_curation_spreadsheet.csv`.

## Run the automated protocol

```bash
cd ${CURATION_RELEASE_ROOT}

# Run the nextflow pipeline, resuming execution of previous attempt if possible.
nextflow run ${CODE_ROOT}/pipelines/export_curation_spreadsheet.nf \
  --input_csv ${CURATION_RELEASE_ROOT}/finished_curation_spreadsheet.csv \
  --curation_root ${CURATION_RELEASE_ROOT} \
  --with_feedback \
  -resume
```

## Check and correct known problematic mappings
There is a [spreadsheet](https://docs.google.com/spreadsheets/d/1m4ld3y3Pfust5JSOJOX9ZmImRCKRGi-fGYj_dExoGj8/edit) which was created to track trait-to-ontology mappings which were especially problematic in the past to users of Open Targets platform. Prior to running subsequent steps, make sure that all traits mentioned in that spreadsheet are mapped to the correct ontology terms in `${BATCH_ROOT_BASE}/manual_curation/latest_mappings.tsv`.

## Submit feedback to EFO
Tables for IMPORT and NEW terms will be created by curators during [step 2](step2-manual-curation.md).
Open a new git issue with EFO to review and import these novel trait names, e.g. [https://github.com/EBISPOT/efo/issues/1898](https://github.com/EBISPOT/efo/issues/1898).


## Submit feedback to ZOOMA
See more details on ZOOMA feedback in the [evidence string generation protocol](../generate-evidence-strings.md#submit-feedback-to-zooma). At this stage, only the **eva_clinvar** dataset is being submitted; clinvar_xrefs is submitted during evidence string generation.

On the Codon cluster, be sure to execute the following on a datamovers node.

```bash
# Create the folder, copy the file to FTP, and update the “latest” folder
FTP_PATH=${FTP_PATH_BASE}/`date +%Y/%m/%d`
mkdir -p ${FTP_PATH}
cp ${BATCH_ROOT_BASE}/manual_curation/eva_clinvar.txt ${FTP_PATH}
cp ${FTP_PATH}/eva_clinvar.txt ${FTP_PATH_BASE}/latest/eva_clinvar.txt
```

After uploading both files, confirm that the changes have propagated to the FTP:
```bash
md5sum ${BATCH_ROOT_BASE}/manual_curation/eva_clinvar.txt
wget -qO- ftp://ftp.ebi.ac.uk/pub/databases/eva/ClinVar/`date +%Y/%m/%d`/eva_clinvar.txt | md5sum
wget -qO- ftp://ftp.ebi.ac.uk/pub/databases/eva/ClinVar/latest/eva_clinvar.txt | md5sum
```
