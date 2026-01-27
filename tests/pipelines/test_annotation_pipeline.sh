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

nextflow run ${CODE_ROOT}/pipelines/annotation_pipeline.nf \
  --output_dir ${BATCH_ROOT} \
  --schema $(cat "${CODE_ROOT}/OT_SCHEMA_VERSION") \
  --clinvar ${BATCH_ROOT_BASE}/input.xml.gz \
  -resume

diff ${BATCH_ROOT}/gene_mapping/consequences_snp.tsv ${BATCH_ROOT_BASE}/expected/consequences_snp.tsv
diff ${BATCH_ROOT}/gene_mapping/consequences_repeat.tsv ${BATCH_ROOT_BASE}/expected/consequences_repeat.tsv
diff ${BATCH_ROOT}/gene_mapping/consequences_structural.tsv ${BATCH_ROOT_BASE}/expected/consequences_structural.tsv
diff ${BATCH_ROOT}/logs/removed_mappings.tsv ${BATCH_ROOT_BASE}/expected/removed_mappings.tsv
# Nextflow parallelism means ordering might not be stable
diff <(sort ${BATCH_ROOT}/evidence_strings/evidence_strings.json) <(sort ${BATCH_ROOT_BASE}/expected/evidence_strings.json)

cd ${CWD}
rm -r ${BATCH_ROOT}
