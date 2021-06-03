# Evidence string generation protocol

## 1. Preparation steps

### Check if the pipeline needs to be updated
Open Targets will circulate an email several weeks before the data submission deadline which will contain the version of the [JSON schema](https://github.com/opentargets/json_schema) to be used. Examine the changes, and modify this pipeline to accommodate them if necessary.

Regardless of whether any changes were made, update the `OT_SCHEMA_VERSION` value both in this document and in the [test files](/tests/eva_cttv_pipeline/evidence_string_generation/config.py).

### Set up the environment
First, [set up the common environment.](environment.md)

Next, set up the protocol-specific environment:

```bash
# Year and month for the upcoming Open Targets release.
# For example, if you're processing data for “20.02” release, this variable will be set to `2020-02`.
export OT_RELEASE=YYYY-MM

# Open Targets JSON schema version.
export OT_SCHEMA_VERSION=2.0.9
```

### Check and correct known problematic mappings
There is a [spreadsheet](https://docs.google.com/spreadsheets/d/1m4ld3y3Pfust5JSOJOX9ZmImRCKRGi-fGYj_dExoGj8/edit) which was created to track trait-to-ontology mappings which were especially problematic in the past to users of Open Targets platform. Prior to running subsequent steps, make sure that all traits mentioned in that spreadsheet are mapped to the correct ontology terms in `${BATCH_ROOT_BASE}/manual_curation/latest_mappings.tsv`.

## 2. Process data
The protocol is automated. See specific section comments for details.

```bash
# Create directory structure for holding all files for the current batch.
export BATCH_ROOT=${BATCH_ROOT_BASE}/batch-${OT_RELEASE}
mkdir -p ${BATCH_ROOT}
cd ${BATCH_ROOT}
mkdir -p clinvar gene_mapping evidence_strings logs

# Download ClinVar data. We always use the most recent XML dump, which contains all data for the release.
wget \
  --directory-prefix ${BATCH_ROOT}/clinvar \
  https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/ClinVarFullRelease_00-latest.xml.gz

# Download the Open Targets JSON schema.
wget \
  -O ${BATCH_ROOT}/evidence_strings/opentargets-${OT_SCHEMA_VERSION}.json \
  https://raw.githubusercontent.com/opentargets/json_schema/${OT_SCHEMA_VERSION}/opentargets.json

# Extract repeat expansion variants from ClinVar and map them to genes.
cd ${CODE_ROOT}
${BSUB_CMDLINE} -K \
  -o ${BATCH_ROOT}/logs/consequence_repeat_expansion.out \
  -e ${BATCH_ROOT}/logs/consequence_repeat_expansion.err \
  python3 ${CODE_ROOT}/consequence_prediction/run_repeat_expansion_variants.py \
    --clinvar-xml         ${BATCH_ROOT}/clinvar/ClinVarFullRelease_00-latest.xml.gz \
    --output-consequences ${BATCH_ROOT}/gene_mapping/consequences_1_repeat.tsv \
    --output-dataframe    ${BATCH_ROOT}/gene_mapping/repeat_dataframe.tsv

# Run ClinVar variants through VEP and map them to genes and functional consequences.
${BSUB_CMDLINE} -K -M 10G \
  -o ${BATCH_ROOT}/logs/consequence_vep.out \
  -e ${BATCH_ROOT}/logs/consequence_vep.err \
  bash ${CODE_ROOT}/consequence_prediction/run_consequence_mapping.sh \
    ${BATCH_ROOT}/clinvar/ClinVarFullRelease_00-latest.xml.gz \
    ${BATCH_ROOT}/gene_mapping/consequences_2_vep.tsv

# Unite results from the previous two steps.
cat \
  ${BATCH_ROOT}/gene_mapping/consequences_1_repeat.tsv \
  ${BATCH_ROOT}/gene_mapping/consequences_2_vep.tsv \
  > ${BATCH_ROOT}/gene_mapping/consequences_3_combined.tsv

# Generate the evidence strings for submission to Open Targets.
${BSUB_CMDLINE} -K -M 10G \
  -o ${BATCH_ROOT}/logs/evidence_string_generation.out \
  -e ${BATCH_ROOT}/logs/evidence_string_generation.err \
  python3 ${CODE_ROOT}/bin/evidence_string_generation.py \
    --clinvar-xml  ${BATCH_ROOT}/clinvar/ClinVarFullRelease_00-latest.xml.gz \
    --efo-mapping  ${BATCH_ROOT_BASE}/manual_curation/latest_mappings.tsv \
    --gene-mapping ${BATCH_ROOT}/gene_mapping/consequences_3_combined.tsv \
    --ot-schema    ${BATCH_ROOT}/evidence_strings/opentargets-${OT_SCHEMA_VERSION}.json \
    --out          ${BATCH_ROOT}/evidence_strings/

# Check that the generated evidence strings do not contain any duplicated evidence strings. For every evidence string, we group the value of fields datatypeId, studyId, targetFromSourceId, variantFunctionalConsequenceId and diseaseFromSourceMappedId, all separated by tabs, sorted and saved at duplicates.json if found duplicated. 
jq --arg sep $'\t' -jr \
  '.datatypeId,$sep,.studyId,$sep,.targetFromSourceId,$sep,.variantFunctionalConsequenceId,$sep,.diseaseFromSourceMappedId,$sep,.diseaseFromSource,"\n"' \
  ${BATCH_ROOT}/evidence_strings/evidence_strings.json \
  | sort | uniq -d > ${BATCH_ROOT}/evidence_strings/duplicates.json

# Convert MedGen and OMIM cross-references into ZOOMA format.
${BSUB_CMDLINE} -K \
  -o ${BATCH_ROOT}/logs/traits_to_zooma_format.out \
  -e ${BATCH_ROOT}/logs/traits_to_zooma_format.err \
  python3 ${CODE_ROOT}/bin/traits_to_zooma_format.py \
    --clinvar-xml    ${BATCH_ROOT}/clinvar/ClinVarFullRelease_00-latest.xml.gz \
    --zooma-feedback ${BATCH_ROOT}/clinvar/clinvar_xrefs.txt
```

## 3. Manual follow-up actions

### Check that generated evidence strings do not contain any duplicates
The algorithm used for generating the evidence strings should not allow any duplicate values to be emitted, and the file `${BATCH_ROOT}/evidence_strings/duplicates.json` should be empty. Check that this is the case.

A repeated evidence string will have identical values for these five fields:
* **datatypeId** - Identifier of the type of data we are associating, varying between somatic and non-somatic ClinVar records (*e.g.* ``somatic_mutation`` or ``genetic_association`` respectively). 
* **studyId** - Reference ClinVar record (*e.g.* ``RCV000015714``).
* **targetFromSourceId** - The gene affected by the variant (*e.g.* ``ENSG00000186832``). 
* **variantFunctionalConsequenceId** - The consequence of such variant (*e.g.* ``SO_0001818``, which corresponds to protein_altering_variant). 
* **diseaseFromSourceMappedId** - Associated phenotype to such variant (*e.g.* ``Orphanet_2337``, which corresponds to a type of keratoderma). 

Nevertheless, we also report evidence strings in which  ``diseaseFromSourceMappedId`` may be empty (``diseaseFromSourceMappedId: null``) - i.e. the phenotype has not been mapped to an ontology yet. Therefore, to check for duplicates we also take into account the field ``diseaseFromSource``, which is the string describing the phenotype within ClinVar records (and is never missing in any evidence string).  

### Update summary metrics
After the evidence strings have been generated, summary metrics need to be updated in the Google Sheets [table](https://docs.google.com/spreadsheets/d/1g_4tHNWP4VIikH7Jb0ui5aNr0PiFgvscZYOe69g191k/) on the “Raw statistics” sheet.

### Submit evidence strings
The evidence string file (`evidence_strings.json`) must be uploaded to the [Open Targets Google Cloud Storage](https://console.cloud.google.com/storage/browser/otar012-eva/) and be named in the format `cttv012-[yyyy]-[mm]-[dd].json.gz` (e.g. `cttv012-2020-10-21.json.gz`).

More details can be found on [Open Targets Github wiki](https://github.com/opentargets/data_release/wiki/OT006-Data-Submission#ot009-evidence-string-generation-json-schema-validation--submission).

### Submit feedback to ZOOMA
The idea with [ZOOMA](http://www.ebi.ac.uk/spot/zooma/) is that we not only use it, but also provide feedback to help improve it. The evidence string generation pipeline generates two files with such a feedback:
1. **clinvar_xrefs.** ClinVar data already includes some cross-links from trait names to disease ontologies. Unfortunately, it almost exclusively uses MedGen and OMIM, which are not acceptable for Open Targets (since they're using EFO). However, mappings from trait names to MedGen and OMIM might still be useful to other users. Hence, we extract and submit them to ZOOMA under the evidence handle “ClinVar_xRefs”.
1. **eva_clinvar.** This contains the trait mappings (to EFO) created during the evidence string generation, including automated and manual mappings.

The files are uploaded to the FTP, where ZOOMA will pick it up. At this stage, you only need to upload the **clinvar_xrefs** dataset (the *eva_clinvar* dataset is updated in the process of the manual curation).

To make changes to the FTP, you will need to log in to the cluster using your **personal account** and then you will need to have set up the common environment like in step 1.
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
    - The `${BATCH_ROOT}/logs/consequence_repeat_expansion.err` log will record all repeat expansion variants which could not be parsed using any of the regular expressions. Verify that there are no new such variants compared to the previous batch.
  + Evidence stringts
    - Version of JSON schema is the same as specified in the Open Targets e-mail
    - All traits mentioned in the [spreadsheet](https://docs.google.com/spreadsheets/d/1m4ld3y3Pfust5JSOJOX9ZmImRCKRGi-fGYj_dExoGj8/edit) are mapped to the correct ontology terms in `${BATCH_ROOT_BASE}/manual_curation/latest_mappings.tsv`.
    - The file `${BATCH_ROOT}/evidence_strings/duplicates.json` is empty, meaning there are no duplicates in the generated evidence strings.
* Step 5 “Manual follow-up actions”
  + The summary metrics
    - Are present in the [spreadsheet](https://docs.google.com/spreadsheets/d/1g_4tHNWP4VIikH7Jb0ui5aNr0PiFgvscZYOe69g191k/)
    - Are calculated correctly (re-calculate using the commands in the spreadsheet as required)
    - Are not worse than for the previous release
  + Generated evidence strings validate against the schema
    - Have actually been submitted to the Open Targets cloud storage
    - The file is the same as on the cluster (check md5)
    - E-mail has been sent to Open Targets, with eva-dev in copy
  + ZOOMA feedback (the FTP path is http://ftp.ebi.ac.uk/pub/databases/eva/ClinVar/latest; to see where files are located on the cluster, see variable `BATCH_ROOT_BASE` on [this page](https://github.com/EBIvariation/configuration/blob/master/open-targets-configuration.md))
    - The changes have been propagated to the FTP, and the files available over FTP are the same as on the cluster
    - The files in the `YYYY/MM/DD` and in the `latest` folders are identical (using either symlinks or copied)
