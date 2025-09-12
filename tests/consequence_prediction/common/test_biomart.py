from cmat.consequence_prediction.common.biomart import query_biomart


def test_query_biomart():
    key_column = ('hgnc_id', 'HGNC_ID')
    query_columns = [('ensembl_gene_id', 'EnsemblGeneID'), ('ensembl_transcript_id', 'EnsemblTranscriptID')]
    identifier_list = ['HGNC:10548', 'HGNC:10560']
    result_df = query_biomart(key_column, query_columns, identifier_list)
    assert set(result_df.columns) == {'HGNC_ID', 'EnsemblGeneID', 'EnsemblTranscriptID'}
    assert len(result_df) == 37
    assert set(result_df['HGNC_ID']) == set(identifier_list)
    assert set(result_df['EnsemblGeneID']) == {'ENSG00000163635', 'ENSG00000124788'}
