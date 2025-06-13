from collections import defaultdict
import logging

import requests
from retry import retry

from cmat.consequence_prediction.common.vep import get_severity_ranking
from cmat.trait_mapping.ols import OLS_BASE_URL

logger = logging.getLogger(__package__)


def process_gene(consequence_type_dict, variant_id, ensembl_gene_id, so_term, ensembl_transcript_id=None):
    consequence_type_dict[variant_id].append(ConsequenceType(ensembl_gene_id, SoTerm(so_term), ensembl_transcript_id))


def process_consequence_type_file(snp_2_gene_file, consequence_type_dict=None):
    """
    Return a dictionary of consequence information extracted from the given file.
    If consequence_type_dict is provided then the information will be merged into this dictionary.
    """
    logger.info('Loading mapping rs -> ENSG/SOterms')
    if consequence_type_dict is None:
        consequence_type_dict = defaultdict(list)

    with open(snp_2_gene_file, "rt") as snp_2_gene_file:
        for line in snp_2_gene_file:
            line = line.rstrip()
            line_list = line.split("\t")

            if len(line_list) < 4:
                logger.warning('Skip invalid line in snp_2_gene file: {}'.format(line))
                continue

            variant_id = line_list[0]
            ensembl_gene_id = line_list[1]
            so_term = line_list[3]

            if ensembl_gene_id == 'NA':
                logger.warning('Skip line with missing gene ID: {}'.format(line))
                continue

            # Include transcript if present
            if len(line_list) >= 5:
                ensembl_transcript_id = line_list[4]
                process_gene(consequence_type_dict, variant_id, ensembl_gene_id, so_term, ensembl_transcript_id)
            else:
                process_gene(consequence_type_dict, variant_id, ensembl_gene_id, so_term)

    logger.info('{} rs->ENSG/SOterms mappings loaded'.format(len(consequence_type_dict)))
    return consequence_type_dict


@retry(tries=10, delay=5, backoff=1.2, jitter=(1, 3), logger=logger)
def get_so_accession_dict(page_size=500):
    """Get name and accession of all hierarchical descendents of sequence_variant in the Sequence Ontology."""
    sequence_variant_id = 'SO:0001060'
    url = f'{OLS_BASE_URL}/api/ontologies/so/hierarchicalDescendants?id={sequence_variant_id}&size={page_size}'
    has_next = True
    results = []
    while has_next:
        response = requests.get(url)
        response.raise_for_status()
        response_json = response.json()
        results += response_json['_embedded']['terms']
        has_next = 'next' in response_json['_links']
        if has_next:
            url = response_json['_links']['next']['href']
    return {
        r['label']: r['short_form']
        for r in results
    }


class SoTerm(object):
    """
    Represents a sequence ontology term belonging to a consequence type object.
    Holds information on accession and rank.
    """
    so_accession_name_dict = get_so_accession_dict()

    ranked_so_names_list = get_severity_ranking()

    def __init__(self, so_name):
        self.so_name = so_name
        if so_name in SoTerm.so_accession_name_dict:
            self._so_accession = SoTerm.so_accession_name_dict[so_name]
        else:
            self._so_accession = None

    @property
    def accession(self):
        if self._so_accession is not None:
            return self._so_accession
        else:
            return None

    @property
    def rank(self):
        # If So name not in Ensembl's ranked list, return the least severe rank
        if self.so_name not in SoTerm.ranked_so_names_list:
            return len(SoTerm.ranked_so_names_list)
        else:
            return SoTerm.ranked_so_names_list.index(self.so_name)

    def __eq__(self, other):
        return self.accession == other.accession

    def __hash__(self):
        return hash(self._so_accession)


class ConsequenceType:
    """
    Holds information on the type of consequence related to a variation
    with relationship to ensembl gene IDs and SO terms
    """

    def __init__(self, ensembl_gene_id, so_term, ensembl_transcript_id=None):
        self.ensembl_gene_id = ensembl_gene_id
        self.so_term = so_term
        self.ensembl_transcript_id = ensembl_transcript_id

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)
