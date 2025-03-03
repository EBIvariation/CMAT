import logging
import itertools
import json
import re
import sys
import os
from collections import defaultdict

import jsonschema

from cmat.clinvar_xml_io import ClinVarDataset
from cmat.clinvar_xml_io.clinical_classification import MultipleClinicalClassificationsError
from cmat.clinvar_xml_io.filtering import filter_by_submission
from cmat.output_generation import consequence_type as CT
from cmat.output_generation.report import Report

logger = logging.getLogger(__package__)

# A regular expression to detect alleles with IUPAC ambiguity bases.
IUPAC_AMBIGUOUS_SEQUENCE = re.compile(r'[^ACGT]')

# If a structural variant has more than this number of target genes, we omit it as too broad in consequences.
MAX_TARGET_GENES = 3

# Output file names.
EVIDENCE_STRINGS_FILE_NAME = 'evidence_strings.json'
EVIDENCE_RECORDS_FILE_NAME = 'evidence_records.tsv'


def validate_evidence_string(ev_string, ot_schema_contents):
    try:
        jsonschema.validate(ev_string, ot_schema_contents, format_checker=jsonschema.FormatChecker())
        return True
    except jsonschema.exceptions.ValidationError as err:
        logger.error('Error: evidence string does not validate against schema.')
        logger.error(f'Error message: {err}')
        logger.error(f'Complete evidence string: {json.dumps(ev_string)}')
        return False
    except jsonschema.exceptions.SchemaError:
        logger.error('Error: OpenTargets schema file is invalid')
        sys.exit(1)


def launch_pipeline(clinvar_xml_file, efo_mapping_file, gene_mapping_file, ot_schema_file, dir_out, start, end):
    os.makedirs(dir_out, exist_ok=True)
    string_to_efo_mappings, _ = load_ontology_mapping(efo_mapping_file)
    variant_to_gene_mappings = CT.process_consequence_type_file(gene_mapping_file)

    report, exception_raised = clinvar_to_evidence_strings(
        string_to_efo_mappings, variant_to_gene_mappings, clinvar_xml_file, ot_schema_file,
        output_evidence_strings=os.path.join(dir_out, EVIDENCE_STRINGS_FILE_NAME), start=start, end=end)
    counts_consistent = report.check_counts()
    report.print_report()
    report.dump_to_file(dir_out)
    if exception_raised or not counts_consistent:
        sys.exit(1)


