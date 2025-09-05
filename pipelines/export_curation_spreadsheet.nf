#!/usr/bin/env nextflow

nextflow.enable.dsl=2

include { getTargetOntology } from './utils.nf'


def helpMessage() {
    log.info"""
    Export manual curation table.

    Params:
        --curation_root     Directory for current batch
        --input_csv         Input csv file
        --mappings          Current mappings file (optional, will use a default path if omitted)
        --with_feedback     Whether to generate EFO/Zooma feedback and final symlinking (default false)
    """
}

params.help = null
params.curation_root = null
params.input_csv = null
params.mappings = "\${BATCH_ROOT_BASE}/manual_curation/latest_mappings.tsv"
params.with_feedback = false

if (params.help) {
    exit 0, helpMessage()
}
if (!params.curation_root or !params.input_csv) {
    exit 1, helpMessage()
}
curationRoot = params.curation_root
codeRoot = "${projectDir}/.."


/*
 * Main workflow.
 */
workflow {
    exportTable()
    combineManualAndAutomated(exportTable.out.finishedMappings)
    getTargetOntology(params.mappings)
    stripMappingsHeader()
    mergeWithLatestMappings(combineManualAndAutomated.out.newMappings, stripMappingsHeader.out.previousMappings)
    checkDuplicates(mergeWithLatestMappings.out.newMappings)
    addMappingsHeader(checkDuplicates.out.duplicatesOk, mergeWithLatestMappings.out.newMappings, getTargetOntology.out.targetOntology)
    if (params.with_feedback) {
        generateZoomaFeedback(addMappingsHeader.out.finalMappings)
        updateLinks(addMappingsHeader.out.finalMappings, generateZoomaFeedback.out.zoomaFeedback)
    }
}

/*
 * Extract the relevant columns from the input CSV.
 */
process exportTable {
    label 'short_time'
    label 'small_mem'

    publishDir "${curationRoot}",
        overwrite: true,
        mode: "copy",
        pattern: "curator_comments.tsv"

    output:
    path "finished_mappings_curation.tsv", emit: finishedMappings
    path "curator_comments.tsv", emit: curatorComments

    script:
    """
    \${PYTHON_BIN} ${codeRoot}/bin/trait_mapping/export_curation_table.py \
        -i ${params.input_csv} \
        -d finished_mappings_curation.tsv \
        -c curator_comments.tsv
    """
}

/*
 * Strip header from existing mappings file.
 */
 process stripMappingsHeader {
    label 'short_time'
    label 'small_mem'

    output:
    path "previous_mappings.tsv", emit: previousMappings

    script:
    """
    grep -v "^#" ${params.mappings} > previous_mappings.tsv
    """
 }

/*
 * Concatenate finished automated and manual mappings into a single file.
 */
process combineManualAndAutomated {
    label 'short_time'
    label 'small_mem'

    input:
    path finishedMappings

    output:
    path "mappings_no_header.tsv", emit: newMappings

    script:
    """
    cat ${curationRoot}/automated_trait_mappings.tsv ${finishedMappings} \
        | sort -u > mappings_no_header.tsv
    """
}

/*
 * Add all mappings from the database which are *not* present in the results of the current curation iteration (automated
 * + manually curated). This is done in order to never lose mappings, even if they are not present in ClinVar during the
 * latest curation iteration.
 */
process mergeWithLatestMappings {
    label 'short_time'
    label 'small_mem'

    input:
    path newMappings
    path previousMappings

    output:
    path newMappings, emit: newMappings

    script:
    """
    # The first file operand is the list of mappings in the current database; and the second is the list of trait names
    # which are only present in the existing database and not in the new mappings.
    export LC_ALL=C
    join -j 1 -t \$'\t' \
        <(sort -t \$'\t' -k 1,1 ${previousMappings}) \
        <(comm -23 <(cut -d \$'\t' -f 1 ${previousMappings} | sort -u) <(cut -d \$'\t' -f 1 ${newMappings} | sort -u)) \
    >> ${newMappings}
    """
}

/*
 * Generate ZOOMA feedback.
 */
process generateZoomaFeedback {
    label 'short_time'
    label 'small_mem'
    publishDir "${curationRoot}",
        overwrite: true,
        mode: "copy",
        pattern: "*.txt"

    input:
    path newMappings

    output:
    path "eva_clinvar.txt", emit: zoomaFeedback

    script:
    """
    echo -e 'STUDY\tBIOENTITY\tPROPERTY_TYPE\tPROPERTY_VALUE\tSEMANTIC_TAG\tANNOTATOR\tANNOTATION_DATE' \
        > eva_clinvar.txt
    tail -n+3 ${newMappings} \
        | cut -f-2 \
        | sort -t\$'\t' -k1,1 \
        | awk -F\$'\t' -vDATE="\$(date +'%y/%m/%d %H:%M')" '{print "\t\tdisease\t" \$1 "\t" \$2 "\teva\t" DATE}' \
    >> eva_clinvar.txt
    """
}

/*
 * Check there are no complete duplicates in the final mappings file.
 */
process checkDuplicates {
    label 'short_time'
    label 'small_mem'

    input:
    path newMappings

    output:
    val true, emit: duplicatesOk  // ensure we don't do the final linking if this check fails

    script:
    """
    sort ${newMappings} | uniq -c | awk '\$1 > 1' > duplicates.tsv
    [[ ! -s duplicates.tsv ]]
    """
}

/*
 * Add generated date and target ontology to header of final mappings file.
 */
process addMappingsHeader {
    label 'short_time'
    label 'small_mem'
    publishDir "${curationRoot}",
        overwrite: true,
        mode: "copy",
        pattern: "*.tsv"

    input:
    val duplicatesOk
    path newMappings
    val targetOntology

    output:
    path "trait_names_to_ontology_mappings.tsv", emit: finalMappings

    script:
    """
    printf '#generated-date=%(%Y-%m-%d)T\n' > trait_names_to_ontology_mappings.tsv
    printf '#ontology=${targetOntology}\n' >> trait_names_to_ontology_mappings.tsv
    printf '#clinvar_trait_name\turi\tlabel\n' >> trait_names_to_ontology_mappings.tsv
    cat ${newMappings} >> trait_names_to_ontology_mappings.tsv
    """
}

/*
 * Update the symbolic links pointing to the location of the most recent curation result and ZOOMA feedback dataset.
 */
process updateLinks {
    label 'short_time'
    label 'small_mem'

    input:
    path finalMappings
    path zoomaFeedback

    script:
    """
    ln -s -f ${curationRoot}/trait_names_to_ontology_mappings.tsv \${BATCH_ROOT_BASE}/manual_curation/latest_mappings.tsv
    ln -s -f ${curationRoot}/eva_clinvar.txt \${BATCH_ROOT_BASE}/manual_curation/eva_clinvar.txt
    ln -s -f ${curationRoot}/curator_comments.tsv \${BATCH_ROOT_BASE}/manual_curation/latest_comments.tsv
    """
}
