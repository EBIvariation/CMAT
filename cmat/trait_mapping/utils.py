import logging
import re
from collections import defaultdict

import requests
from requests import HTTPError
from retry import retry

logger = logging.getLogger(__package__)


class ServerError(HTTPError):
    """A server-side error occurred."""


@retry(exceptions=(ConnectionError, requests.RequestException), logger=logger,
       tries=8, delay=2, backoff=1.2, jitter=(1, 3))
def json_request(url: str, payload: dict = None, params: dict = None, method=requests.get) -> dict:
    """Makes a request of a specified type (by default GET) with the specified URL and payload, attempts to parse the
    result as a JSON string and return it as a dictionary, on failure raises an exception."""
    result = method(url, data=payload, params=params)
    result.raise_for_status()
    return result.json()


def string_to_preferred_ontologies(ontology_string, target_ontology):
    """
    Takes a comma-separated string listing ontology IDs and returns a list of ontology IDs in a consistent order
    with the target ontology removed.
    E.g. 'efo,hp,mondo' with target='efo' => ['mondo', 'hp']
    """
    preferred_ontologies = sorted([ontology.lower().strip() for ontology in ontology_string.split(",")], reverse=True)
    if target_ontology.lower() in preferred_ontologies:
        preferred_ontologies.remove(target_ontology.lower())
    return preferred_ontologies


def load_ontology_mapping(trait_mapping_file, schema=None):
    """
    Load ontology mappings from a TSV file.

    :param trait_mapping_file: Path to TSV file containing ontology mappings
    :param schema: Optional OT JSON schema object, if present will filter out non-matching ontology IDs
    :return: Tuple containing:
        - dict from trait name to ontology mappings
        - str for target ontology according to optional mappings header (default EFO)
        - list of nonmatching mappings (empty if no schema)
    """
    trait_2_ontology = defaultdict(list)
    target_ontology = 'EFO'
    n_ontology_mappings = 0
    in_header = True
    ontology_id_regex = '.*'
    if schema:
        ontology_id_regex = schema['definitions']['diseaseFromSourceMappedId']['pattern']
    nonmatching_mappings = []

    with open(trait_mapping_file, 'rt') as f:
        for line in f:
            line = line.rstrip()
            if in_header:
                # Extract ontology if present
                m = re.match(r'^#ontology=(.*?)$', line)
                if m and m.group(1):
                    target_ontology = m.group(1).upper()
            if line.startswith('#') or not line:
                continue
            in_header = False
            line_list = line.split('\t')
            assert len(line_list) == 3, f'Incorrect string to ontology mapping format for line {line}'
            clinvar_name, ontology_id, ontology_label = line_list

            # Only include the mapping if it matches the schema's regex
            if re.match(ontology_id_regex, ontology_id.split('/')[-1]):
                trait_2_ontology[clinvar_name.lower()].append((ontology_id, ontology_label))
                n_ontology_mappings += 1
            else:
                nonmatching_mappings.append((clinvar_name, ontology_id, ontology_label))

    logger.info('{} ontology mappings loaded for ontology {}'.format(n_ontology_mappings, target_ontology))
    return trait_2_ontology, target_ontology, nonmatching_mappings