def clinvar_to_evidence_strings(string_to_efo_mappings, variant_to_gene_mappings, clinvar_xml, ot_schema,
                                output_evidence_strings, start=None, end=None):
    report = Report(trait_mappings=string_to_efo_mappings, consequence_mappings=variant_to_gene_mappings)
    ot_schema_contents = json.loads(open(ot_schema).read())
    output_evidence_strings_file = open(output_evidence_strings, 'wt')
    exception_raised = False

    logger.info('Processing ClinVar records')
    i = -1
    dataset = ClinVarDataset(clinvar_xml)
    for clinvar_set in dataset.iter_cvs():
        # If start & end provided, only process records in the range [start, end)
        i += 1
        if start and i < start:
            continue
        if end and i >= end:
            break

        report.clinvar_total += 1
        if report.clinvar_total % 1000 == 0:
            logger.info(f'{report.clinvar_total} records processed')

        # Catch any exceptions for this record so we can continue processing.
        try:
            # Failure mode 1 (fatal). Record is only supported by submissions deemed to be unusable.
            if not filter_by_submission(clinvar_set):
                report.clinvar_fatal_excluded_submission += 1
                continue
            clinvar_record = clinvar_set.rcv

            # Failure mode 2 (skip). Contains multiple clinical classification annotations.
            # This is new as of V2 of the ClinVar XSD and should definitely be supported at some point,
            # but as it can cause parsing complications we catch these cases first.
            # See GH issue for context: https://github.com/EBIvariation/CMAT/issues/396
            if len(clinvar_record.clinical_classifications) > 1:
                logger.warning(f'Found multiple clinical classifications in record {clinvar_record.accession}')
                report.clinvar_skip_multiple_clinical_classifications += 1
                continue

            # Failure mode 3 (fatal). A ClinVar record contains no valid traits (traits which have at least one valid,
            # potentially mappable name).
            if not clinvar_record.traits_with_valid_names:
                report.clinvar_fatal_no_valid_traits += 1
                continue
            # Failure mode 4 (fatal). A ClinVar record contains no valid clinical significance terms, likely due to
            # submissions being flagged.
            if not clinvar_record.valid_clinical_significances:
                report.clinvar_fatal_no_clinical_significance += 1
                continue

            # Failure mode 5 (skip). A ClinVar record contains an unsupported variation type.
            if clinvar_record.measure is None:
                report.clinvar_skip_unsupported_variation += 1
                continue

            # Within each ClinVar record, an evidence string is generated for all possible permutations of (1) valid
            # allele origins, (2) EFO mappings, and (3) genes where the variant has effect.
            grouped_allele_origins = convert_allele_origins(clinvar_record.valid_allele_origins)
            consequence_types, _ = get_consequence_types(clinvar_record.measure, variant_to_gene_mappings)
            grouped_diseases = group_diseases_by_efo_mapping(clinvar_record.traits_with_valid_names,
                                                             string_to_efo_mappings)

            # Failure mode 6 (skip). No functional consequences are available.
            if not consequence_types:
                report.clinvar_skip_no_functional_consequences += 1
                continue

            # Gather consequence mapping counts for variants of interest
            if clinvar_record.measure.is_repeat_expansion_variant:
                report.repeat_expansion_variants += len(consequence_types)
            if is_structural_variant(clinvar_record.measure):
                report.structural_variants += len(consequence_types)

            # Failure mode 7 (skip). A ClinVar record has at least one trait with at least one valid name, but no
            # suitable EFO mappings were found in the database. This will still generate an evidence string, but is
            # tracked as a failure so we can continue to measure mapping coverage.
            if not contains_mapping(grouped_diseases):
                report.clinvar_skip_missing_efo_mapping += 1
                unmapped_trait_name = clinvar_record.traits_with_valid_names[0].preferred_or_other_valid_name
                report.unmapped_trait_names[unmapped_trait_name] += 1

            assert grouped_allele_origins and grouped_diseases and consequence_types, \
                'Some of the attribute lists are still empty even after passing all checks.'

            complete_evidence_strings_generated = 0
            evidence_strings_generated = 0
            for allele_origins, disease_attributes, consequence_attributes in itertools.product(
                    grouped_allele_origins, grouped_diseases, consequence_types):
                disease_name, disease_source_id, disease_mapped_efo_id = disease_attributes
                evidence_string = generate_evidence_string(clinvar_record, allele_origins, disease_name,
                                                           disease_source_id, disease_mapped_efo_id,
                                                           consequence_attributes)

                # Validate and immediately output the evidence string (not keeping everything in memory).
                is_valid = validate_evidence_string(evidence_string, ot_schema_contents)
                if is_valid:
                    output_evidence_strings_file.write(json.dumps(evidence_string) + '\n')

                    # Record some evidence string and trait metrics.
                    evidence_strings_generated += 1
                    if disease_mapped_efo_id is not None:
                        complete_evidence_strings_generated += 1
                        report.used_trait_mappings.add(disease_mapped_efo_id)

            if complete_evidence_strings_generated == 1:
                report.clinvar_done_one_complete_evidence_string += 1
            elif complete_evidence_strings_generated > 1:
                report.clinvar_done_multiple_complete_evidence_strings += 1

            if evidence_strings_generated == 0:
                report.clinvar_skip_invalid_evidence_string += 1
                # If this record also did not have any EFO-mapped traits, it has already been counted as "skip".
                # Correct this so the counts match up but we retain the more important skip reason.
                if not contains_mapping(grouped_diseases):
                    report.clinvar_skip_missing_efo_mapping -= 1

            report.complete_evidence_string_count += complete_evidence_strings_generated
            report.evidence_string_count += evidence_strings_generated

        except MultipleClinicalClassificationsError as mcce:
            # Ensure we catch any of these that fall through (e.g. from multiple description text)
            logger.error(str(mcce))
            report.clinvar_skip_multiple_clinical_classifications += 1

        except Exception as e:
            # We catch exceptions but record when one is thrown, so that the pipeline will crash after processing all
            # records and printing the report.
            logger.error(f'Problem generating evidence for {clinvar_set.rcv.accession}')
            logger.error(f'Error: {repr(e)}')
            exception_raised = True
            continue

    output_evidence_strings_file.close()
    return report, exception_raised


