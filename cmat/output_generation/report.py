import logging
import os
from collections import Counter

import yaml

logger = logging.getLogger(__package__)

# Add representers to enable safe-dump
yaml.SafeDumper.add_representer(Counter,
                                lambda dumper, data: dumper.represent_mapping('tag:yaml.org,2002:map', data.items()))

UNMAPPED_TRAITS_FILE_NAME = 'unmapped_traits.tsv'
COUNTS_FILE_NAME = 'counts.yml'


class Report:
    """Holds counters and other records for a pipeline run."""

    def __init__(self, trait_mappings=None, consequence_mappings=None, nonmatching_mappings=None):
        # The main evidence string counter.
        self.evidence_string_count = 0
        # Complete evidence strings are ones with an EFO mapping.
        self.complete_evidence_string_count = 0

        # ClinVar record counters.
        self.clinvar_total = 0
        self.clinvar_fatal_no_valid_traits = 0
        self.clinvar_fatal_no_clinical_significance = 0
        self.clinvar_fatal_excluded_submission = 0
        self.clinvar_skip_unsupported_variation = 0
        self.clinvar_skip_no_functional_consequences = 0
        self.clinvar_skip_missing_efo_mapping = 0
        self.clinvar_skip_invalid_evidence_string = 0
        self.clinvar_skip_multiple_clinical_classifications = 0
        self.clinvar_done_one_complete_evidence_string = 0
        self.clinvar_done_multiple_complete_evidence_strings = 0
        self.clinvar_fatal = 0
        self.clinvar_skipped = 0
        self.clinvar_done = 0

        # Total number of trait-to-ontology mappings present in the database.
        self.total_trait_mappings = 0
        if trait_mappings:
            self.total_trait_mappings = sum([len(mappings) for mappings in trait_mappings.values()])
        # All distinct (trait name, EFO ID) mappings used in the evidence strings.
        self.used_trait_mappings = set()
        # All unmapped trait names which prevented evidence string generation and their counts.
        self.unmapped_trait_names = Counter()
        # Trait-to-ontology mappings dropped due to not matching the schema regex
        self.nonmatching_trait_mappings = 0
        if nonmatching_mappings:
            self.nonmatching_trait_mappings = len(nonmatching_mappings)

        # Variant-to-consequence mapping counts.
        self.total_consequence_mappings = 0
        if consequence_mappings:
            self.total_consequence_mappings = sum([len(mappings) for mappings in consequence_mappings.values()])
        self.repeat_expansion_variants = 0
        self.structural_variants = 0

    def __eq__(self, other):
        if not isinstance(other, Report):
            return NotImplemented
        return self.__dict__ == other.__dict__

    def __add__(self, other):
        if not isinstance(other, Report):
            return NotImplemented
        result = Report()
        for var_name in vars(self).keys() | vars(other).keys():
            if var_name == 'total_trait_mappings':
                result.total_trait_mappings = max(self.total_trait_mappings, other.total_trait_mappings)
            elif var_name == 'total_consequence_mappings':
                result.total_consequence_mappings = max(self.total_consequence_mappings,
                                                        other.total_consequence_mappings)
            elif var_name == 'used_trait_mappings':
                result.used_trait_mappings = self.used_trait_mappings | other.used_trait_mappings
            else:
                result.__setattr__(var_name, self.__getattribute__(var_name) + other.__getattribute__(var_name))
        return result

    def dump_to_file(self, dir_out, filename=COUNTS_FILE_NAME):
        with open(os.path.join(dir_out, filename), 'w') as f:
            yaml.safe_dump(vars(self), f)

    def load_from_file(self, filename):
        with open(filename, 'r') as f:
            data = yaml.safe_load(f)
            self.__dict__.update(**data)
        # yaml loads a dict, convert to counter
        self.unmapped_trait_names = Counter(self.unmapped_trait_names)

    def compute_record_tallies(self):
        """Compute tallies of records fatal/skipped/done based on the more granular counts."""
        self.clinvar_fatal = (self.clinvar_fatal_no_valid_traits + self.clinvar_fatal_no_clinical_significance +
                              self.clinvar_fatal_excluded_submission)
        self.clinvar_skipped = (self.clinvar_skip_unsupported_variation + self.clinvar_skip_no_functional_consequences +
                                self.clinvar_skip_missing_efo_mapping + self.clinvar_skip_invalid_evidence_string +
                                self.clinvar_skip_multiple_clinical_classifications)
        self.clinvar_done = (self.clinvar_done_one_complete_evidence_string +
                             self.clinvar_done_multiple_complete_evidence_strings)

    def check_counts(self):
        """Return True if counts are consistent, False otherwise."""
        self.compute_record_tallies()
        expected_total = self.clinvar_fatal + self.clinvar_skipped + self.clinvar_done
        if expected_total != self.clinvar_total:
            logger.error(f'ClinVar evidence string tallies do not add up to the total amount: '
                         f'fatal + skipped + done = {expected_total}, total = {self.clinvar_total}')
            return False
        return True

    def print_report(self):
        """Print report of counts."""
        self.compute_record_tallies()
        report = f'''Total number of evidence strings generated\t{self.evidence_string_count}
            Total number of complete evidence strings generated\t{self.complete_evidence_string_count}

            Total number of ClinVar records\t{self.clinvar_total}
                Fatal: Cannot produce evidence\t{self.clinvar_fatal}
                    No traits with valid names\t{self.clinvar_fatal_no_valid_traits}
                    No clinical significance\t{self.clinvar_fatal_no_clinical_significance}
                    Excluded submissions\t{self.clinvar_fatal_excluded_submission}
                Skipped: Can be rescued by future improvements\t{self.clinvar_skipped}
                    Unsupported variation type\t{self.clinvar_skip_unsupported_variation}
                    No functional consequences\t{self.clinvar_skip_no_functional_consequences}
                    Missing EFO mapping\t{self.clinvar_skip_missing_efo_mapping}
                    Invalid evidence string\t{self.clinvar_skip_invalid_evidence_string}
                    Multiple clinical classifications\t{self.clinvar_skip_multiple_clinical_classifications}
                Done: Generated at least one complete evidence string\t{self.clinvar_done}
                    One complete evidence string\t{self.clinvar_done_one_complete_evidence_string}
                    Multiple complete evidence strings\t{self.clinvar_done_multiple_complete_evidence_strings}
            Percentage of all potentially supportable ClinVar records which generated at least one complete evidence string\t{
        self.clinvar_done / (self.clinvar_skipped + self.clinvar_done):.1%}

            Total number of trait-to-ontology mappings in the database\t{self.total_trait_mappings}
                The number of distinct trait-to-ontology mappings dropped due to not matching the schema regex\t{
                self.nonmatching_trait_mappings}
                The number of distinct trait-to-ontology mappings used in the evidence strings\t{
        len(self.used_trait_mappings)}
            The number of distinct unmapped trait names which prevented complete evidence string generation\t{
        len(self.unmapped_trait_names)}

            Total number of variant to consequence mappings\t{self.total_consequence_mappings}
                Number of repeat expansion variants\t{self.repeat_expansion_variants}
                Number of structural variants \t{self.structural_variants}'''.replace('\n' + ' ' * 12, '\n')
        print(report)

    def write_unmapped_terms(self, dir_out):
        with open(os.path.join(dir_out, UNMAPPED_TRAITS_FILE_NAME), 'w') as unmapped_traits_file:
            for trait, number_of_occurrences in sorted(self.unmapped_trait_names.items(), key=lambda x: -x[1]):
                unmapped_traits_file.write(f'{trait}\t{number_of_occurrences}\n')
