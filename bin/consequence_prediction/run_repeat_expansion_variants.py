#!/usr/bin/env python3
"""A wrapper script for running the repeat expansion pipeline."""

import argparse
from cmat.consequence_prediction.repeat_expansion_variants import pipeline

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    '--clinvar-xml', required=True,
    help='ClinVar XML dump file (ClinVarFullRelease_00-latest.xml.gz)'
)
parser.add_argument(
    '--include-transcripts', required=False, action='store_true',
    help='Whether to include transcript IDs along with consequence terms'
)
parser.add_argument(
    '--output-consequences', required=True,
    help='File to output functional consequences to. Format is compatible with the main VEP mapping pipeline.'
)
parser.add_argument(
    '--output-dataframe', required=False,
    help='File to output full dataframe for subsequent analysis and debugging.'
)
args = parser.parse_args()
pipeline.main(args.clinvar_xml, args.include_transcripts, args.output_consequences, args.output_dataframe)
