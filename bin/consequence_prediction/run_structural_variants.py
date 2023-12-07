#!/usr/bin/env python3
"""A wrapper script for running the structural variant pipeline."""

import argparse
from cmat.consequence_prediction.structural_variants import pipeline

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    '--clinvar-xml', required=True,
    help='ClinVar XML dump file (ClinVarFullRelease_00-latest.xml.gz)'
)
parser.add_argument(
    '--output-consequences', required=True,
    help='File to output functional consequences to. Format is compatible with the main VEP mapping pipeline.'
)

args = parser.parse_args()
pipeline.main(args.clinvar_xml, args.output_consequences)
