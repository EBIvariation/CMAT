import json
import os

import requests
import xml.etree.ElementTree as ElementTree

from cmat.clinvar_xml_io import ClinVarTrait
from cmat.output_generation import clinvar_to_evidence_strings
from cmat.output_generation import consequence_type as CT
from cmat.output_generation.clinvar_to_evidence_strings import MAX_TARGET_GENES

import config

EFO_MAPPINGS, _ = clinvar_to_evidence_strings.load_ontology_mapping(config.efo_mapping_file)
GENE_MAPPINGS = CT.process_consequence_type_file(config.snp_2_gene_file)


class TestGetMappingsTest:
    @classmethod
    def setup_class(cls):
        cls.efo_mappings = EFO_MAPPINGS
        cls.gene_mappings = GENE_MAPPINGS

    def test_efo_mapping(self):
        assert len(self.efo_mappings) == 10

        assert self.efo_mappings['renal-hepatic-pancreatic dysplasia 2'][0] == (
            'http://www.orpha.net/ORDO/Orphanet_294415', 'Renal-hepatic-pancreatic dysplasia')
        assert self.efo_mappings['frontotemporal dementia, ubiquitin-positive'][0] == (
            'http://www.orpha.net/ORDO/Orphanet_282', 'Frontotemporal dementia')
        assert self.efo_mappings['3 beta-hydroxysteroid dehydrogenase deficiency'][0] == (
            'http://www.orpha.net/ORDO/Orphanet_90791',
            'Congenital adrenal hyperplasia due to 3-beta-hydroxysteroid dehydrogenase deficiency')

        assert self.efo_mappings['coronary artery disease/myocardial infarction'] == [
            ('http://www.ebi.ac.uk/efo/EFO_0000612', 'myocardial infarction'),
            ('http://www.ebi.ac.uk/efo/EFO_0001645', 'coronary heart disease')]

    def test_consequence_type_dict(self):
        assert len(self.gene_mappings) == 22

        assert '14:67727191:G:A' in self.gene_mappings
        assert '14:67727197:C:T' in self.gene_mappings
        assert '14:67729179:T:C' in self.gene_mappings
        assert '14:67729307:CG:C' in self.gene_mappings

        assert 'rs0' not in self.gene_mappings
        assert 'rs5' not in self.gene_mappings
        assert 'rs9' not in self.gene_mappings


class TestGetTermsFromFileTest:
    @classmethod
    def setup_class(cls):
        ignore_file = os.path.join(os.path.dirname(__file__), 'resources', 'ignore_file.txt')
        cls.ignore_terms = clinvar_to_evidence_strings.get_terms_from_file(ignore_file)

    def test_with_file(self):
        assert len(self.ignore_terms) == 218
        assert self.ignore_terms[0] == "http://purl.obolibrary.org/obo/HP_0011677"
        assert self.ignore_terms[-1] == "http://www.orpha.net/ORDO/Orphanet_120795"

    def test_no_file(self):
        assert clinvar_to_evidence_strings.get_terms_from_file(None) == []


class TestConvertAlleleOrigins:
    def test_just_germline(self):
        orig_allele_origins = ['germline']
        converted_allele_origins = clinvar_to_evidence_strings.convert_allele_origins(orig_allele_origins)
        assert [['germline']] == converted_allele_origins

    def test_just_somatic(self):
        orig_allele_origins = ['somatic']
        converted_allele_origins = clinvar_to_evidence_strings.convert_allele_origins(orig_allele_origins)
        assert [['somatic']] == converted_allele_origins

    def test_mixed_germline(self):
        orig_allele_origins = ['germline', 'inherited', 'not applicable']
        converted_allele_origins = clinvar_to_evidence_strings.convert_allele_origins(orig_allele_origins)
        assert [['germline', 'inherited', 'not applicable']] == converted_allele_origins

    def test_duplicate(self):
        orig_allele_origins = ['germline', 'germline']
        converted_allele_origins = clinvar_to_evidence_strings.convert_allele_origins(orig_allele_origins)
        assert [['germline']] == converted_allele_origins
        orig_allele_origins = ['inherited', 'inherited', 'germline']
        converted_allele_origins = clinvar_to_evidence_strings.convert_allele_origins(orig_allele_origins)
        assert [['germline', 'inherited']] == converted_allele_origins
        orig_allele_origins = ['somatic', 'somatic', 'somatic']
        converted_allele_origins = clinvar_to_evidence_strings.convert_allele_origins(orig_allele_origins)
        assert [['somatic']] == converted_allele_origins

    def test_stringcase(self):
        orig_allele_origins = ['Germline']
        converted_allele_origins = clinvar_to_evidence_strings.convert_allele_origins(orig_allele_origins)
        assert [['germline']] == converted_allele_origins
        orig_allele_origins = ['SOMATIC']
        converted_allele_origins = clinvar_to_evidence_strings.convert_allele_origins(orig_allele_origins)
        assert [['somatic']] == converted_allele_origins

    def test_mixed(self):
        orig_allele_origins = ['germline', 'somatic']
        converted_allele_origins = clinvar_to_evidence_strings.convert_allele_origins(orig_allele_origins)
        assert [['somatic'], ['germline']] == converted_allele_origins
        orig_allele_origins = ['somatic', 'inherited', 'not applicable']
        converted_allele_origins = clinvar_to_evidence_strings.convert_allele_origins(orig_allele_origins)
        assert [['somatic'], ['inherited', 'not applicable']] == converted_allele_origins

    def test_missing(self):
        orig_allele_origins = []
        converted_allele_origins = clinvar_to_evidence_strings.convert_allele_origins(orig_allele_origins)
        assert [[]] == converted_allele_origins