def format_creation_date(s):
    if not s:
        return None
    m = re.search('\d{4}-\d{2}-\d{2}', s)
    if m and m.group(0):
        return m.group(0)
    return None


def generate_evidence_string(clinvar_record, allele_origins, disease_name, disease_source_id, disease_mapped_efo_id,
                             consequence_attributes):
    """Generates an evidence string based on ClinVar record and some additional attributes."""
    is_somatic = allele_origins == ['somatic']
    evidence_string = {
        # ALLELE ORIGIN ATTRIBUTES. There are three attributes which are currently completely redundant (their
        # values are completely correlated between each other). This is intended, see answer to question 1 here:
        # https://github.com/EBIvariation/eva-opentargets/issues/189#issuecomment-782136128.
        'alleleOrigins': allele_origins,
        'datasourceId': 'eva_somatic' if is_somatic else 'eva',
        'datatypeId': 'somatic_mutation' if is_somatic else 'genetic_association',

        # ASSOCIATION ATTRIBUTES.
        # List of patterns of inheritance reported for the variant.
        'allelicRequirements': clinvar_record.mode_of_inheritance,

        # Levels of clinical significance reported for the variant.
        'clinicalSignificances': clinvar_record.valid_clinical_significances,

        # Confidence (review status).
        'confidence': clinvar_record.review_status,

        # Literature. ClinVar records provide three types of references: trait-specific; variant-specific; and
        # "observed in" references. Open Targets are interested only in that last category.
        'literature': sorted(set([str(r) for r in clinvar_record.evidence_support_pubmed_refs])),

        # RCV identifier.
        'studyId': clinvar_record.accession,

        # Record creation date, formatted as YYYY-MM-DD
        'releaseDate': format_creation_date(clinvar_record.created_date),

        # VARIANT ATTRIBUTES.
        'targetFromSourceId': consequence_attributes.ensembl_gene_id,
        'variantFunctionalConsequenceId': consequence_attributes.so_term.accession,
        'variantId': clinvar_record.measure.vcf_full_coords,  # CHROM_POS_REF_ALT notation.
        'variantRsId': clinvar_record.measure.rs_id,
        'variantFromSourceId': clinvar_record.vcv_id,

        # PHENOTYPE ATTRIBUTES.
        # The alphabetical list of *all* valid disease names from all traits from that ClinVar record, reported as a
        # flat list. See https://github.com/EBIvariation/eva-opentargets/issues/221 for a discussion of this choice.
        'cohortPhenotypes': sorted({name for trait in clinvar_record.traits_with_valid_names for name in trait.all_valid_names}),

        # One disease name for this evidence string (see group_diseases_by_efo_mapping).
        'diseaseFromSource': disease_name,

        # The internal identifier of that disease.
        'diseaseFromSourceId': disease_source_id,

        # The EFO identifier to which we mapped that first disease. Converting the URI to a compact representation as
        # required by the Open Targets JSON schema.
        'diseaseFromSourceMappedId': disease_mapped_efo_id.split('/')[-1] if disease_mapped_efo_id else None,
    }
    if clinvar_record.measure.preferred_current_hgvs:
        evidence_string['variantHgvsId'] = clinvar_record.measure.preferred_current_hgvs.text

    # Remove the attributes with empty values (either None or empty lists).
    evidence_string = {key: value for key, value in evidence_string.items() if value}
    return evidence_string


