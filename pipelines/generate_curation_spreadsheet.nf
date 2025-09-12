#!/usr/bin/env nextflow

nextflow.enable.dsl=2

include { getTargetOntology } from './utils.nf'


def helpMessage() {
    log.info"""
    Generate automated trait mappings and table for manual curation.

    Params:
        --curation_root     Directory for current batch
        --clinvar           ClinVar XML file (optional, will download latest if omitted)
        --mappings          Current mappings file (optional, will use a default path if omitted)
        --comments          Current curator comments file (optional, will use a default path if omitted)
        --chunk_size        Chunk size to split traits into (default 1000)
        --max_forks         Max number of processes to run in parallel (default 10)
    """
}

params.help = null
params.curation_root = null
params.clinvar = null
params.mappings = "\${BATCH_ROOT_BASE}/manual_curation/latest_mappings.tsv"
params.comments = "\${BATCH_ROOT_BASE}/manual_curation/latest_comments.tsv"
params.chunk_size = 1000
params.max_forks = 10

if (params.help) {
    exit 0, helpMessage()
}
if (!params.curation_root) {
    exit 1, helpMessage()
}
curationRoot = params.curation_root
codeRoot = "${projectDir}/.."


/*
 * Main workflow.
 */
workflow {
    if (params.clinvar != null) {
        clinvarXml = Channel.fromPath(params.clinvar)
    } else {
        clinvarXml = downloadClinvar()
    }
    getTargetOntology(params.mappings)
    parseTraits(clinvarXml)
    splitTraits(parseTraits.out.parsedTraits)
    processTraits(splitTraits.out.traitChunk.flatten(), getTargetOntology.out.targetOntology)
    collectAutomatedMappings(processTraits.out.automatedTraits.collect())
    collectCurationTraits(processTraits.out.traitsForCuration.collect())
    createCurationTable(collectCurationTraits.out.curationTraits)
}

/*
 * Download ClinVar data, using the most recent XML dump.
 */
process downloadClinvar {
    label 'small_mem'

    output:
    path "clinvar.xml.gz", emit: clinvarXml

    script:
    """
    wget -O clinvar.xml.gz \
        https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/RCV_release/ClinVarRCVRelease_00-latest.xml.gz
    """
}

/*
 * Parse traits from ClinVar XML.
 */
process parseTraits {
    input:
    path clinvarXml

    output:
    path "parsed_traits.csv", emit: parsedTraits

    script:
    """
    \${PYTHON_BIN} ${codeRoot}/bin/trait_mapping/parse_traits.py \
        -i ${clinvarXml} \
        -o parsed_traits.csv
    """
}

/*
 * Split parsed traits into multiple chunks.
 */
process splitTraits {
    label 'short_time'
    label 'small_mem'

    input:
    path parsedTraits

    output:
    path("parsed_traits-*", emit: traitChunk)

    script:
    """
    split -a 5 -d -l ${params.chunk_size} ${parsedTraits} parsed_traits-
    """
}

/*
 * Process traits through Zooma and OLS.
 */
process processTraits {
    maxForks params.max_forks
    errorStrategy 'finish'

    input:
    each path(traitChunk)
    val targetOntology

    output:
    path "automated_traits_*.tsv", emit: automatedTraits
    path "curation_traits_*.tsv", emit: traitsForCuration

    script:
    // If targetOntology is anything but EFO, we set the query ontologies for Zooma and OxO to be the same,
    // and do not use the data sources search option for Zooma.
    def queryOntologyFlag = targetOntology.equalsIgnoreCase("EFO")? "" : "-n ${targetOntology.toLowerCase()} -t ${targetOntology.toLowerCase()} -r none"
    """
    \${PYTHON_BIN} ${codeRoot}/bin/trait_mapping/process_traits.py \
        -i ${traitChunk} \
        --target-ontology ${targetOntology} \
        ${queryOntologyFlag} \
        -o automated_traits_${traitChunk}.tsv \
        -c curation_traits_${traitChunk}.tsv
    """
}

/*
 * Aggregate automated trait mappings into a single file.
 */
process collectAutomatedMappings {
    label 'short_time'
    label 'small_mem'
    publishDir "${curationRoot}",
        overwrite: true,
        mode: "copy",
        pattern: "*.tsv"

    input:
    path "automated_traits_*.tsv"

    output:
    path "automated_trait_mappings.tsv", emit: automatedTraits

    script:
    """
    cat automated_traits_*.tsv >> automated_trait_mappings.tsv
    """
}

/*
 * Aggregate traits for manual curation into a single file.
 */
process collectCurationTraits {
    label 'short_time'
    label 'small_mem'

    input:
    path "curation_traits_*.tsv"

    output:
    path "traits_requiring_curation.tsv", emit: curationTraits

    script:
    """
    cat *.tsv > traits_requiring_curation.tsv
    """
}

/*
 * Create the table for manual curation.
 */
process createCurationTable {
    publishDir "${curationRoot}",
        overwrite: true,
        mode: "copy",
        pattern: "*.tsv"

    input:
    path curationTraits

    output:
    path "google_sheets_table.tsv", emit: curationTable

    script:
    """
    \${PYTHON_BIN} ${codeRoot}/bin/trait_mapping/create_table_for_manual_curation.py \
        --traits-for-curation ${curationTraits} \
        --previous-mappings ${params.mappings} \
        --previous-comments ${params.comments} \
        --output google_sheets_table.tsv
    """
}
