import logging
from itertools import groupby

logger = logging.getLogger(__package__)


class OntologyEntry:
    """
    A representation of an ontology term mapped to using this pipeline. Includes a uri and a label
    which are the two details needed in a finished mapping, in addition to the ClinVar trait name.
    """
    def __init__(self, uri, label):
        self.uri = uri
        self.label = label

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        if self.uri != other.uri or self.label != other.label:
            return False
        return True

    def __hash__(self):
        return hash((self.uri, self.label))


class Trait:
    """
    Object to hold data for one trait name. Including the number of ClinVar record's traits it
    appears in, any Zooma and OxO mappings, and any mappings which are ready to be output.
    """
    def __init__(self, name, identifier, frequency, associated_with_nt_expansion=False):
        self.name = name
        self.identifier = identifier
        self.frequency = frequency
        self.ols_result_list = []
        self.zooma_result_list = []
        self.oxo_result_list = []
        self.finished_mapping_set = set()
        self.associated_with_nt_expansion = associated_with_nt_expansion

    @property
    def is_finished(self):
        """
        Return boolean which confirms whether the trait has finished mappings ready to be output
        """
        return len(self.finished_mapping_set) > 0

    @property
    def is_associated_with_nt_expansion(self):
        """
        Returns a boolean property which indicates whether the trait is associated with a NT expansion (nucleotide
        repeat expansion) variant.
        """
        return self.associated_with_nt_expansion

    def process_ols_results(self):
        """
        Deduplicate OLS mappings and check whether any can be output as a finished ontology mapping.
        Put any finished mappings in finished_mapping_set
        """
        # First deduplicate by IRI, taking the top-ranked results associated with each IRI
        sorted_results = sorted(self.ols_result_list, key=lambda x: x.uri)
        deduplicated_results = []
        for iri, grouped_results in groupby(sorted_results, key=lambda x: x.uri):
            deduplicated_results.append(max(grouped_results))
        self.ols_result_list = deduplicated_results

        for ols_result in self.ols_result_list:
            # Accept current mappings in the target ontology with full exact matches on the label
            if ols_result.in_target_ontology and ols_result.is_current and 'label' in ols_result.full_exact_match:
                ontology_entry = OntologyEntry(ols_result.uri, ols_result.label)
                self.finished_mapping_set.add(ontology_entry)

    def process_zooma_results(self):
        """
        Check whether any Zooma mappings can be output as a finished ontology mapping.
        Put any finished mappings in finished_mapping_set
        """
        for zooma_result in self.zooma_result_list:
            for mapping in zooma_result.mapping_list:
                # Accept current mappings in the target ontology with either high-confidence or exact string matches
                if mapping.in_ontology and mapping.is_current and (zooma_result.confidence.lower() == "high"
                                                                   or zooma_result.zooma_label.lower() == self.name.lower()):
                    ontology_entry = OntologyEntry(mapping.uri, mapping.ontology_label)
                    self.finished_mapping_set.add(ontology_entry)

    def process_oxo_mappings(self):
        """
        Check whether any OxO mappings can be output as a finished ontology mapping.
        Put any finished mappings in finished_mapping_set
        """
        for result in self.oxo_result_list:
            for mapping in result.mapping_list:
                if mapping.in_ontology and mapping.is_current and mapping.distance == 1:
                    uri = str(mapping.uri)
                    ontology_label = mapping.ontology_label
                    ontology_entry = OntologyEntry(uri, ontology_label)
                    logger.debug('Found an OxO finished mapping: {}'.format(uri))
                    self.finished_mapping_set.add(ontology_entry)