class TestGetConsequenceTypes:

    @classmethod
    def setup_class(cls):
        # A single example ClinVar record
        cls.test_crm = config.get_test_clinvar_record().measure
        # Example result from the gene & functional consequence mapping pipeline for several variants
        cls.consequence_type_dict = GENE_MAPPINGS

    def test_get_consequence_types(self):
        assert clinvar_to_evidence_strings.get_consequence_types(self.test_crm, self.consequence_type_dict)[
                   0][0] == CT.ConsequenceType('ENSG00000139988', CT.SoTerm('missense_variant')), ''
        assert clinvar_to_evidence_strings.get_consequence_types(self.test_crm, {})[0] == []

    def test_structural_variant_consequences(self):
        structural_crm = config.get_test_clinvar_record('test_structural_record.xml.gz').measure
        consequences = [CT.ConsequenceType('ENSG00000075151', CT.SoTerm('splice_polypyrimidine_tract_variant'))]
        consequence_dict = {structural_crm.preferred_current_hgvs.text: consequences}
        assert clinvar_to_evidence_strings.get_consequence_types(structural_crm, consequence_dict) == (consequences, 'COMPLEX')

        # don't get consequences if there are more than MAX_TARGET_GENES
        long_consequence_dict = {structural_crm.preferred_current_hgvs.text: consequences * (MAX_TARGET_GENES+1)}
        assert clinvar_to_evidence_strings.get_consequence_types(structural_crm, long_consequence_dict) == ([], 'NONE')


class TestGenerateEvidenceStringTest:
    """Verifies that the evidence strings generated from a test ClinVar record matches the expectation."""

    def setup_method(self):
        # This is required to display evidence string diffs (if any)
        self.maxDiff = None
        # Attributes for the evidence string generation
        self.clinvar_record = config.get_test_clinvar_record()
        self.disease_name = 'Rare congenital non-syndromic heart malformation'
        self.disease_source_id = 'C4017284'
        self.disease_mapped_efo_id = 'Orphanet_88991'
        self.consequence_attributes = GENE_MAPPINGS['14:67729209:A:G'][0]
        # Open Targets JSON schema
        schema_url = f'https://raw.githubusercontent.com/opentargets/json_schema/{config.OT_SCHEMA_VERSION}/' \
                     f'schemas/disease_target_evidence.json'
        self.ot_schema_contents = requests.get(schema_url).json()

    def test_genetics_evidence_string(self):
        """Verifies expected genetics evidence string generation."""
        evidence = clinvar_to_evidence_strings.generate_evidence_string(
            clinvar_record=self.clinvar_record,
            allele_origins=['germline'],
            disease_name=self.disease_name,
            disease_source_id=self.disease_source_id,
            disease_mapped_efo_id=self.disease_mapped_efo_id,
            consequence_attributes=self.consequence_attributes
        )
        # Check that the evidence string validates against schema
        clinvar_to_evidence_strings.validate_evidence_string(evidence, self.ot_schema_contents)
        # Check that the evidence string contents are as expected
        evidence_string = json.dumps(evidence, sort_keys=True, indent=2)
        expected_evidence_string = config.get_expected_evidence_string('genetics')
        assert evidence_string == expected_evidence_string

    def test_somatic_evidence_string(self):
        """Verifies expected somatic evidence string generation."""
        evidence = clinvar_to_evidence_strings.generate_evidence_string(
            clinvar_record=self.clinvar_record,
            allele_origins=['somatic'],
            disease_name=self.disease_name,
            disease_source_id=self.disease_source_id,
            disease_mapped_efo_id=self.disease_mapped_efo_id,
            consequence_attributes=self.consequence_attributes
        )
        # Check that the evidence string validates against schema
        clinvar_to_evidence_strings.validate_evidence_string(evidence, self.ot_schema_contents)
        # Check that the evidence string contents are as expected
        evidence_string = json.dumps(evidence, sort_keys=True, indent=2)
        expected_evidence_string = config.get_expected_evidence_string('somatic')
        assert evidence_string == expected_evidence_string

    def test_multiple_trait_names_evidence_string(self):
        """Verifies evidence string generation when there are multiple traits for a record
        and multiple names for a trait."""
        record = config.get_test_clinvar_record('multiple_names.xml.gz')
        evidence = clinvar_to_evidence_strings.generate_evidence_string(
            clinvar_record=record,
            allele_origins=['somatic'],
            disease_name='Skeletal dysplasia',
            disease_source_id='C0410528',
            disease_mapped_efo_id='HP_0002652',
            consequence_attributes=self.consequence_attributes
        )
        # Check that the evidence string validates against schema
        clinvar_to_evidence_strings.validate_evidence_string(evidence, self.ot_schema_contents)
        # Check that the evidence string contents are as expected
        evidence_string = json.dumps(evidence, sort_keys=True, indent=2)
        expected_evidence_string = config.get_expected_evidence_string('multiple_names')
        assert evidence_string == expected_evidence_string

    def test_no_mapping_evidence_string(self):
        """Verifies evidence string generation when there are no EFO mappings for a trait."""
        evidence = clinvar_to_evidence_strings.generate_evidence_string(
            clinvar_record=self.clinvar_record,
            allele_origins=['somatic'],
            disease_name=self.disease_name,
            disease_source_id=self.disease_source_id,
            disease_mapped_efo_id=None,
            consequence_attributes=self.consequence_attributes
        )
        # Check that the evidence string validates against schema
        clinvar_to_evidence_strings.validate_evidence_string(evidence, self.ot_schema_contents)
        # Check that diseaseFromSourceMappedId is not present
        assert 'diseaseFromSourceMappedId' not in evidence

    def test_no_allele_origins_evidence_string(self):
        """Verifies evidence string generation when there are no allele origins."""
        evidence = clinvar_to_evidence_strings.generate_evidence_string(
            clinvar_record=self.clinvar_record,
            allele_origins=[],
            disease_name=self.disease_name,
            disease_source_id=self.disease_source_id,
            disease_mapped_efo_id=self.disease_mapped_efo_id,
            consequence_attributes=self.consequence_attributes
        )
        # Check that the evidence string validates against schema
        clinvar_to_evidence_strings.validate_evidence_string(evidence, self.ot_schema_contents)
        # Check that alleleOrigins is not present and datatype is eva
        assert 'alleleOrigins' not in evidence
        assert evidence['datasourceId'] == 'eva'


