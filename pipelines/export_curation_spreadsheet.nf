#!/usr/bin/env nextflow

nextflow.enable.dsl=2


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
if (!params.curation_root || !params.input_csv) {
    exit 1, helpMessage()
}
curationRoot = params.curation_root
codeRoot = "${projectDir}/.."


/*
 * Main workflow.
 */
workflow {
    exportTable()
    createLatestMappings(
        Channel.of("${curationRoot}/automated_trait_mappings.tsv"),
        exportTable.out.finishedMappings,
        Channel.of(params.mappings)
    )

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
 * Create latest mappings file.
 */
process createLatestMappings {
    label 'default_time'
    label 'small_mem'

    publishDir "${curationRoot}",
        overwrite: true,
        mode: "copy",
        pattern: "*.tsv"

    input:
    val automatedMappings
    path curatedMappings
    val previousMappings

    output:
    path "trait_names_to_ontology_mappings.tsv", emit: finalMappings
    path "obsolete_mappings.tsv", emit: obsoleteMappings

    script:
    """
    \${PYTHON_BIN} ${codeRoot}/bin/trait_mapping/create_latest_mappings.py \
        --automated ${automatedMappings} \
        --curated ${curatedMappings} \
        --previous ${previousMappings}
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
