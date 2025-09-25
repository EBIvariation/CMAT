#!/usr/bin/env python3

import argparse
from collections import Counter
import logging

import matplotlib.pyplot as plt
import numpy as np
from sankeyflow import Sankey

from cmat import clinvar_xml_io
from cmat.clinvar_xml_io.clinical_classification import MultipleClinicalClassificationsError

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Ensure that divide by zero raises an exception rather than a warning
np.seterr(divide='raise')


class SankeyDiagram(Counter):

    def __init__(self, name, width, height):
        super().__init__()
        self.name = name
        self.width = width
        self.height = height

    def add_transitions(self, *transition_chain):
        """For example, if a transition chain is (RCV, MeasureSet, Variant), two transitions will be added to the Sankey
        diagram: (RCV → MeasureSet) and (MeasureSet → Variant)."""
        for t_from, t_to in zip(transition_chain, transition_chain[1:]):
            self[(t_from, t_to)] += 1

    def generate_diagram(self):
        """Generate and save a Sankey diagram directly to file."""
        dpi = 144
        plt.figure(figsize=(self.width/dpi, self.height/dpi), dpi=dpi)
        flows = [(self._format_label(t_from), self._format_label(t_to), t_count)
                 for (t_from, t_to), t_count in sorted(self.items(), key=lambda x: -x[1])]
        try:
            logger.info(f'Generating diagram: {self.name}')
            s = Sankey(flows=flows,
                       node_pad_y_min=0.04,
                       node_pad_y_max=0.08,
                       node_opts=dict(label_format='{label}: {value}', label_opts=dict(fontsize=8)))
        except FloatingPointError:
            # Perturb values to avoid divide-by-zero errors. TODO: come up with a better solution to this
            plt.figure(figsize=(self.width/dpi, (self.height+1)/dpi), dpi=dpi)
            s = Sankey(flows=flows,
               node_pad_y_min=0.03,
               node_pad_y_max=0.08,
               node_opts=dict(label_format='{label}: {value}', label_opts=dict(fontsize=8)))
        s.draw()
        plt.savefig(self.name, bbox_inches='tight')

    def _format_label(self, label):
        max_len = 20
        words = label.split()
        lines = []
        line = ''
        while len(words) > 0:
            while len(line) < max_len and len(words) > 0:
                line += f' {words.pop(0)}'
            lines.append(line)
            line = ''
        return '\n'.join(lines)

    def __str__(self):
        lines = [f'========== SANKEY DIAGRAM: {self.name} ==========',
                 f'Build using http://sankeymatic.com/build/ with width={self.width}, height={self.height}']
        for (t_from, t_to), t_count in sorted(self.items(), key=lambda x: -x[1]):
            lines.append(f'    {t_from} [{t_count}] {t_to}')
        return '\n'.join(lines)


class SupplementaryTable:

    def __init__(self, name, fields, sort_lambda=None):
        self.name = name
        self.fields = fields
        self.data = []
        self.sort_lambda = sort_lambda

    def add_row(self, row):
        assert len(row) == len(self.fields), 'Incorrect length of the row supplied'
        self.data.append(row)

    def __str__(self):
        lines = [f'>>>>>>>>>> SUPPLEMENTARY TABLE: {self.name} <<<<<<<<<<',
                 '|'.join(self.fields), '|'.join(':--' for _ in range(len(self.fields)))]
        sorted_data = sorted(self.data, key=self.sort_lambda)
        for row in sorted_data:
            lines.append('|'.join([str(v) for v in row]))
        return '\n'.join(lines)


class SupplementaryTableCounter(SupplementaryTable):

    def __init__(self, name, field_name, sort_lambda=lambda x: -x[1]):
        super().__init__(name=name, fields=(field_name, 'Count'), sort_lambda=sort_lambda)
        self.counter = Counter()

    def add_count(self, item):
        self.counter[item] += 1

    def __str__(self):
        # On demand, tally the counter, add the rows, and return the standard string representation
        for item, count in self.counter.items():
            self.add_row([item, count])
        return super().__str__()


