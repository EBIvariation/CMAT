import re
import xml.etree.ElementTree as ET
from collections import defaultdict

from cmat.clinvar_xml_io.ontology_uri import OntologyUri

from cmat.clinvar_xml_io import ClinVarTrait, ClinVarRecordMeasure, ClinVarDataset, ClinVarRecord
from cmat.clinvar_xml_io.xml_parsing import iterate_rcv_from_xml
from cmat.output_generation.clinvar_to_evidence_strings import get_consequence_types
from cmat.output_generation import consequence_type as CT
from cmat.output_generation.evaluation.set_metrics import SetComparisonMetrics
from cmat.trait_mapping.utils import load_ontology_mapping

PROCESSOR = 'CMAT'


class AnnotatingClinVarDataset(ClinVarDataset):
    """This class provides the ability to parse ClinVar records (RCVs) and annotate them with ontology mappings and
    consequence mappings on the fly."""

    def __init__(self, clinvar_xml, string_to_ontology_mappings, variant_to_gene_mappings, target_ontology,
                 eval_gene_mappings=None, eval_xref_mappings=None, eval_latest_mappings=None):
        super().__init__(clinvar_xml)
        self.header_attr['ProcessedBy'] = PROCESSOR
        self.string_to_ontology_mappings = string_to_ontology_mappings
        self.variant_to_gene_mappings = variant_to_gene_mappings
        self.target_ontology = target_ontology

        self.eval_gene_mappings = eval_gene_mappings
        self.eval_xref_mappings = eval_xref_mappings
        self.eval_latest_mappings = eval_latest_mappings
        self.do_eval = (self.eval_gene_mappings and self.eval_xref_mappings and self.eval_latest_mappings)
        self.overall_counts = {}
        self.obsolete_counts = {}
        self.gene_metrics = None
        self.conseq_metrics = None
        # Gene and consequence metrics, split by variant category
        self.simple_variant_metrics = None
        self.repeat_variant_metrics = None
        self.complex_variant_metrics = None

        self.trait_metrics = None
        self.mismatches_file = None

    def __iter__(self):
        # Initialise counts
        self.overall_counts = {
            'total': 0,
            'has_supported_measure': 0,
            'has_supported_trait': 0,
            'both_measure_and_trait': 0
        }
        self.obsolete_counts = {
            'cv_total': 0,    # total EFO xrefs used by ClinVar
            'cmat_total': 0,  # total EFO mappings used by CMAT
            'cv_obsolete': 0,
            'cmat_obsolete': 0
        }
        self.gene_metrics = SetComparisonMetrics()
        self.conseq_metrics = SetComparisonMetrics()
        # First counter is genes, second is consequences
        self.simple_variant_metrics = (SetComparisonMetrics(), SetComparisonMetrics())
        self.repeat_variant_metrics = (SetComparisonMetrics(), SetComparisonMetrics())
        self.complex_variant_metrics = (SetComparisonMetrics(), SetComparisonMetrics())

        self.trait_metrics = SetComparisonMetrics()
        if self.do_eval:
            self.mismatches_file = open('mismatches.tsv', 'w+')
            self.mismatches_file.write('RCV\tCV\tCMAT\n')

        for rcv in iterate_rcv_from_xml(self.clinvar_xml):
            record = AnnotatedClinVarRecord(rcv, self.xsd_version)
            self.annotate(record)
            yield record

        # Finalise counts - computes averages, etc.
        self.gene_metrics.finalise()
        self.conseq_metrics.finalise()
        self.trait_metrics.finalise()
        for metrics in self.simple_variant_metrics + self.repeat_variant_metrics + self.complex_variant_metrics:
            metrics.finalise()
        if self.do_eval:
            self.mismatches_file.close()

    def annotate(self, record):
        self.overall_counts['total'] += 1
        # Functional consequences for measure
        if record.measure:
            self.overall_counts['has_supported_measure'] += 1
            self.annotate_and_count_measure(record)
        # EFO terms for traits
        if record.traits_with_valid_names:
            self.overall_counts['has_supported_trait'] += 1
            self.annotate_and_count_traits(record)
        if record.measure and record.traits_with_valid_names:
            self.overall_counts['both_measure_and_trait'] += 1

    def annotate_and_count_measure(self, record):
        consequence_types, variant_category = get_consequence_types(record.measure, self.variant_to_gene_mappings)
        record.measure.add_ensembl_annotations(consequence_types)

        annotated_genes = {ct.ensembl_gene_id for ct in consequence_types if ct.ensembl_gene_id}
        annotated_conseqs = {EnsemblAnnotatedClinVarMeasure.format_so_term(ct.so_term)
                             for ct in consequence_types if ct.so_term}

        if self.eval_gene_mappings:
            existing_ensembl_ids = self.eval_gene_mappings.get(record.accession, [])
            self.gene_metrics.count_and_score(cv_set=existing_ensembl_ids, cmat_set=annotated_genes)
            self.conseq_metrics.count_and_score(cv_set=record.measure.existing_so_terms, cmat_set=annotated_conseqs)
            if variant_category == 'SIMPLE':
                self.simple_variant_metrics[0].count_and_score(cv_set=existing_ensembl_ids, cmat_set=annotated_genes)
                self.simple_variant_metrics[1].count_and_score(cv_set=record.measure.existing_so_terms,
                                                               cmat_set=annotated_conseqs)
            elif variant_category == 'REPEAT':
                self.repeat_variant_metrics[0].count_and_score(cv_set=existing_ensembl_ids, cmat_set=annotated_genes)
                self.repeat_variant_metrics[1].count_and_score(cv_set=record.measure.existing_so_terms,
                                                               cmat_set=annotated_conseqs)
            elif variant_category == 'COMPLEX':
                self.complex_variant_metrics[0].count_and_score(cv_set=existing_ensembl_ids, cmat_set=annotated_genes)
                self.complex_variant_metrics[1].count_and_score(cv_set=record.measure.existing_so_terms,
                                                               cmat_set=annotated_conseqs)

    def annotate_and_count_traits(self, record):
        for trait in record.traits_with_valid_names:
            # Get current EFO ids - only used for evaluation
            existing_efo_ids = set()
            for db, iden, _ in trait.current_efo_aligned_xrefs:
                curie = OntologyUri(iden, db).curie
                if curie:
                    existing_efo_ids.add(curie)

            # Add annotations - only based on preferred name
            target_ontology_ids = [
                OntologyMappedClinVarTrait.format_ontology_id(ontology_id)
                for ontology_id, ontology_label
                in self.string_to_ontology_mappings.get(trait.preferred_or_other_valid_name.lower(), [])
            ]
            trait.add_ontology_mappings(target_ontology_ids, self.target_ontology)

            # Evaluation
            if self.eval_xref_mappings and self.eval_latest_mappings:
                existing_current_efo_ids = set()
                for cv_id in existing_efo_ids:
                    # Check whether existing ID is obsolete
                    self.obsolete_counts['cv_total'] += 1
                    if self.eval_xref_mappings[cv_id]['is_obsolete']:
                        self.obsolete_counts['cv_obsolete'] += 1
                    # Only record current EFO-contained IDs for comparison
                    elif self.eval_xref_mappings[cv_id]['synonyms']:
                        existing_current_efo_ids.add(cv_id)

                annotated_current_efo_ids = set()
                for efo_id in target_ontology_ids:

                    # Check whether annotated ID is obsolete
                    self.obsolete_counts['cmat_total'] += 1
                    if self.eval_latest_mappings[efo_id]['is_obsolete']:
                        self.obsolete_counts['cmat_obsolete'] += 1
                        # Don't add to the set of annotations if obsolete
                        continue

                    for cv_id in existing_current_efo_ids:
                        # Attempt to match an ID in ClinVar based on synonyms - if our ID is in the list of synonyms for
                        # a ClinVar ID (or vice versa), we use the synonymous ClinVar ID for comparison.
                        if (efo_id in self.eval_xref_mappings[cv_id]['synonyms']
                                or cv_id in self.eval_latest_mappings[efo_id]['synonyms']):
                            annotated_current_efo_ids.add(cv_id)

                    # If didn't find anything, just use our ID, which will count as not matching.
                    if not annotated_current_efo_ids:
                        annotated_current_efo_ids.add(efo_id)

                self.trait_metrics.count_and_score(cv_set=existing_current_efo_ids, cmat_set=annotated_current_efo_ids)
                # Output mismatches for manual inspection
                if existing_current_efo_ids and annotated_current_efo_ids and len(existing_current_efo_ids & annotated_current_efo_ids) == 0:
                    self.mismatches_file.write(f"{record.accession}\t{','.join(existing_current_efo_ids)}\t{','.join(annotated_current_efo_ids)}\n")

    def report(self):
        print('\nOverall counts (RCVs):')
        self.print_counter(self.overall_counts)
        if self.eval_gene_mappings:
            print('\nGene annotations:')
            self.gene_metrics.report()
            print('\nFunctional consequences:')
            self.conseq_metrics.report()

            print('\nBy variant type:')
            print('\n\tSimple (genes):')
            self.simple_variant_metrics[0].report()
            print('\n\tSimple (consequences):')
            self.simple_variant_metrics[1].report()
            print('\n\tRepeat (genes):')
            self.repeat_variant_metrics[0].report()
            print('\n\tRepeat (consequences):')
            self.repeat_variant_metrics[1].report()
            print('\n\tComplex (genes):')
            self.complex_variant_metrics[0].report()
            print('\n\tComplex (consequences):')
            self.complex_variant_metrics[1].report()

        if self.eval_xref_mappings:
            print('\nTrait mappings:')
            self.trait_metrics.report()
            print('\nObsolete terms:')
            self.print_counter(self.obsolete_counts)
        print()

    @staticmethod
    def print_counter(counter):
        max_len = len(max(counter.keys(), key=lambda x: len(x)))
        for k, v in counter.items():
            print(f'{k: <{max_len}} {v}')


