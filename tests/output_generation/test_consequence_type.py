from collections import defaultdict

from cmat.output_generation import consequence_type as CT
from cmat.output_generation.consequence_type import get_so_accession_dict

import config


def test_process_gene():
    test_consequence_type_dict = defaultdict(list)
    test_rs_id = "rs121912888"
    test_ensembl_gene_id = "ENSG00000139219"
    test_so_name = "missense_variant"

    test_consequence_type = CT.ConsequenceType(test_ensembl_gene_id, CT.SoTerm(test_so_name))
    CT.process_gene(test_consequence_type_dict, test_rs_id, test_ensembl_gene_id, test_so_name)

    assert test_consequence_type_dict["rs121912888"][0] == test_consequence_type


def test_process_consequence_type_file_tsv():
    test_consequence_type = CT.ConsequenceType("ENSG00000139988", CT.SoTerm("synonymous_variant"))
    consequence_type_dict = CT.process_consequence_type_file(config.snp_2_gene_file)
    assert consequence_type_dict["14:67729241:C:T"][0] == test_consequence_type


def test_ensembl_so_term():
    so_term = CT.SoTerm('stop_gained')
    assert so_term.accession == 'SO_0001587'
    assert so_term.rank == 3


def test_nonexistent_so_term():
    so_term = CT.SoTerm('not_real_term')
    assert so_term.accession is None
    assert so_term.rank == 41


def test_repeat_expansion_so_term():
    so_term = CT.SoTerm('short_tandem_repeat_expansion')
    assert so_term.accession == 'SO_0002162'
    assert so_term.rank == 41


def test_get_so_accession_dict():
    results = get_so_accession_dict(page_size=100)
    assert len(results) == 232