def find_attribute(rcv, xpath, attribute_name):
    """Find an attribute in the RCV record which can have either zero or one occurrence. Return a textual representation
    of the attribute, including special representations for the case of zero or multiple, constructed using the
    attribute_name parameter."""
    attributes = rcv.findall(xpath)
    if len(attributes) == 0:
        return '{} missing'.format(attribute_name)
    elif len(attributes) == 1:
        return attributes[0].text
    else:
        return '{} multiple'.format(attribute_name)


def review_status_stars(score):
    black_stars = score
    white_stars = 4 - black_stars
    return '★' * black_stars + '☆' * white_stars


def rcv_to_link(rcv_id):
    return f'[{rcv_id}](https://www.ncbi.nlm.nih.gov/clinvar/{rcv_id}/)'


def main(clinvar_xml, process_items=None, print_diagram_source=False):
    # Sankey diagrams for visualisation
    sankey_variation_representation = SankeyDiagram('variant-types.png', 1200, 600)
    sankey_trait_representation = SankeyDiagram('traits.png', 1200, 400)
    sankey_trait_xrefs = SankeyDiagram('trait-xrefs.png', 1200, 400)
    sankey_clinical_classification = SankeyDiagram('clinical-classification.png', 1400, 800)
    sankey_star_rating = SankeyDiagram('star-rating.png', 1400, 600)
    sankey_mode_of_inheritance = SankeyDiagram('mode-of-inheritance.png', 1200, 500)
    sankey_allele_origin = SankeyDiagram('allele-origin.png', 1200, 600)
    sankey_inheritance_origin = SankeyDiagram('inheritance-origin.png', 1200, 400)

    # Supplementary tables and counters for the report
    counter_trait_xrefs = SupplementaryTableCounter('All trait cross-references', 'Source')
    counter_clin_class_complex = SupplementaryTableCounter('Complex clinical classification levels', 'Clinical classification')
    counter_clin_class_all = SupplementaryTableCounter('All clinical classification levels', 'Clinical classification')
    counter_star_rating = SupplementaryTableCounter(
        'Distribution of records by star rating', 'Star rating', sort_lambda=lambda x: x[0])
    counter_obs_method_type = SupplementaryTableCounter('All observation method types', 'Observation method type')
    table_multiple_mode_of_inheritance = SupplementaryTable(
        'Multiple mode of inheritance', ['RCV', 'Modes of inheritance'], sort_lambda=lambda x: (x[1], x[0]))
    counter_multiple_allele_origin = SupplementaryTableCounter('Multiple allele origins', 'Allele origins')
    table_inconsistent_moi_ao = SupplementaryTable(
        'Inconsistent mode of inheritance and allele origin values', ['RCV', 'Modes of inheritance', 'Allele origins'],
        sort_lambda=lambda x: (x[1], x[2], x[0]))

    elements_processed = 0
    for clinvar_record in clinvar_xml_io.ClinVarDataset(clinvar_xml):
        rcv_id = clinvar_record.accession

        # RCV can contain either a MeasureSet, or a GenotypeSet. It must not contain both.
        measure_sets = clinvar_record.record_xml.findall('MeasureSet')
        genotype_sets = clinvar_record.record_xml.findall('GenotypeSet')
        if len(measure_sets) == 1 and len(genotype_sets) == 0:
            # Most common case. RCV directly contains one measure set.
            measure_set = measure_sets[0]
            measure_set_type = measure_set.attrib['Type']
            sankey_variation_representation.add_transitions('RCV', 'MeasureSet', measure_set_type)

            # Only go into details for single variants, the most common type
            if measure_set_type != 'Variant':
                continue

            # Variation representation
            measures = measure_set.findall('Measure')
            assert len(measures) == 1, 'MeasureSet of type Variant must contain exactly one Measure'
            sankey_variation_representation.add_transitions(measure_set_type, measures[0].attrib['Type'])

            # Trait representation
            traits = clinvar_record.traits
            if len(traits) == 0:
                raise AssertionError('There must always be at least one trait')
            elif len(traits) == 1:
                traits_category = 'One trait'
            else:
                traits_category = 'Multiple traits'
            names_category = 'One name per trait'
            ontology_category = 'No EFO-aligned xrefs'
            for trait in traits:
                if len(trait.all_names) > 1:
                    names_category = 'Multiple names per trait'
                if len(trait.current_efo_aligned_xrefs) > 1:
                    ontology_category = 'Has EFO-aligned xrefs'
                # Count all xref sources for each trait
                for db, _, _ in trait.xrefs:
                    counter_trait_xrefs.add_count(db)
            sankey_trait_representation.add_transitions('Variant', clinvar_record.trait_set_type, traits_category, names_category)
            sankey_trait_xrefs.add_transitions('Variant', clinvar_record.trait_set_type, traits_category, ontology_category)

            # Clinical classification
            class_cardinality = 'Single classification'
            if len(clinvar_record.clinical_classifications) > 1:
                class_cardinality = 'Multiple classifications'
            # Somatic, germline, oncogenic, or combinations thereof
            class_type = ', '.join(sorted(clin_class.type for clin_class in clinvar_record.clinical_classifications))
            for clin_class in clinvar_record.clinical_classifications:
                try:
                    # New in V2 attributes for somatic classifications
                    # TODO maybe do this only for somatic
                    #  (first check with the whole dataset that there's nothing for germline/oncogenic...)
                    assertion_type = clin_class.somatic_assertion_type or "no assertion type"
                    clinical_impact = clin_class.somatic_clinical_impact or "no clinical impact"

                    clin_class_split = clin_class.clinical_significance_list
                    clin_class_raw = clin_class.clinical_significance_raw
                    # Count all individual clinical classification terms
                    for clin_class_term in clin_class_split:
                        counter_clin_class_all.add_count(clin_class_term)
                    # Simple terms included in the diagram
                    if len(clin_class_split) == 1:
                        sankey_clinical_classification.add_transitions(
                            'Variant', class_cardinality, class_type, assertion_type, clinical_impact, 'Simple',
                            clin_class_raw)
                    # Compound terms included in supplementary tables only
                    else:
                        sankey_clinical_classification.add_transitions(
                            'Variant', class_cardinality, class_type, assertion_type, clinical_impact, 'Complex')
                        counter_clin_class_complex.add_count(clin_class_raw)
                except MultipleClinicalClassificationsError as e:
                    # Multiple descriptions within a single clinical classification
                    # TODO think about how to deal with these - count or visualise
                    sankey_clinical_classification.add_transitions('Variant', class_cardinality, class_type,
                                                                   'Multiple assertions')

            # Review status, star rating, and observation method type
            try:
                review_status = clinvar_record.review_status
                star_rating = review_status_stars(clinvar_record.score)
                observation_method_type = ', '.join(sorted(set(clinvar_record.observation_method_types)))
                sankey_star_rating.add_transitions('Variant', 'Single classification', star_rating, review_status,
                                                   observation_method_type)
                counter_star_rating.add_count(star_rating)
                for obs_method_type in clinvar_record.observation_method_types:
                    counter_obs_method_type.add_count(obs_method_type)
            except MultipleClinicalClassificationsError:
                # TODO think about how to deal with these
                sankey_star_rating.add_transitions('Variant', 'Multiple classifications')

            # Mode of inheritance
            modes_of_inheritance = clinvar_record.mode_of_inheritance
            modes_of_inheritance_text = ', '.join(sorted(modes_of_inheritance))
            if len(modes_of_inheritance) == 0:
                mode_of_inheritance_category = 'Missing'
            elif 'Somatic mutation' in modes_of_inheritance:
                if len(modes_of_inheritance) > 1:
                    mode_of_inheritance_category = 'Germline & somatic'
                else:
                    mode_of_inheritance_category = 'Somatic'
            else:
                mode_of_inheritance_category = 'Germline'
            sankey_mode_of_inheritance.add_transitions('Variant', mode_of_inheritance_category)
            if mode_of_inheritance_category == 'Germline':
                if len(modes_of_inheritance) == 1:
                    sankey_mode_of_inheritance.add_transitions('Germline', 'Single', modes_of_inheritance_text)
                else:
                    sankey_mode_of_inheritance.add_transitions('Germline', 'Multiple')
            # Log multiple ModeOfInheritance cases in a separate table
            if len(modes_of_inheritance) > 1:
                table_multiple_mode_of_inheritance.add_row([rcv_to_link(rcv_id), modes_of_inheritance_text])

            # Allele origins
            allele_origins = clinvar_record.allele_origins
            allele_origin_text = ', '.join(sorted(allele_origins))
            if len(allele_origins) == 0:
                allele_origin_category = 'Missing'
            elif 'somatic' in allele_origins:
                if len(allele_origins) > 1:
                    allele_origin_category = 'Germline & somatic'
                else:
                    allele_origin_category = 'Somatic'
            else:
                allele_origin_category = 'Germline'
            sankey_allele_origin.add_transitions('Variant', allele_origin_category)
            if allele_origin_category == 'Germline':
                if len(allele_origins) == 1:
                    sankey_allele_origin.add_transitions(allele_origin_category, 'Single', allele_origin_text)
                else:
                    sankey_allele_origin.add_transitions(allele_origin_category, 'Multiple')
            # Log multiple allele of origin values in a separate table
            if len(allele_origins) > 1:
                counter_multiple_allele_origin.add_count(allele_origin_text)

            # Mode of inheritance and allele origin mapping
            if mode_of_inheritance_category != 'Missing' and allele_origin_category != 'Missing':
                sankey_inheritance_origin.add_transitions(
                    f'[MoI] {mode_of_inheritance_category}', f'{allele_origin_category} [AO]')
                if mode_of_inheritance_category != allele_origin_category:
                    table_inconsistent_moi_ao.add_row([rcv_to_link(rcv_id), modes_of_inheritance_text,
                                                       allele_origin_text])

        elif len(measure_sets) == 0 and len(genotype_sets) == 1:
            # RCV directly contains one genotype set.
            genotype_set = genotype_sets[0]
            sankey_variation_representation.add_transitions('RCV', 'GenotypeSet', genotype_set.attrib['Type'])
        else:
            raise AssertionError('RCV must contain either exactly one measure set, or exactly one genotype set')

        # Track the number of already processed elements
        elements_processed += 1
        if elements_processed % 100000 == 0:
            logger.info(f'Processed {elements_processed} elements')
        if process_items and elements_processed >= process_items:
            break

    logger.info(f'Done. Processed {elements_processed} elements')

    # Output the code for Sankey diagrams. Transitions are sorted in decreasing number of counts, so that the most frequent
    # cases are on top.
    for sankey_diagram in (sankey_variation_representation, sankey_trait_representation, sankey_trait_xrefs,
                           sankey_clinical_classification, sankey_star_rating, sankey_mode_of_inheritance,
                           sankey_allele_origin, sankey_inheritance_origin):
        if print_diagram_source:
            print('\n')
            print(sankey_diagram)
        sankey_diagram.generate_diagram()

    # Output the supplementary tables for the report.
    for supplementary_table in (counter_trait_xrefs, counter_clin_class_complex, counter_clin_class_all,
                                counter_star_rating, counter_obs_method_type, table_multiple_mode_of_inheritance,
                                counter_multiple_allele_origin, table_inconsistent_moi_ao):
        print('\n')
        print(supplementary_table)

    print('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--clinvar-xml', required=True)
    parser.add_argument('--process-items', type=int)
    parser.add_argument('--print-diagram-source', action='store_true', default=False)
    args = parser.parse_args()
    main(args.clinvar_xml, args.process_items, args.print_diagram_source)
