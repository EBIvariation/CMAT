import os

import pytest

from cmat.clinvar_xml_io.clinvar_set import ClinVarSet
from cmat.clinvar_xml_io.xml_parsing import iterate_cvs_from_xml


@pytest.fixture
def clinvar_set():
    resources_dir = os.path.join(os.path.dirname(__file__), 'resources')
    input_file = os.path.join(resources_dir, 'clinvar_dataset_v2.xml.gz')
    return ClinVarSet(next(iterate_cvs_from_xml(input_file)), 2.0)


@pytest.fixture
def submitted_record(clinvar_set):
    return clinvar_set.scvs[0]


def test_clinvar_set(clinvar_set):
    assert clinvar_set.rcv.accession == 'RCV000002127'
    assert len(clinvar_set.scvs) == 5
    assert clinvar_set.id == '188870850'
    assert clinvar_set.title == 'NM_152443.3(RDH12):c.677A>G (p.Tyr226Cys) AND Leber congenital amaurosis 13'
    assert clinvar_set.status == 'current'


def test_clinvar_submitted_record(submitted_record):
    assert submitted_record.submitter == 'OMIM'
    assert submitted_record.submitter_id == '3'
    assert submitted_record.submission_name is None
    assert submitted_record.accession == 'SCV000022285'
    assert submitted_record.valid_allele_origins == {'germline'}
    assert submitted_record.evidence_support_pubmed_refs == [15258582, 15322982]
    assert submitted_record.collection_method_types == ['literature only']

    assert submitted_record.created_date == '2013-04-04'  # submission first publicly available
    assert submitted_record.submission_date == '2015-07-02'  # submission last revised
    assert submitted_record.last_updated_date == '2015-07-05'  # submission last revision publicly available

    with pytest.raises(NotImplementedError):
        assert submitted_record.valid_clinical_significances


def test_clinvar_submitted_record_trait(submitted_record):
    assert len(submitted_record.traits_with_valid_names) == 1
    scv_trait = submitted_record.traits_with_valid_names[0]

    assert scv_trait.preferred_or_other_valid_name == 'LEBER CONGENITAL AMAUROSIS 13'
    assert scv_trait.current_efo_aligned_xrefs == []


def test_clinvar_submitted_record_measure(submitted_record):
    assert submitted_record.measure is not None
    scv_measure = submitted_record.measure

    assert scv_measure.preferred_or_other_name == 'RDH12, TYR226CYS'
    assert scv_measure.preferred_current_hgvs is None
    assert not scv_measure.has_complete_coordinates
    assert scv_measure.variant_type == 'Variation'
