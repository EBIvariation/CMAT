import logging

from cmat.clinvar_xml_io.xml_parsing import find_elements, find_optional_unique_element

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ClinVarTrait:
    """Represents a single ClinVar trait (usually a disease), with the corresponding database and Pubmed
    cross-references."""

    # Some trait records in ClinVar contain names which are non-specific and cannot possibly be resolved to any
    # meaningful EFO term.
    NONSPECIFIC_TRAITS = {
        '', 'allhighlypenetrant', 'disease', 'none provided', 'not provided', 'not specified',
        'reclassified - variant of unknown significance', 'see cases', 'variant of unknown significance',
        'reclassified - adra2c polymorphism', 'reclassified - adrb1 polymorphism'
    }

    # These database identifiers are directly importable into EFO
    EFO_ALIGNED_ONTOLOGIES = {'Human Phenotype Ontology', 'EFO', 'Orphanet', 'MONDO'}

    def __init__(self, trait_xml, clinvar_record):
        self.trait_xml = trait_xml
        self.clinvar_record = clinvar_record

    def __str__(self):
        return f'ClinVarTrait object with name {self.preferred_or_other_valid_name} from ClinVar record ' \
               f'{self.clinvar_record.accession}'

    @property
    def identifier(self):
        return self.trait_xml.attrib['ID'].strip()

    @property
    def all_names(self):
        """Returns a lexicographically sorted list of all trait names, including the preferred one (if any)."""
        return sorted(name.text for name in find_elements(self.trait_xml, './Name/ElementValue'))

    @property
    def all_valid_names(self):
        """Returns a lexicographically sorted list of all valid trait names. A valid name is defined as something which
        is not contained in the list of nonspecific traits, which cannot possibly be resolved to a valid EFO mapping."""
        return [name for name in self.all_names if name.lower() not in self.NONSPECIFIC_TRAITS]

    @property
    def preferred_name(self):
        """Returns a single preferred name, as indicated in the ClinVar record."""
        name = find_optional_unique_element(self.trait_xml, './Name/ElementValue[@Type="Preferred"]')
        return None if name is None else name.text

    @property
    def preferred_or_other_valid_name(self):
        """Returns a consistent valid name for a trait, if one is present."""
        if self.preferred_name and self.preferred_name.lower() not in self.NONSPECIFIC_TRAITS:
            return self.preferred_name
        elif self.all_valid_names:
            return self.all_valid_names[0]
        else:
            return None

    @property
    def pubmed_refs(self):
        """Trait-specific PubMed references, contained inside a Trait entity. These are usually reviews or practice
        guidelines related to a disease or a group of diseases."""
        return [int(elem.text) for elem in find_elements(self.trait_xml, './Citation/ID[@Source="PubMed"]')]

    @property
    def xrefs(self):
        return [(elem.attrib['DB'], elem.attrib['ID'].strip(), elem.attrib.get('Status', 'current').lower())
                for elem in find_elements(self.trait_xml, './XRef')]

    @property
    def medgen_id(self):
        """Attempts to resolve a single MedGen ID for a trait. If not present, returns None. If multiple are present,
        returns the first one lexicographically."""
        medgen_ids = []
        for db, id_, status in self.xrefs:
            if db == 'MedGen' and status == 'current':
                medgen_ids.append(id_)
        medgen_ids.sort()
        if len(medgen_ids) == 0:
            logger.warning(f'No MedGen ID for {self}')
        elif len(medgen_ids) == 1:
            return medgen_ids[0]
        else:
            logger.warning(f'Multiple MedGen IDs for {self}: {medgen_ids}')
            return medgen_ids[0]

    @property
    def current_efo_aligned_xrefs(self):
        """Returns current EFO or EFO-aligned ids."""
        return [(db, iden, status) for (db, iden, status) in self.xrefs
                if status == 'current' and db in self.EFO_ALIGNED_ONTOLOGIES]