class AnnotatedClinVarRecord(ClinVarRecord):

    def __init__(self, record_xml, xsd_version):
        super().__init__(record_xml, xsd_version, trait_class=OntologyMappedClinVarTrait,
                         measure_class=EnsemblAnnotatedClinVarMeasure)


class OntologyMappedClinVarTrait(ClinVarTrait):

    def add_ontology_mappings(self, ontology_ids, target_ontology):
        ontology_elts = []
        for ontology_id in ontology_ids:
            ontology_id = self.format_ontology_id(ontology_id)
            # Include Status attribute so this isn't included among current xrefs
            ontology_elts.append(ET.Element('XRef', attrib={
                'ID': ontology_id, 'DB': target_ontology, 'Status': 'annotated', 'providedBy': PROCESSOR}))
        self.trait_xml.extend(ontology_elts)

    @staticmethod
    def format_ontology_id(ontology_id):
        if ontology_id.startswith('http'):
            return ontology_id.split('/')[-1].replace('_', ':')
        return ontology_id


class EnsemblAnnotatedClinVarMeasure(ClinVarRecordMeasure):

    def add_ensembl_annotations(self, consequences):
        consequence_elts = []
        for consequence_attributes in consequences:
            attr_set_elt = ET.Element('AttributeSet', attrib={'providedBy': PROCESSOR})
            attribute_elt = ET.Element('Attribute', attrib={'Type': 'MolecularConsequence'})
            attribute_elt.text = consequence_attributes.so_term.so_name.replace('_', ' ')
            so_elt = ET.Element('XRef', attrib={'ID': self.format_so_term(consequence_attributes.so_term),
                                                'DB': 'Sequence Ontology'})
            ensembl_gene_elt = ET.Element('XRef', attrib={'ID': consequence_attributes.ensembl_gene_id,
                                                          'DB': 'Ensembl Gene'})
            attr_set_elt.extend((attribute_elt, so_elt, ensembl_gene_elt))
            # Add transcript if present
            if consequence_attributes.ensembl_transcript_id:
                ensembl_transcript_elt = ET.Element('XRef', attrib={'ID': consequence_attributes.ensembl_transcript_id,
                                                                    'DB': 'Ensembl Transcript'})
                attr_set_elt.append(ensembl_transcript_elt)
            consequence_elts.append(attr_set_elt)
        self.measure_xml.extend(consequence_elts)

    @staticmethod
    def format_so_term(so_term):
        return so_term.accession.replace('_', ':')


