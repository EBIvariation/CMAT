import logging
import re
import xml.etree.ElementTree as ElementTree
from functools import cached_property
from xml.dom import minidom

from cmat.clinvar_xml_io.clinical_classification import MultipleClinicalClassificationsError
from cmat.clinvar_xml_io.clinvar_measure import ClinVarRecordMeasure
from cmat.clinvar_xml_io.clinvar_trait import ClinVarTrait
from cmat.clinvar_xml_io.xml_parsing import find_elements, find_optional_unique_element, \
    find_mandatory_unique_element

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ClinVarRecord:
    """
    Base class for both reference and submitted records in ClinVar. See also:
    /data-exploration/clinvar-variant-types/README.md for the in-depth explanation of ClinVar data model
    """

    # Some allele origin terms in ClinVar are essentially conveying lack of information and are thus not useful.
    NONSPECIFIC_ALLELE_ORIGINS = {'unknown', 'not provided', 'not applicable', 'tested-inconclusive', 'not-reported'}

    def __init__(self, record_xml, xsd_version, trait_class=ClinVarTrait, measure_class=ClinVarRecordMeasure):
        """Initialise a ClinVar record object from an RCV XML record."""
        self.record_xml = record_xml
        self.xsd_version = xsd_version

        # Add a list of traits
        self.trait_set = []
        for trait in find_elements(self.record_xml, './TraitSet/Trait'):
            self.trait_set.append(trait_class(trait, self))

        # We are currently only processing MeasureSets of type Variant which are included directly in the RCV record.
        # Some other options (currently not supported) are:
        # * MeasureSet of types "Haplotype", "Phase unknown", or "Distinct chromosomes"
        # * GenotypeSet, which contains an assertion about a group of variants from different chromosome copies, with
        #   the type of be either a "CompoundHeterozygote" or a "Diplotype"
        variant_measure = find_optional_unique_element(self.record_xml, './MeasureSet[@Type="Variant"]/Measure')
        if not variant_measure:
            self.measure = None
        else:
            self.measure = measure_class(variant_measure, self, self.vcv_id)

    def __str__(self):
        return f'ClinVarRecord object with accession {self.accession}'

    def write(self, output):
        xml_str = minidom.parseString(ElementTree.tostring(self.record_xml)).toprettyxml(indent='  ', encoding='utf-8')
        # version 3.8 adds superfluous root
        if xml_str.startswith(b'<?xml'):
            xml_str = re.sub(b'<\?xml.*?>', b'', xml_str)
        xml_str = b'  '.join([s for s in xml_str.strip().splitlines(True) if s.strip()])
        xml_str += b'\n'
        output.write(xml_str)

    @property
    def accession(self):
        return find_mandatory_unique_element(self.record_xml, './ClinVarAccession').attrib['Acc']

    @property
    def vcv_id(self):
        """ClinVar's accession for a MeasureSet, present only in RCV records."""
        return find_mandatory_unique_element(self.record_xml, './MeasureSet').attrib.get('Acc', None)

    @property
    def last_updated_date(self):
        """This tracks the latest update date, counting even minor technical updates.
        Appears differently in reference and submitted records."""
        raise NotImplementedError

    @property
    def created_date(self):
        """This tracks the date the record was first made public on ClinVar.
        Appears differently in reference and submitted records."""
        raise NotImplementedError

    @property
    def mode_of_inheritance(self):
        """Return a (possibly empty) list of modes of inheritance for a given ClinVar record."""
        return sorted({
            elem.text for elem in find_elements(self.record_xml, './AttributeSet/Attribute[@Type="ModeOfInheritance"]')
        })

    @property
    def trait_set_type(self):
        return find_mandatory_unique_element(self.record_xml, './TraitSet').attrib['Type']

    @property
    def traits(self):
        """Returns a list of traits associated with the ClinVar record, in the form of Trait objects."""
        return self.trait_set

    @property
    def traits_with_valid_names(self):
        """Returns a list of traits which have at least one valid (potentially resolvable) name."""
        return [trait for trait in self.trait_set if trait.preferred_or_other_valid_name]

    @property
    def evidence_support_pubmed_refs(self):
        """The references of this type represent evidence support for this specific variant being observed in this
        specific disease. These are the references displayed on the ClinVar website in the "Assertion and evidence
        details" section at the bottom of the page."""
        return [int(elem.text)
                for elem in find_elements(self.record_xml, './ObservedIn/ObservedData/Citation/ID[@Source="PubMed"]')]

    @property
    def allele_origins(self):
        return {elem.text for elem in find_elements(self.record_xml, './ObservedIn/Sample/Origin')}

    @property
    def valid_allele_origins(self):
        """Returns all valid allele origins, i.e. ones that are not in the list of nonspecific terms."""
        return {origin for origin in self.allele_origins if origin.lower() not in self.NONSPECIFIC_ALLELE_ORIGINS}

    @cached_property
    def clinical_classifications(self):
        """List of clinical classifications (Germline, Somatic, or Oncogenecity)"""
        raise NotImplementedError

    # The following properties are maintained for backwards compatibility, but are only present for a ClinVarRecord
    # if there is exactly one ClinicalClassification for the record.
    # Otherwise these should be taken from the ClinicalClassification objects directly.

    @property
    def last_evaluated_date(self):
        if len(self.clinical_classifications) > 1:
            raise MultipleClinicalClassificationsError(f'Found multiple ClinicalClassifications for {self.accession}')
        return self.clinical_classifications[0].last_evaluated_date

    @property
    def review_status(self):
        if len(self.clinical_classifications) > 1:
            raise MultipleClinicalClassificationsError(f'Found multiple ClinicalClassifications for {self.accession}')
        return self.clinical_classifications[0].review_status

    @property
    def score(self):
        if len(self.clinical_classifications) > 1:
            raise MultipleClinicalClassificationsError(f'Found multiple ClinicalClassifications for {self.accession}')
        return self.clinical_classifications[0].score

    @property
    def clinical_significance_list(self):
        if len(self.clinical_classifications) > 1:
            raise MultipleClinicalClassificationsError(f'Found multiple ClinicalClassifications for {self.accession}')
        return self.clinical_classifications[0].clinical_significance_list

    @property
    def valid_clinical_significances(self):
        if len(self.clinical_classifications) > 1:
            raise MultipleClinicalClassificationsError(f'Found multiple ClinicalClassifications for {self.accession}')
        return self.clinical_classifications[0].valid_clinical_significances

    @property
    def observation_method_types(self):
        return [elem.text for elem in find_elements(self.record_xml, './ObservedIn/Method/MethodType')]
