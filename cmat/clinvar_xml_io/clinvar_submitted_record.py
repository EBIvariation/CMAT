import logging
from functools import cached_property

from cmat.clinvar_xml_io.clinvar_record import ClinVarRecord
from cmat.clinvar_xml_io.xml_parsing import find_mandatory_unique_element

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ClinVarSubmittedRecord(ClinVarRecord):
    """
    Submitted records (SCVs) are structured similarly to reference records (RCVs) with a few exceptions, though they
    typically have fewer annotations - for example, variant coordinates, HGVS expressions or ontology mappings which are
    added by curators.

    SCVs also contain additional information about the actual submission, which we model in this class.
    """

    def __init__(self, record_xml, xsd_version, reference_record):
        super().__init__(record_xml, xsd_version)
        # Each SCV is associated with a single RCV
        self.reference_record = reference_record

    def __str__(self):
        return f'ClinVarSubmittedRecord object with accession {self.accession}'

    @property
    def submission_date(self):
        """Date of submission or when submission was last revised (for first submission, use created_date)."""
        return find_mandatory_unique_element(self.record_xml, './ClinVarSubmissionID').attrib.get('submitterDate', None)

    @property
    def last_updated_date(self):
        return find_mandatory_unique_element(self.record_xml, './ClinVarAccession').attrib.get('DateUpdated', None)

    @property
    def created_date(self):
        return find_mandatory_unique_element(self.record_xml, './ClinVarAccession').attrib.get('DateCreated', None)

    @property
    def submitter(self):
        """Name of the submitting organization."""
        return find_mandatory_unique_element(self.record_xml, './ClinVarSubmissionID').attrib.get('submitter', None)

    @property
    def submitter_id(self):
        """Numeric identifier associated with the submitting organization."""
        return find_mandatory_unique_element(self.record_xml, './ClinVarAccession').attrib.get('OrgID', None)

    @property
    def submission_name(self):
        """Name or identifier associated with the submission. This is optional."""
        return self.record_xml.attrib.get('SubmissionName', None)

    @cached_property
    def clinical_classifications(self):
        # Submitted record clinical classifications are defined a bit differently than reference records
        raise NotImplementedError('Clinical classification parsing not implemented for SCVs')
