from enum import Enum
from functools import total_ordering
import logging

from cmat.trait_mapping.ontology_mapping import OntologyMapping, MappingProvenance, MappingContext
from cmat.trait_mapping.utils import json_request


ZOOMA_HOST = 'https://www.ebi.ac.uk'
logger = logging.getLogger(__package__)


@total_ordering
class ZoomaConfidence(Enum):
    """Enum to represent the confidence of a mapping in Zooma."""
    LOW = 1
    MEDIUM = 2
    GOOD = 3
    HIGH = 4

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self.value == other.value

    def __hash__(self):
        return hash(self.value)

    def __lt__(self, other):
        return self.value < other.value

    def __str__(self):
        return self.name


class ZoomaMapping(OntologyMapping):
    def __init__(self, mapping_context, uri, confidence, zooma_source):
        super().__init__(mapping_context, uri, MappingProvenance.ZOOMA)
        self.confidence = ZoomaConfidence[confidence.upper()]
        self.zooma_source = zooma_source

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return super().__eq__(other) and self.confidence == other.confidence

    def __hash__(self):
        return hash((super().__hash__, self.confidence, self.zooma_source))

    def __lt__(self, other):
        if isinstance(other, ZoomaMapping):
            # Higher confidence means better mapping
            return super().__lt__(other) and self.confidence > other.confidence
        elif isinstance(other, OntologyMapping):
            return super().__lt__(other)
        return NotImplemented


def get_zooma_results(mapping_context: MappingContext, filters: dict) -> list:
    """
    Given a trait name, Zooma filters in a dict and a hostname to use, query Zooma and return a list
    of Zooma mappings for this trait.

    First get the URI, label from a selected source, confidence and source:
    http://snarf.ebi.ac.uk:8580/spot/zooma/v2/api/services/annotate?propertyValue=intellectual+disability
    Then the ontology label to replace the label from a source:
    https://www.ebi.ac.uk/ols/api/terms?iri=http%3A%2F%2Fwww.ebi.ac.uk%2Fefo%2FEFO_0003847

    :param trait_name: A string containing a trait name from a ClinVar record.
    :param filters: A dictionary containing filters used when querying OxO
    :param target_ontology: ID of target ontology (default EFO)
    :return: List of ZoomaResults
    """
    url = build_zooma_query(mapping_context.trait_name, filters)
    zooma_response_list = json_request(url)

    if zooma_response_list is None:
        return []

    return get_zooma_results_for_trait(mapping_context, zooma_response_list)


def build_zooma_query(trait_name: str, filters: dict) -> str:
    """
    Given a trait name, filters and hostname, create a url with which to query Zooma. Return this
    url.

    :param trait_name: A string containing a trait name from a ClinVar record.
    :param filters: A dictionary containing filters used when querying OxO
    :return: String of a url which can be requested
    """
    url = "{}/spot/zooma/v2/api/services/annotate?propertyValue={}".format(ZOOMA_HOST, trait_name)
    url_filters = [
                    "required:[{}]".format(filters["required"]),
                    "ontologies:[{}]".format(filters["ontologies"]),
                    "preferred:[{}]".format(filters["preferred"])
                  ]
    url += "&filter={}".format(",".join(url_filters))
    return url


def get_zooma_results_for_trait(mapping_context: MappingContext, zooma_response_list: list) -> list:
    """
    Given a response from a Zooma request return ZoomaResults based upon the data in that request.

    :param zooma_response_list: A json (dict) response from a Zooma request.
    :return: List of ZoomaResulst in the Zooma response.
    """
    result_list = []
    for response in zooma_response_list:
        uris = response["semanticTags"]
        confidence = response["confidence"]
        source_name = response["derivedFrom"]["provenance"]["source"]["name"]
        for uri in uris:
            result_list.append(ZoomaMapping(mapping_context, uri, confidence, source_name))
    # Keep only high confidence results
    return [m for m in result_list if m.confidence == ZoomaConfidence.HIGH]
