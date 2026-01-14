/*
 * Extract target ontology from mappings file header. Defaults to EFO if missing.
 */
process getTargetOntology {
    label 'short_time'
    label 'small_mem'

    input:
    val mappingsFile

    output:
    env ONTOLOGY, emit: targetOntology

    script:
    """
    ONTOLOGY=\$(grep '^#ontology=' ${mappingsFile} | sed 's/#ontology=//g')
    ONTOLOGY=\${ONTOLOGY:-EFO}
    """
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
 * Download the Open Targets JSON schema.
 */
process downloadJsonSchema {
    label 'short_time'
    label 'small_mem'

    input:
    val schemaVersion

    output:
    path "opentargets-${schemaVersion}.json", emit: jsonSchema

    script:
    """
    wget -O opentargets-${schemaVersion}.json \
        https://raw.githubusercontent.com/opentargets/json_schema/${schemaVersion}/schemas/disease_target_evidence.json
    """
}
