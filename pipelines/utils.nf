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