class TestGroupDiseasesByMappingTest:
    """Verifies behaviour of group_diseases_by_efo_mapping."""

    def setup_method(self):
        self.string_to_efo_mappings = {
            'disease a': [('EFO_1', 'Term 1')],
            'disease b': [('EFO_1', 'Term 1')],
            'disease c': [('EFO_1', 'Term 1')],
            'disease d': [('EFO_2', 'Term 2'), ('EFO_3', 'Term 3')]
        }

    @staticmethod
    def get_trait(name, medgen):
        """Return ClinVarTrait with given name and medgen id."""
        # template for trait xml that allows name and medgen id to be inserted
        trait_xml_template = f'''
        <Trait ID="123" Type="Disease">
            <Name>
                <ElementValue Type="Preferred">{name}</ElementValue>
            </Name>
            <XRef ID="{medgen}" DB="MedGen" />
        </Trait>
        '''
        return ClinVarTrait(trait_xml=ElementTree.fromstring(trait_xml_template), clinvar_record=None)

    def test_multiple_diseases_mapped_to_one_term(self):
        """Diseases mapped to same EFO term should be grouped together, and the lexicographically first one returned."""
        trait_a = self.get_trait('Disease A', 'MedGen_A')
        trait_b = self.get_trait('Disease B', 'MedGen_B')
        trait_c = self.get_trait('Disease C', 'MedGen_C')
        expected_result = [('Disease A', 'MedGen_A', 'EFO_1')]
        result = clinvar_to_evidence_strings.group_diseases_by_efo_mapping(
            clinvar_record_traits=[trait_b, trait_c, trait_a],
            string_to_efo_mappings=self.string_to_efo_mappings,
        )
        assert result == expected_result

    def test_one_disease_mapped_to_multiple_terms(self):
        """One disease mapped to multiple terms should be split."""
        trait_d = self.get_trait('Disease D', 'MedGen_D')
        expected_result = [('Disease D', 'MedGen_D', 'EFO_2'), ('Disease D', 'MedGen_D', 'EFO_3')]
        result = clinvar_to_evidence_strings.group_diseases_by_efo_mapping(
            clinvar_record_traits=[trait_d],
            string_to_efo_mappings=self.string_to_efo_mappings,
        )
        assert result == expected_result

    def test_disease_without_mapping(self):
        """Diseases without mappings should be included but not grouped."""
        trait_e = self.get_trait('Disease E', 'MedGen_E')
        trait_f = self.get_trait('Disease F', 'MedGen_F')
        expected_result = [('Disease E', 'MedGen_E', None), ('Disease F', 'MedGen_F', None)]
        result = clinvar_to_evidence_strings.group_diseases_by_efo_mapping(
            clinvar_record_traits=[trait_e, trait_f],
            string_to_efo_mappings=self.string_to_efo_mappings,
        )
        assert result == expected_result
