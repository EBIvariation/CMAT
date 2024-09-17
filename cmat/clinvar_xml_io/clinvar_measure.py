import logging
from functools import cached_property

from cmat.clinvar_xml_io.hgvs_variant import HgvsVariant
from cmat.clinvar_xml_io.xml_parsing import find_elements, find_optional_unique_element

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ClinVarRecordMeasure:
    """This class represents individual ClinVar record "measures". Measures are essentially isolated variants, which can
    be combined into either MeasureSets (include one or more Measures) or GenotypeSets. For a detailed description of
    ClinVar data model, see data-exploration/clinvar-variant-types/."""

    # For ClinVar Microsatellite events with complete coordinates, require the event to be at least this number of bases
    # long in order for it to be considered a repeat expansion event. Smaller events will be processed as regular
    # insertions. The current value was chosen as a reasonable threshold to separate thousands of very small insertions
    # which are technically microsatellite expansion events but are not long enough to be considered clinically
    # significant repeat expansion variants.
    REPEAT_EXPANSION_THRESHOLD = 12

    # Microsatellite variant types.
    MS_DELETION = 'deletion'
    MS_SHORT_EXPANSION = 'short_expansion'
    MS_REPEAT_EXPANSION = 'repeat_expansion'
    MS_NO_COMPLETE_COORDS = 'no_complete_coords'

    def __init__(self, measure_xml, clinvar_record, vcv_id):
        self.measure_xml = measure_xml
        self.clinvar_record = clinvar_record
        self.vcv_id = vcv_id

    @property
    def all_names(self):
        """Returns a lexicographically sorted list of all measure names, including the preferred one (if any)."""
        return sorted(name.text for name in find_elements(self.measure_xml, './Name/ElementValue'))

    @property
    def preferred_name(self):
        """Returns a single preferred measure name, as indicated in the ClinVar record."""
        name = find_optional_unique_element(self.measure_xml, './Name/ElementValue[@Type="Preferred"]')
        return None if name is None else name.text

    @property
    def preferred_or_other_name(self):
        """Returns a consistent name for a measure, if one is present."""
        if self.preferred_name:
            return self.preferred_name
        elif self.all_names:
            return self.all_names[0]
        else:
            return None

    @property
    def preferred_gene_symbols(self):
        return [elem.text for elem in find_elements(
            self.measure_xml, './MeasureRelationship/Symbol/ElementValue[@Type="Preferred"]')]

    @property
    def hgnc_ids(self):
        return [elem.attrib['ID'] for elem in find_elements(self.measure_xml, './MeasureRelationship/XRef[@DB="HGNC"]')]

    @property
    def rs_id(self):
        """Returns dbSNP rsID found for the record measure."""
        rs_ids = ['rs' + elem.attrib['ID'] for elem in find_elements(self.measure_xml, './XRef[@DB="dbSNP"]')]
        if len(rs_ids) == 0:
            return None
        elif len(rs_ids) == 1:
            return rs_ids[0]
        else:
            logger.warning(f'Found multiple RS IDs for {self.clinvar_record}, this is not yet supported')
            return None

    @property
    def nsv_id(self):
        nsv_ids = [elem.attrib['ID']
                   for elem in find_elements(self.measure_xml, './XRef[@DB="dbVar"]')
                   if elem.attrib['ID'].startswith('nsv')]
        if len(nsv_ids) == 0:
            return None
        elif len(nsv_ids) == 1:
            return nsv_ids[0]
        else:
            logger.warning(f'Found multiple NSV IDs for {self.clinvar_record}, this is not yet supported')
            return None

    @property
    def existing_so_terms(self):
        all_so_terms = set()
        for attr_elem in find_elements(self.measure_xml, './AttributeSet'):
            if ('providedBy' not in attr_elem.attrib
                    and find_elements(attr_elem, './Attribute[@Type="MolecularConsequence"]')):
                for so_elem in find_elements(attr_elem, './XRef[@DB="Sequence Ontology"]'):
                    all_so_terms.add(so_elem.attrib['ID'])
        return all_so_terms

    @cached_property
    def _hgvs_to_types(self):
        """
        Returns a dict of HgvsVariant to type attributes from the XML, for all HGVS identifiers in the measure.
        For example, if there's an element
            <Attribute Type="HGVS, genomic, RefSeqGene">NG_008029.2:g.9185del</Attribute>
        we will include
            'NG_008029.2:g.9185del': ['hgvs', 'genomic', 'refseqgene']
        in the returned dict.
        """
        return {
            HgvsVariant(elem.text): {t.lower().strip() for t in elem.attrib['Type'].split(',')}
            for elem in find_elements(self.measure_xml, './AttributeSet/Attribute')
            if elem.attrib['Type'].startswith('HGVS') and elem.text is not None
        }

    @cached_property
    def all_hgvs(self):
        return [hgvs for hgvs in self._hgvs_to_types]

    @cached_property
    def current_hgvs(self):
        return {hgvs for hgvs, types in self._hgvs_to_types.items() if 'previous' not in types}

    @cached_property
    def genomic_hgvs(self):
        return {hgvs for hgvs, types in self._hgvs_to_types.items() if 'genomic' in types}

    @cached_property
    def toplevel_refseq_hgvs(self):
        for hgvs, types in self._hgvs_to_types.items():
            if types == {'hgvs', 'genomic', 'top level'}:
                return hgvs
        return None

    @cached_property
    def preferred_current_hgvs(self):
        """
        Returns a consistent current HGVS identifier for a measure, if one is present.
        Currently the order of preferences is as follows:
        - top level RefSeq HGVS
        - lexicographically first genomic HGVS
        - lexicographically first other HGVS
        """
        if self.toplevel_refseq_hgvs:
            return self.toplevel_refseq_hgvs
        elif self.current_hgvs:
            current_genomic = sorted(self.current_hgvs & self.genomic_hgvs)
            if current_genomic:
                for hgvs in current_genomic:
                    if hgvs.reference_sequence == self.sequence_location_helper('Accession'):
                        return hgvs
                return current_genomic[0]
            return sorted(self.current_hgvs)[0]
        return None

    @property
    def variant_type(self):
        return self.measure_xml.attrib['Type']

    @property
    def explicit_insertion_length(self):
        if self.vcf_alt and self.vcf_ref:
            return len(self.vcf_alt) - len(self.vcf_ref)
        return None

    @property
    def microsatellite_category(self):
        if self.variant_type == 'Microsatellite':
            if self.has_complete_coordinates:
                if self.explicit_insertion_length < 0:
                    return self.MS_DELETION
                elif self.explicit_insertion_length < self.REPEAT_EXPANSION_THRESHOLD:
                    return self.MS_SHORT_EXPANSION
                else:
                    return self.MS_REPEAT_EXPANSION
            else:
                return self.MS_NO_COMPLETE_COORDS
        else:
            return None

    @property
    def is_repeat_expansion_variant(self):
        return self.microsatellite_category in (self.MS_REPEAT_EXPANSION, self.MS_NO_COMPLETE_COORDS)

    @property
    def pubmed_refs(self):
        """Variant-specific PubMed references, contained inside a Measure entity. These are usually large reviews which
        focus on genetics of specific types of variants or genomic regions."""
        return [int(elem.text) for elem in find_elements(self.measure_xml, './Citation/ID[@Source="PubMed"]')]

    @property
    def chr(self):
        return self.sequence_location_helper('Chr')

    @property
    def vcf_pos(self):
        return self.sequence_location_helper('positionVCF')

    @property
    def vcf_ref(self):
        return self.sequence_location_helper('referenceAlleleVCF')

    @property
    def vcf_alt(self):
        return self.sequence_location_helper('alternateAlleleVCF')

    @property
    def has_complete_coordinates(self):
        return bool(self.chr and self.vcf_pos and self.vcf_ref and self.vcf_alt)

    @property
    def vcf_full_coords(self):
        """Returns complete variant coordinates in CHROM_POS_REF_ALT format, if present, otherwise None."""
        if self.has_complete_coordinates:
            return '_'.join([self.chr, self.vcf_pos, self.vcf_ref, self.vcf_alt])

    def sequence_location_helper(self, attr):
        if self.variant_type == 'Translocation':
            # TODO: Translocations have multiple locations and are not supported.
            # TODO: https://github.com/EBIvariation/eva-opentargets/issues/171
            return None
        sequence_locations = find_elements(self.measure_xml, './SequenceLocation[@Assembly="GRCh38"]')
        if len(sequence_locations) != 1:
            # TODO: Support variants with multiple locations (for example, chrX/chrY).
            # TODO: https://github.com/EBIvariation/eva-opentargets/issues/172
            return None
        return sequence_locations[0].attrib.get(attr)

    def get_variant_name_or_hgvs(self):
        if self.preferred_or_other_name:
            return self.preferred_or_other_name
        if self.toplevel_refseq_hgvs:
            return self.toplevel_refseq_hgvs.text
        return None