def load_evaluation_latest(input_path):
    mapping = {}
    with open(input_path) as input_file:
        for line in input_file:
            cols = line.strip().split('\t')
            if len(cols) != 3:
                continue
            mapping[cols[0]] = {
                'is_obsolete': cols[1] == 'True',
                'synonyms': string_to_set(cols[2])
            }
    return mapping


def load_evaluation_gene_mappings(input_path):
    mapping = defaultdict(list)
    with open(input_path) as input_file:
        for line in input_file:
            cols = line.strip().split('\t')
            if len(cols) != 2:
                continue
            mapping[cols[0]].append(cols[1])
    return mapping


def load_evaluation_xref_mappings(input_path):
    mapping = {}
    with open(input_path) as input_file:
        for line in input_file:
            cols = line.strip().split('\t')
            if len(cols) == 5:
                mapping[cols[0]] = {
                    'is_obsolete': cols[1] == 'True',
                    'synonyms': string_to_set(cols[2]),
                    'parents': string_to_set(cols[3]),
                    'children': string_to_set(cols[4])
                }
            elif len(cols) == 3:
                mapping[cols[0]] = {
                    'is_obsolete': cols[1] == 'True',
                    'synonyms': string_to_set(cols[2])
                }
            else:
                continue
    return mapping


def string_to_set(s):
    return set(x for x in re.sub(r"{|}|'", '', s).split(', ') if x)


def generate_annotated_clinvar_xml(clinvar_xml_file, trait_mapping_file, gene_mapping_file, output_xml_file,
                                   eval_gene_file=None, eval_xref_file=None, eval_latest_file=None):
    """Generate an annotated XML file of ClinVar RCVs based on trait mapping and gene mapping files (as documented in
    clinvar_to_evidence_strings)."""
    string_to_ontology_mappings, target_ontology, _ = load_ontology_mapping(trait_mapping_file)
    variant_to_gene_mappings = CT.process_consequence_type_file(gene_mapping_file)
    # Need all files to do an evaluation
    if eval_gene_file and eval_xref_file and eval_latest_file:
        eval_gene_mappings = load_evaluation_gene_mappings(eval_gene_file)
        eval_xref_mappings = load_evaluation_xref_mappings(eval_xref_file)
        eval_latest_mappings = load_evaluation_latest(eval_latest_file)
        dataset = AnnotatingClinVarDataset(clinvar_xml_file, string_to_ontology_mappings, variant_to_gene_mappings,
                                           target_ontology,
                                           eval_gene_mappings=eval_gene_mappings,
                                           eval_xref_mappings=eval_xref_mappings,
                                           eval_latest_mappings=eval_latest_mappings)
    else:
        dataset = AnnotatingClinVarDataset(clinvar_xml_file, string_to_ontology_mappings, variant_to_gene_mappings,
                                           target_ontology)
    dataset.write(output_xml_file)
    dataset.report()
