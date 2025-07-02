import logging
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