def get_consequence_types(clinvar_record_measure, consequence_type_dict):
    """Returns the list of functional consequences for a given ClinVar record measure.

    This is the place where ClinVar records are paired with the information about gene and functional consequences.
    This information is produced by two pipelines in the `consequence_prediction` subdirectory:
    1. The main one, `vep_mapping_pipeline`, runs all records in the ClinVar XML dump through Variant Effect Predictor
       and outputs the results using a VCF-compatible "CHROM:POS:REF:ALT" identifier.
    2. The auxiliary one, `repeat_expansion_variants`, uses a different approach to extract information about repeat
       expansion variants from the ClinVar XML dump. The repeat expansion variants have several important features:
       a. Even the variants which have the coordinates cannot be adequately processed by VEP: it will output the wrong
          functional consequence type.
       b. The "CHROM:POS:REF:ALT" notation is not useful for these variants, because some of them have an indeterminate
          number of repeats, hence there is no single ALT allele.
       This second pipeline outputs the results using the RCV identifier from ClinVar."""

    # As the first option, try to link a variant and its functional consequence by RCV accession. This will only happen
    # for repeat expansion variants, since the main pipeline uses CHROM:POS:REF:ALT identifiers.
    #
    # The reason we don't use RCV accessions more often is because they are, in general, not variant-specific: the same
    # RCV may link to multiple variants with different functional consequences. However, for repeat expansion variants
    # RCV accessions *are* specific and contain only one variant.
    #
    # The reason we pair first by RCV accession and *then* by CHROM:POS:REF:ALT identifiers is that some repeat
    # expansion variants will be fed to VEP and will receive incorrect consequence annotations. By using RCV pairing
    # first, we prioritise results of the variant expansion pipeline over the general VEP pipeline.
    if clinvar_record_measure.clinvar_record.accession in consequence_type_dict:
        return consequence_type_dict[clinvar_record_measure.clinvar_record.accession], 'REPEAT'

    # If RCV is not present in the consequences file, pair using full variant description (CHROM:POS:REF:ALT)
    if clinvar_record_measure.has_complete_coordinates:
        # This VCF-flavoured identifier is used to pair ClinVar records with functional consequence predictions.
        # Example of such an identifier: 14:23423715:G:A.
        coord_id = ':'.join([clinvar_record_measure.chr, str(clinvar_record_measure.vcf_pos),
                             clinvar_record_measure.vcf_ref, clinvar_record_measure.vcf_alt])
        # Log unusual variants with IUPAC ambiguity symbols. Example: 12_32625716_G_H (from RCV000032000).
        if IUPAC_AMBIGUOUS_SEQUENCE.search(clinvar_record_measure.vcf_ref + clinvar_record_measure.vcf_alt):
            logger.warning(f'Observed variant with non-ACGT allele sequences: {coord_id}')
        if coord_id in consequence_type_dict:
            return consequence_type_dict[coord_id], 'SIMPLE'

    # If there's also no complete coordinates, pair using HGVS
    if clinvar_record_measure.preferred_current_hgvs:
        hgvs_id = clinvar_record_measure.preferred_current_hgvs.text
        if hgvs_id in consequence_type_dict:
            consequences = consequence_type_dict[hgvs_id]
            if len(consequences) > MAX_TARGET_GENES:
                logger.warning(f'Skipping variant {hgvs_id} with {len(consequences)} target genes')
                return [], 'NONE'
            return consequences, 'COMPLEX'

    # Previously, the pairing was also attempted based on rsID and nsvID. This is not reliable because of lack of allele
    # specificity, and has been removed.
    return [], 'NONE'


def write_string_list_to_file(string_list, filename):
    with open(filename, 'wt') as out_file:
        out_file.write('\n'.join(string_list))


def load_ontology_mapping(trait_mapping_file):
    trait_2_ontology = defaultdict(list)
    target_ontology = 'EFO'
    n_ontology_mappings = 0
    in_header = True

    with open(trait_mapping_file, 'rt') as f:
        for line in f:
            line = line.rstrip()
            if in_header:
                # Extract ontology if present
                m = re.match(r'^#ontology=(.*?)$', line)
                if m and m.group(1):
                    target_ontology = m.group(1).upper()
            if line.startswith('#') or not line:
                continue
            in_header = False
            line_list = line.split('\t')
            assert len(line_list) == 3, f'Incorrect string to ontology mapping format for line {line}'
            clinvar_name, ontology_id, ontology_label = line_list
            trait_2_ontology[clinvar_name.lower()].append((ontology_id, ontology_label))
            n_ontology_mappings += 1
    logger.info('{} ontology mappings loaded for ontology {}'.format(n_ontology_mappings, target_ontology))
    return trait_2_ontology, target_ontology


