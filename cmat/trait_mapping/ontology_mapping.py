import logging
from enum import Enum
from functools import total_ordering

from cmat.trait_mapping.ols import get_label_and_synonyms_from_ols, get_is_in_ontologies, is_current_and_in_ontology, \
    get_fields_with_match, EXACT_SYNONYM_KEY

logger = logging.getLogger(__package__)


class MappingProvenance(Enum):
    PREVIOUS = 0
    OLS = 1
    CLINVAR_XREF = 2
    ZOOMA = 3
    OXO = 4

    def __str__(self):
        return self.name


class MatchType(Enum):
    EXACT_MATCH_LABEL = 0
    EXACT_MATCH_SYNONYM = 1
    CONTAINED_MATCH_LABEL = 2
    CONTAINED_MATCH_SYNONYM = 3
    TOKEN_MATCH_LABEL = 4
    TOKEN_MATCH_SYNONYM = 5
    NO_MATCH = 6

    def __str__(self):
        return self.name


class MappingSource(Enum):
    TARGET_CURRENT = 0
    TARGET_OBSOLETE = 1
    PREFERRED_NOT_TARGET = 2
    NOT_PREFERRED_TARGET = 3

    def to_string(self, target_ontology, preferred_ontologies):
        # Workaround to make more curation-friendly output strings while staying ontology-agnostic
        target_string = target_ontology.upper()
        preferred_string = '_'.join(p.upper() for p in preferred_ontologies)
        return self.name.replace('TARGET', target_string).replace('PREFERRED', preferred_string)


class MappingContext:
    """
    MappingContext provides the context in which a mapping is proposed. It includes the search term (trait name),
    the target ontology and any preferred ontologies.
    """
    def __init__(self, trait_name, target_ontology, preferred_ontologies):
        self.trait_name = trait_name
        self.target_ontology = target_ontology
        self.preferred_ontologies = preferred_ontologies


@total_ordering
class OntologyMapping:
    """
    An OntologyMapping represents a possible mapping between a string (trait name) and an ontology term (URI).
    It utilises (cached) OLS queries in order to gather relevant information for determining the quality of the mapping.
    """
    def __init__(self, mapping_context, uri, provenance,
                 label=None, in_target_ontology=None, in_preferred_ontology=None, is_current=None,
                 exact_match=None, contained_match=None, token_match=None):
        self.mapping_context = mapping_context
        self.uri = uri
        self.provenance = provenance
        self.label = label
        self.in_target_ontology = in_target_ontology
        self.in_preferred_ontology = in_preferred_ontology
        self.is_current = is_current
        self.exact_match = exact_match
        self.contained_match = contained_match
        self.token_match = token_match

    def __str__(self):
        mapping_source_str = self.get_mapping_source().to_string(self.mapping_context.target_ontology, self.mapping_context.preferred_ontologies)
        return f'{self.uri}|{self.label}|{self.provenance}|{self.get_match_type()}|{mapping_source_str}'

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.mapping_context == other.mapping_context and self.uri == other.uri

    def __hash__(self):
        return hash((self.mapping_context, self.uri))

    def __gt__(self, other):
        # TODO add provenance to this
        # Larger means better mapping
        # In general, full exact matches > contained matches > token matches,
        # and target ontology > preferred ontologies > neither
        if self.exact_match:
            if other.exact_match:
                return self.ontology_rank() > other.ontology_rank()
            else:
                return True
        if self.contained_match:
            if other.exact_match:
                return False
            if other.contained_match:
                return self.ontology_rank() > other.ontology_rank()
            else:
                return True
        if self.token_match:
            if other.exact_match:
                return False
            if other.contained_match:
                return False
            if other.token_match:
                return self.ontology_rank() > other.ontology_rank()
            else:
                return True

    def ontology_rank(self):
        if self.in_target_ontology:
            return 2
        if self.in_preferred_ontology:
            return 1
        return 0

    # TODO ensure these are robust to non-ontologies (e.g. medgen)

    def get_label(self):
        if self.label is not None:
            return self.label
        return get_label_and_synonyms_from_ols(self.uri)[0]

    def get_match_type(self):
        if any(x is None for x in [self.exact_match, self.contained_match, self.token_match]):
            label, synonyms = get_label_and_synonyms_from_ols(self.uri)
            self.exact_match, self.contained_match, self.token_match = get_fields_with_match(
                self.mapping_context.trait_name, ['label', EXACT_SYNONYM_KEY],
                {'label': label, EXACT_SYNONYM_KEY: list(synonyms)})

        if self.exact_match:
            if 'label' in self.exact_match:
                return MatchType.EXACT_MATCH_LABEL
            if EXACT_SYNONYM_KEY in self.exact_match:
                return MatchType.EXACT_MATCH_SYNONYM
        if self.contained_match:
            if 'label' in self.contained_match:
                return MatchType.CONTAINED_MATCH_LABEL
            if EXACT_SYNONYM_KEY in self.contained_match:
                return MatchType.CONTAINED_MATCH_SYNONYM
        if self.token_match:
            if 'label' in self.token_match:
                return MatchType.TOKEN_MATCH_LABEL
            if EXACT_SYNONYM_KEY in self.token_match:
                return MatchType.TOKEN_MATCH_SYNONYM
        return MatchType.NO_MATCH

    def get_mapping_source(self):
        if any(x is None for x in [self.in_target_ontology, self.in_preferred_ontology, self.is_current]):
            self.in_target_ontology, self.in_preferred_ontology = get_is_in_ontologies(self.uri, self.mapping_context.target_ontology,
                                                                                       self.mapping_context.preferred_ontologies)
            self.is_current = is_current_and_in_ontology(self.uri, self.mapping_context.target_ontology) if self.in_target_ontology else False

        if self.in_target_ontology:
            return MappingSource.TARGET_CURRENT if self.is_current else MappingSource.TARGET_OBSOLETE
        if self.in_preferred_ontology:
            return MappingSource.PREFERRED_NOT_TARGET
        return MappingSource.NOT_PREFERRED_TARGET


class PreviousMapping(OntologyMapping):
    def __init__(self, mapping_context, uri, label):
        super().__init__(mapping_context, uri, MappingProvenance.PREVIOUS, label)


class ClinVarXrefMapping(OntologyMapping):
    def __init__(self, mapping_context, uri):
        super().__init__(mapping_context, uri, MappingProvenance.CLINVAR_XREF)
