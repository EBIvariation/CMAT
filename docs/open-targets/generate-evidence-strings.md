# Evidence string generation protocol

## 1. Preparation steps

### Check if the pipeline needs to be updated
Open Targets will circulate an email several weeks before the data submission deadline which will contain the version of the [JSON schema](https://github.com/opentargets/json_schema) to be used. Examine the changes, and modify this pipeline to accommodate them if necessary.

Regardless of whether any changes were made, update the `OT_SCHEMA_VERSION` value in [this file](/OT_SCHEMA_VERSION), which is used both in this protocol and the tests.

### Set up the environment
First, [set up the common environment.](environment.md)

Next, set up the protocol-specific environment:

```bash
# Year and month for the upcoming Open Targets release.
# For example, if you're processing data for “20.02” release, this variable will be set to `2020-02`.
export OT_RELEASE=YYYY-MM

# Open Targets JSON schema version.
export OT_SCHEMA_VERSION=$(cat "${CODE_ROOT}/OT_SCHEMA_VERSION")
```

## 1. Process data
The protocol is automated. See specific section comments for details.

```bash
# Create directory structure for holding all files for the current batch.
export BATCH_ROOT=${BATCH_ROOT_BASE}/batch-${OT_RELEASE}
mkdir -p ${BATCH_ROOT}
cd ${BATCH_ROOT}
mkdir -p clinvar gene_mapping evidence_strings logs

# Run the nextflow pipeline, resuming execution of previous attempt if possible.
nextflow run ${CODE_ROOT}/pipelines/annotation_pipeline.nf \
  --output_dir ${BATCH_ROOT} \
  --schema ${OT_SCHEMA_VERSION} \
  -resume
```

### Note on duplication checks
The algorithm used for generating the evidence strings should not allow any duplicate values to be emitted, and the automated pipeline should fail with an error if duplicates are detected.

A repeated evidence string will have identical values for these five fields:
* **datatypeId** - Identifier of the type of data we are associating, varying between somatic and non-somatic ClinVar records (*e.g.* ``somatic_mutation`` or ``genetic_association`` respectively). 
* **studyId** - Reference ClinVar record (*e.g.* ``RCV000015714``).
* **targetFromSourceId** - The gene affected by the variant (*e.g.* ``ENSG00000186832``).
* **variantId** - The variant descriptive ID (*e.g.* ``11_5254661_T_A``, which corresponds to a point mutation from Thymine to Adenine at coordinate 5254661 of Chromosome 11).
* **variantFunctionalConsequenceId** - The consequence of such variant (*e.g.* ``SO_0001818``, which corresponds to protein_altering_variant). 
* **diseaseFromSourceMappedId** - Associated phenotype to such variant (*e.g.* ``Orphanet_2337``, which corresponds to a type of keratoderma). 

Nevertheless, we also report evidence strings in which  ``diseaseFromSourceMappedId`` may be empty (``diseaseFromSourceMappedId: null``) - i.e. the phenotype has not been mapped to an ontology yet. Therefore, to check for duplicates we also take into account the field ``diseaseFromSource``, which is the string describing the phenotype within ClinVar records (and is never missing in any evidence string).

## 2. Manual follow-up actions

### Update summary metrics
After the evidence strings have been generated, summary metrics need to be updated in the Google Sheets [table](https://docs.google.com/spreadsheets/d/1g_4tHNWP4VIikH7Jb0ui5aNr0PiFgvscZYOe69g191k/) on the “Raw statistics” sheet.

There are also a few version numbers to record. For EFO version, compare the release date [here](https://github.com/EBISPOT/efo/releases) with manual curation date. For Ensembl version, do the same with the release date [here](https://www.ensembl.org/index.html) and the evidence string generation date.

### Submit evidence strings
The evidence string file (`evidence_strings.json`) must be uploaded to the [Open Targets Google Cloud Storage](https://console.cloud.google.com/storage/browser/otar012-eva/).
To do this, run the following:
```shell
${CODE_ROOT}/bin/upload_to_gcloud.py --input-file evidence_strings/evidence_strings.json --destination-folder disease-target-evidence
```

Once the upload is complete, send an email to Open Targets (data [at] opentargets.org) containing the following information from the [metrics spreadsheet](https://docs.google.com/spreadsheets/d/1g_4tHNWP4VIikH7Jb0ui5aNr0PiFgvscZYOe69g191k/):
* The number of submitted evidence strings
* The ClinVar release date
* The Ensembl release
* The EFO version used for mapping
* The `CMAT` pipeline version
* The Open Targets JSON schema version

### Submit feedback to ZOOMA
The idea with [ZOOMA](http://www.ebi.ac.uk/spot/zooma/) is that we not only use it, but also provide feedback to help improve it. The evidence string generation pipeline generates two files with such a feedback:
1. **clinvar_xrefs.** ClinVar data already includes some cross-links from trait names to disease ontologies. Unfortunately, it almost exclusively uses MedGen and OMIM, which are not acceptable for Open Targets (since they're using EFO). However, mappings from trait names to MedGen and OMIM might still be useful to other users. Hence, we extract and submit them to ZOOMA under the evidence handle “ClinVar_xRefs”.
1. **eva_clinvar.** This contains the trait mappings (to EFO) created during the evidence string generation, including automated and manual mappings.

The files are uploaded to the FTP, where ZOOMA will pick it up. At this stage, you only need to upload the **clinvar_xrefs** dataset (the *eva_clinvar* dataset is updated in the process of the manual curation).

To make changes to the FTP, you will need to log in to a datamover node.
```bash
# Create the folder, copy the file to FTP, and update the “latest” folder
FTP_PATH=${FTP_PATH_BASE}/`date +%Y/%m/%d`
mkdir -p ${FTP_PATH}
cp ${BATCH_ROOT}/clinvar/clinvar_xrefs.txt ${FTP_PATH}
cp ${FTP_PATH}/clinvar_xrefs.txt ${FTP_PATH_BASE}/latest/clinvar_xrefs.txt
```

After uploading both files, confirm that the changes have propagated to the FTP:
```bash
md5sum ${BATCH_ROOT}/clinvar/clinvar_xrefs.txt
wget -qO- ftp://ftp.ebi.ac.uk/pub/databases/eva/ClinVar/`date +%Y/%m/%d`/clinvar_xrefs.txt | md5sum
wget -qO- ftp://ftp.ebi.ac.uk/pub/databases/eva/ClinVar/latest/clinvar_xrefs.txt | md5sum
```

If everything has been done correctly, hash sums will be the same. Note that the FTP may take a few minutes to update after you make changes on the cluster.

## Review checklist
* General
  + All relevant logs are present and contain no unexpected warnings or errors
  + All intermediate and output files
    - Are present
    - In the correct format without obvious errors (compare with the previous OT batch)
    - Line/record count is the same or more compared to the previous OT batch
    - Files are terminated correctly (not ending abruptly after an incomplete record)
* Step 2 “Set up directories and download the data”
  + Working directory exists and its structure is as described in the instructions for the step
* Step 3 “Manual steps & checks before running the pipeline”
  + References to the Open Targets schema version are updated throughout the code and in the test files
* Step 4 “Process data”
  + Functional consequences
    - There shouldn't be any warnings such as “Error on last attempt, skipping” in the logs. This might mean that one of the servers was down during processing, and potentially not all information has been gathered.
    - The final file with the genes & consequences contains both “normal variants”, and a few dozen repeat variants, including `short_tandem_repeat_expansion` and `trinucleotide_repeat_expansion` ones.
    - The `${BATCH_ROOT}/logs/consequence_repeat.err` log will record all repeat expansion variants which could not be parsed using any of the regular expressions. Verify that there are no new such variants compared to the previous batch.
  + Evidence stringts
    - Version of JSON schema is the same as specified in the Open Targets e-mail
* Step 5 “Manual follow-up actions”
  + The summary metrics
    - Are present in the [spreadsheet](https://docs.google.com/spreadsheets/d/1g_4tHNWP4VIikH7Jb0ui5aNr0PiFgvscZYOe69g191k/)
    - Are calculated correctly (re-calculate using the commands in the spreadsheet as required)
    - Are not worse than for the previous release
  + Generated evidence strings validate against the schema
    - Have actually been submitted to the Open Targets cloud storage
    - The file is the same as on the cluster (check md5)
    - E-mail has been sent to Open Targets, with opentargets-clinvar in copy
  + ZOOMA feedback (the FTP path is http://ftp.ebi.ac.uk/pub/databases/eva/ClinVar/latest; to see where files are located on the cluster, see variable `BATCH_ROOT_BASE` on [this page](https://github.com/EBIvariation/configuration/blob/master/open-targets-configuration.md))
    - The changes have been propagated to the FTP, and the files available over FTP are the same as on the cluster
    - The files in the `YYYY/MM/DD` and in the `latest` folders are identical (using either symlinks or copied)
