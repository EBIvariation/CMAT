#!/bin/bash

set -Eeuo pipefail
export LC_COLLATE=C

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
export CODE_ROOT="$(dirname $(dirname "${SCRIPT_DIR}"))"

export BATCH_ROOT_BASE=${SCRIPT_DIR}/resources

CWD=${PWD}
BATCH_ROOT=${BATCH_ROOT_BASE}/test_batch
mkdir -p ${BATCH_ROOT}
cd ${BATCH_ROOT}

nextflow run ${CODE_ROOT}/pipelines/generate_curation_spreadsheet.nf \
  --curation_root ${BATCH_ROOT} \
  --clinvar ${BATCH_ROOT_BASE}/input.xml.gz \
  -resume

sort -o ${BATCH_ROOT}/automated_trait_mappings.tsv ${BATCH_ROOT}/automated_trait_mappings.tsv
diff ${BATCH_ROOT}/automated_trait_mappings.tsv ${BATCH_ROOT_BASE}/expected/automated_trait_mappings.tsv
diff ${BATCH_ROOT}/google_sheets_table.tsv ${BATCH_ROOT_BASE}/expected/google_sheets_table.tsv

nextflow run ${CODE_ROOT}/pipelines/export_curation_spreadsheet.nf \
  --curation_root ${BATCH_ROOT} \
  --input_csv ${BATCH_ROOT_BASE}/finished_curation_spreadsheet.csv \
  -resume

diff ${BATCH_ROOT}/curator_comments.tsv ${BATCH_ROOT_BASE}/expected/curator_comments.tsv
diff -I '^#generated-date' ${BATCH_ROOT}/trait_names_to_ontology_mappings.tsv ${BATCH_ROOT_BASE}/expected/trait_names_to_ontology_mappings.tsv

cd ${CWD}
rm -r ${BATCH_ROOT}
