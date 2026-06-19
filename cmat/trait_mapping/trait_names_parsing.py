from collections import Counter, defaultdict

from cmat.clinvar_xml_io import ClinVarDataset
from cmat.clinvar_xml_io.filtering import filter_by_submission
from cmat.clinvar_xml_io.ontology_uri import OntologyUri
from cmat.trait_mapping.trait import Trait


def parse_trait_names(filepath: str) -> list:
    """For a file containing ClinVar records in the XML format, return a list of Traits for the records in the file.
    Each Trait object contains trait name, how many times it occurs in the input file, a list of URLs appearing as
    ClinVar cross-references, and whether it is linked to an NT expansion variant.

    Trait occurrence count is calculated based on all unique (RCV, trait name) tuples in the input file. This is because
    each such tuple will, generally speaking, correspond to one output evidence string. So if we want to gauge which
    trait names are more important to curate, we need to consider how many such tuples it appears in.

    Traits which are implicated in "Microsatellite" variants are marked using a special field, because a subset of
    microsatellites are NT expansion variants, and their curation is of highest importance even if the number of records
    which they are linked to is low.

    :param filepath: Path to a gzipped file containing ClinVar XML dump.
    :return: A list of Trait objects."""

    # Tracks how many times a trait name occurs in ClinVar
    trait_name_counter = Counter()

    # Track cross-references associated with each trait name.
    # Do this separately from trait name/ID, just in case ClinVar has different sets of xrefs associated with the same
    # trait across different RCVs.
    trait_xrefs = defaultdict(list)

    # Tracks all traits which are at least once implicated in "NT expansion", or nucleotide repeat expansion, variants.
    # Their curation is of highest importance regardless of how many records they are actually associated with.
    nt_expansion_traits = set()

    dataset = ClinVarDataset(filepath)
    for clinvar_set in dataset.iter_cvs():
        if not filter_by_submission(clinvar_set):
            continue
        clinvar_record = clinvar_set.rcv
        trait_names_and_ids = set()
        for trait in clinvar_record.traits_with_valid_names:
            trait_tuple = (trait.preferred_or_other_valid_name.lower(), trait.identifier)
            trait_names_and_ids.add(trait_tuple)

            # Add xrefs from this trait
            xrefs = []
            for (db, id_, status) in trait.xrefs:
                if status.lower() == 'current' and db.lower() in OntologyUri.db_to_uri_conversion:
                    xrefs.append(OntologyUri(id_, db).uri)

            trait_xrefs[trait_tuple].extend(xrefs)
            trait_name_counter[trait_tuple] += 1
        if clinvar_record.measure and clinvar_record.measure.is_repeat_expansion_variant:
            nt_expansion_traits |= trait_names_and_ids

    # Count trait occurrences
    traits = []
    for trait_tuple, trait_frequency in trait_name_counter.items():
        if trait_tuple[0] == '-':
            print('Skipped {} missing trait names'.format(trait_frequency))
            continue
        associated_with_nt_expansion = trait_tuple in nt_expansion_traits
        traits.append(Trait(name=trait_tuple[0], identifier=trait_tuple[1], frequency=trait_frequency,
                            xrefs=trait_xrefs.get(trait_tuple, []),
                            associated_with_nt_expansion=associated_with_nt_expansion))

    return traits
