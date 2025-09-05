import os

from cmat.consequence_prediction.structural_variants import pipeline


def get_test_resource(resource_name):
    """Gets full path to the test resource located in the same directory as the test module."""

    # Full path to this module.
    this_module = os.path.abspath(__file__)

    # Full path to the directory where it is contained.
    module_directory = os.path.dirname(this_module)

    # Full path to the requested resource.
    return os.path.join(module_directory, 'resources', resource_name)


def run_pipeline(resource_name, include_transcripts=False):
    """Runs the pipeline on a given test resource and returns the output consequences as a list of lists."""
    input_filename = get_test_resource(resource_name)
    consequences_df = pipeline.main(input_filename, include_transcripts)
    consequences = [[col for col in row] for row in consequences_df.itertuples(index=False)]
    return consequences


def test_successful_run():
    assert sorted(run_pipeline('precise_genomic.xml.gz')) == sorted([
        ['NC_000016.10:g.72059151_72063259del', 'ENSG00000257017', 'HP', 'stop_lost'],
        ['NC_000016.10:g.72059151_72063259del', 'ENSG00000261701', 'HPR', 'feature_truncation'],
        ['NC_000001.11:g.25271785_25329047del', 'ENSG00000117616', 'RSRP1', 'intron_variant'],
        ['NC_000001.11:g.25271785_25329047del', 'ENSG00000187010', 'RHD', 'stop_lost'],
        ['NC_000011.10:g.5226797_5226798insGCC', 'ENSG00000244734', 'HBB', 'feature_elongation']
    ])


def test_successful_run_with_transcripts():
    results = run_pipeline('precise_genomic.xml.gz', include_transcripts=True)
    assert len(results) == 50
    assert ['NC_000001.11:g.25271785_25329047del', 'ENSG00000187010', 'RHD', 'stop_lost', 'ENST00000454452'] in results


def test_has_complete_coordinates():
    assert run_pipeline('complete_coordinates.xml.gz') == []


def test_no_current_genomic_hgvs():
    assert run_pipeline('no_current_genomic_hgvs.xml.gz') == []


def test_no_valid_precise_span():
    assert run_pipeline('no_valid_precise_span.xml.gz') == []