def get_terms_from_file(terms_file_path):
    if terms_file_path is not None:
        print('Loading list of terms...')
        with open(terms_file_path, 'rt') as terms_file:
            terms_list = [line.rstrip() for line in terms_file]
        print(str(len(terms_file_path)) + ' terms found at ' + terms_file_path)
    else:
        terms_list = []

    return terms_list


def is_structural_variant(measure):
    # Our working definition of "structural variant"
    return not measure.is_repeat_expansion_variant and not measure.has_complete_coordinates


def convert_allele_origins(orig_allele_origins):
    """Splits the original list of allele origins from ClinVar into up to two groups: one for 'somatic' (if present),
    and another one for all other types, which are considered 'germline' (if present). If no allele origins are
    provided, return a single empty group (which will be classified as 'germline')."""
    orig_allele_origins = {item.lower() for item in orig_allele_origins}
    converted_allele_origins = []
    if 'somatic' in orig_allele_origins:
        converted_allele_origins.append(['somatic'])
        orig_allele_origins.remove('somatic')
    if orig_allele_origins:  # Is there something remaining for the second (non-somatic) group?
        converted_allele_origins.append(sorted(orig_allele_origins))
    return converted_allele_origins if converted_allele_origins else [[]]


def group_diseases_by_efo_mapping(clinvar_record_traits, string_to_efo_mappings):
    """Processes and groups diseases from a ClinVar record in two ways. First, diseases mapping to the same EFO term are
    grouped together. Second, if a group of diseases has multiple EFO mappings, they are split into separate groups.
    For each group, the tuple of the following values is returned: (1) the original name of the disease which comes
    first lexicographically; (2) the original MedGen ID of that disease; (3) the mapped EFO term of that disease.
    Diseases without mappings are included, see https://github.com/EBIvariation/eva-opentargets/issues/237.

    For example, for a ClinVar record with the following mappings:
        * Diseases A, B, C -> EFO_1
        * Disease D -> EFO_2 & EFO_3
        * Diseases E, F -> EFO_4 & EFO_5
        * Disease G -> No mapping

    The following tuples will be generated:
        * (A, MedGen_A, EFO_1)
        * (D, MedGen_D, EFO_2)
        * (D, MedGen_D, EFO_3)
        * (E, MedGen_E, EFO_4)
        * (E, MedGen_E, EFO_5)
        * (G, MedGen_G, None)"""

    # Group traits by their EFO mappings and explode multiple mappings.
    efo_to_traits = defaultdict(list)  # Key: EFO ID, value: list of traits mapped to that ID.
    grouped_tuples = []
    for trait in clinvar_record_traits:
        is_unmapped = True
        # Try to match using all trait names.
        for trait_name in trait.all_names:
            for efo_id, efo_label in string_to_efo_mappings.get(trait_name.lower(), []):
                is_unmapped = False
                efo_to_traits[efo_id].append(trait)
        # Unmapped traits are kept but not grouped
        if is_unmapped:
            grouped_tuples.append((trait.preferred_or_other_valid_name, trait.medgen_id, None))

    # Generate tuples by keeping only one disease from each group.
    for efo_id, traits in efo_to_traits.items():
        traits = sorted(traits, key=lambda t: t.preferred_or_other_valid_name)
        selected_trait = traits[0]
        grouped_tuples.append((selected_trait.preferred_or_other_valid_name, selected_trait.medgen_id, efo_id))
    return grouped_tuples


def contains_mapping(grouped_diseases):
    """Checks whether any disease tuple (as described above) contains an EFO mapping."""
    return any(group[-1] for group in grouped_diseases)
