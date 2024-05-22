import os

from cmat.clinvar_xml_io.xml_parsing import parse_header_attributes


resources_dir = os.path.join(os.path.dirname(__file__), 'resources')


def test_parse_header_attributes():
    input_file = os.path.join(resources_dir, 'test_clinvar_dataset.xml.gz')
    header_attr = parse_header_attributes(input_file)
    assert header_attr['Dated'] == '2023-02-22'
    assert header_attr['xsi:noNamespaceSchemaLocation'] == 'http://ftp.ncbi.nlm.nih.gov/pub/clinvar/xsd_public/clinvar_public_1.60.xsd'
