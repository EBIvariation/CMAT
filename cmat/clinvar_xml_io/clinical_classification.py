import re

from cmat.clinvar_xml_io.xml_parsing import find_mandatory_unique_element, find_optional_unique_element


class MultipleClinicalClassificationsError(NotImplementedError):
    # Raised when we encounter multiples of clinical classifications or their attributes when not expected.
    # This is new as of ClinVar XSD V2 and will be supported at some point in the future.
    pass


class ClinicalClassification:

    # A score for the review status of the assigned clinical significance ranges from 0 to 4 and corresponds to the
    # number of "gold stars" displayed on ClinVar website. See details here:
    # https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/
    score_map = {
        'no assertion provided': 0,  # v1 only
        'no classification provided': 0,
        'no classification for the single variant': 0,
        'no classification for the individual variant': 0,
        'no assertion criteria provided': 0,
        'no classifications from unflagged records': 0,
        'criteria provided, single submitter': 1,
        'criteria provided, conflicting interpretations': 1,  # v1 only
        'criteria provided, conflicting classifications': 1,
        'criteria provided, multiple submitters': 2,
        'criteria provided, multiple submitters, no conflicts': 2,
        'reviewed by expert panel': 3,
        'practice guideline': 4,
    }
    # Map clinical classification types from XML tags to more readable names
    type_map = {
        'GermlineClassification': 'germline',
        'SomaticClinicalImpact': 'somatic',
        'OncogenicityClassification': 'oncogenicity',
        'NoClassification': 'none'
    }

    # Some records have been flagged by ClinVar and should not be used.
    INVALID_CLINICAL_SIGNIFICANCES = {'no classifications from unflagged records'}

    def __init__(self, class_xml, clinvar_record):
        self.class_xml = class_xml
        self.clinvar_record = clinvar_record
        self.xsd_version = clinvar_record.xsd_version
        self.type = self.type_map.get(class_xml.tag, class_xml.tag)

    @property
    def last_evaluated_date(self):
        """This tracks the latest (re)evaluation date for the clinical interpretation.
        See https://github.com/opentargets/platform/issues/1161#issuecomment-683938510 for details."""
        if self.xsd_version < 2:
            # The DateLastEvaluated attribute is not always present. In this case, this property will be None.
            return self.class_xml.attrib.get('DateLastEvaluated')
        return find_optional_unique_element(self.class_xml, './DateLastEvaluated')

    @property
    def review_status(self):
        """Return a review status text for the assigned clinical significance. See score_map above for the list of
        possible values."""
        review_status = find_mandatory_unique_element(self.class_xml, './ReviewStatus').text
        assert review_status in self.score_map, f'Unknown review status {review_status} in RCV {self.clinvar_record.accession}'
        return review_status

    @property
    def score(self):
        """Return a score (star rating) for the assigned clinical significance. See score_map above."""
        return self.score_map[self.review_status]

    @property
    def clinical_significance_raw(self):
        """The original clinical significance string as stored in ClinVar. Example: 'Benign/Likely benign'."""
        try:
            return find_mandatory_unique_element(self.class_xml, './Description').text
        except AssertionError as e:
            raise MultipleClinicalClassificationsError(f'Found multiple descriptions for one ClinicalClassification in '
                                                       f'{self.clinvar_record.accession}')

    @property
    def clinical_significance_list(self):
        """The normalised deduplicated list of all clinical significance values. The original value is (1) split into
        multiple values by 3 delimiters: ('/', ', ', '; '), (2) converted into lowercase and (3) sorted
        lexicographically. Example: 'Benign/Likely benign, risk_factor' → ['benign', 'likely benign', 'risk factor'].
        See /data-exploration/clinvar-variant-types/README.md for further explanation."""
        return sorted(list(set(re.split('/|, |; ', self.clinical_significance_raw.lower().replace('_', ' ')))))

    @property
    def valid_clinical_significances(self):
        return [cs for cs in self.clinical_significance_list if cs.lower() not in self.INVALID_CLINICAL_SIGNIFICANCES]

    @property
    def somatic_assertion_type(self):
        try:
            return find_mandatory_unique_element(self.class_xml, './Description').attrib.get('ClinicalImpactAssertionType')
        except AssertionError as e:
            raise MultipleClinicalClassificationsError(f'Found multiple descriptions for one ClinicalClassification in '
                                                       f'{self.clinvar_record.accession}')

    @property
    def somatic_clinical_impact(self):
        try:
            return find_mandatory_unique_element(self.class_xml, './Description').attrib.get('ClinicalImpactClinicalSignificance')
        except AssertionError as e:
            raise MultipleClinicalClassificationsError(f'Found multiple descriptions for one ClinicalClassification in '
                                                       f'{self.clinvar_record.accession}')
