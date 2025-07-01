import argparse
import sys

import cmat.trait_mapping.main as main
from cmat.trait_mapping.utils import string_to_preferred_ontologies


def launch():
    parser = ArgParser(sys.argv)

    main.process_traits(parser.input_traits_filepath, parser.output_mappings_filepath,
                        parser.output_curation_filepath, parser.filters, parser.zooma_host,
                        parser.oxo_target_list, parser.oxo_distance, parser.ols_query_fields, parser.ols_field_list,
                        parser.target_ontology, parser.preferred_ontologies)


class ArgParser:

    def __init__(self, argv):
        description = """
                Script for running terms through Zooma, retrieving mapped uri, label from OLS,
                confidence of the mapping, and source of the mapping.
                """
        parser = argparse.ArgumentParser(description=description)

        parser.add_argument("-i", dest="input_traits_filepath", required=True,
                            help="path to input file for all traits")
        parser.add_argument("-o", dest="output_mappings_filepath", required=True,
                            help="path to output file for mappings")
        parser.add_argument("-c", dest="output_curation_filepath", required=True,
                            help="path to output file for curation")
        parser.add_argument("-n", dest="zooma_ontologies", default="efo,ordo,hp,mondo",
                            help="ontologies to use in zooma query")
        parser.add_argument("-r", dest="required", default="cttv,eva-clinvar,clinvar-xrefs,gwas",
                            help="data sources to use in query.")
        parser.add_argument("-p", dest="preferred", default="eva-clinvar,cttv,gwas,clinvar-xrefs",
                            help="preference for data sources, with preferred data source first.")
        parser.add_argument("-z", dest="zooma_host", default="https://www.ebi.ac.uk",
                            help="the host to use for querying zooma")
        parser.add_argument("-t", dest="oxo_target_list", default="Orphanet,efo,hp,mondo",
                            help="target ontologies to use with OxO")
        parser.add_argument("-d", dest="oxo_distance", default=3,
                            help="distance to use to query OxO.")
        parser.add_argument("-l", dest="ols_ontology_list", default="efo,mondo,hp",
                            help="ontologies to use with OLS search")
        parser.add_argument("-q", dest="ols_query_fields", default="label,synonym",
                            help="query fields to use for OLS search")
        parser.add_argument("-f", dest="ols_field_list", default="iri,label,ontology_name,synonym",
                            help="field list to return from OLS search")
        parser.add_argument('--target-ontology', help='ID of target ontology (default EFO, for allowable values see'
                                                      'https://www.ebi.ac.uk/ols/ontologies)', default='EFO')

        args = parser.parse_args(args=argv[1:])

        self.input_traits_filepath = args.input_traits_filepath
        self.output_mappings_filepath = args.output_mappings_filepath
        self.output_curation_filepath = args.output_curation_filepath

        self.filters = {"ontologies": args.zooma_ontologies,
                        "required": args.required,
                        "preferred": args.preferred}

        self.zooma_host = args.zooma_host
        self.oxo_target_list = [target.strip() for target in args.oxo_target_list.split(",")]
        self.oxo_distance = args.oxo_distance
        self.ols_query_fields = args.ols_query_fields
        self.ols_field_list = args.ols_field_list
        self.target_ontology = args.target_ontology
        self.preferred_ontologies = string_to_preferred_ontologies(args.ols_ontology_list, self.target_ontology)


if __name__ == '__main__':
    launch()
