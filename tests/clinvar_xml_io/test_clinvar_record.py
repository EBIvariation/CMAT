import os

import pytest

from cmat.clinvar_xml_io import ClinVarDataset
from cmat.clinvar_xml_io.clinical_classification import MultipleClinicalClassificationsError

resources_dir = os.path.join(os.path.dirname(__file__), 'resources')


def test_clinvar_record_v1_v2_migration():
    # Same RCV in both versions
    v1_input_file = os.path.join(resources_dir, 'clinvar_dataset_v1.xml.gz')
    v2_input_file = os.path.join(resources_dir, 'clinvar_dataset_v2.xml.gz')
    record_v1 = next(iter(ClinVarDataset(v1_input_file)))
    record_v2 = next(iter(ClinVarDataset(v2_input_file)))
    assert record_v1.xsd_version == 1.6
    assert record_v2.xsd_version == 2.0

    assert record_v1.accession == record_v2.accession
    assert record_v1.score == record_v2.score
    assert set(record_v1.valid_clinical_significances) == set(record_v2.valid_clinical_significances)
    assert set(record_v1.valid_allele_origins) == set(record_v2.valid_allele_origins)


def test_multiple_clinical_classifications_record():
    # input dataset with only one record
    input_file = os.path.join(resources_dir, 'multiple_classifications.xml.gz')
    record = next(iter(ClinVarDataset(input_file)))

    assert len(record.clinical_classifications) == 2
    assert set(cc.type for cc in record.clinical_classifications) == {'germline', 'somatic'}
    with pytest.raises(MultipleClinicalClassificationsError):
        print(record.valid_clinical_significances)


class TestClinvarRecord:
    """Tests base class as well as reference record"""

    @classmethod
    def setup_class(cls):
        input_file = os.path.join(resources_dir, 'clinvar_dataset_v2.xml.gz')
        cls.test_clinvar_record = next(iter(ClinVarDataset(input_file)))

    def test_date(self):
        """Check that the last updated date of the referenceClinVarAssertion is loaded correctly"""
        assert self.test_clinvar_record.last_updated_date == '2024-04-15'

    def test_score(self):
        assert self.test_clinvar_record.score == 2

    def test_review_status(self):
        assert self.test_clinvar_record.review_status == 'criteria provided, multiple submitters, no conflicts'

    def test_acc(self):
        assert self.test_clinvar_record.accession == 'RCV000002127'

    def test_traits(self):
        assert self.test_clinvar_record.traits[0].preferred_name == 'Leber congenital amaurosis 13'
        assert self.test_clinvar_record.traits[0].preferred_or_other_valid_name == 'Leber congenital amaurosis 13'

    def test_trait_pubmed_refs(self):
        assert self.test_clinvar_record.traits[0].pubmed_refs == [20301590, 30285347]

    def test_observed_pubmed_refs(self):
        assert self.test_clinvar_record.evidence_support_pubmed_refs == [15258582, 15322982]

    def test_clinical_significance(self):
        assert self.test_clinvar_record.clinical_significance_list == ['likely pathogenic', 'pathogenic']

    def test_allele_origins(self):
        assert self.test_clinvar_record.allele_origins == {'germline', 'inherited', 'unknown'}

    def test_valid_allele_origins(self):
        assert self.test_clinvar_record.valid_allele_origins == {'germline', 'inherited'}

    def test_trait_efo_ids(self):
        assert self.test_clinvar_record.traits[0].current_efo_aligned_xrefs == [('MONDO', 'MONDO:0012990', 'current')]

    def test_observation_method_types(self):
        assert self.test_clinvar_record.collection_method_types == ['literature only', 'clinical testing', 'clinical testing', 'research']
