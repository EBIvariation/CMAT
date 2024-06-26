from cmat.output_generation import consequence_type as CT

import config


class TestClinvarRecord:
    @classmethod
    def setup_class(cls):
        cls.test_clinvar_record = config.get_test_clinvar_record()

    def test_date(self):
        """Check that the last updated date of the referenceClinVarAssertion is loaded correctly"""
        assert self.test_clinvar_record.date == '2024-04-15'

    def test_score(self):
        assert self.test_clinvar_record.score == 2

    def test_review_status(self):
        assert self.test_clinvar_record.review_status == 'criteria provided, multiple submitters, no conflicts'

    def test_acc(self):
        assert self.test_clinvar_record.accession == 'RCV000002127'

    def test_traits(self):
        assert self.test_clinvar_record.traits[0].preferred_name == 'Leber congenital amaurosis 13'
        assert self.test_clinvar_record.traits[0].preferred_or_other_valid_name == 'Leber congenital amaurosis 13'

    def test_trait_pubmed_refs(self):
        assert self.test_clinvar_record.traits[0].pubmed_refs == [20301590, 30285347]

    def test_observed_pubmed_refs(self):
        assert self.test_clinvar_record.evidence_support_pubmed_refs == [15258582, 15322982]

    def test_clinical_significance(self):
        assert self.test_clinvar_record.clinical_significance_list == ['likely pathogenic', 'pathogenic']

    def test_allele_origins(self):
        assert self.test_clinvar_record.allele_origins == {'germline', 'inherited', 'unknown'}

    def test_valid_allele_origins(self):
        assert self.test_clinvar_record.valid_allele_origins == {'germline', 'inherited'}

    def test_trait_efo_ids(self):
        assert self.test_clinvar_record.traits[0].current_efo_aligned_xrefs == [('MONDO', 'MONDO:0012990', 'current')]


class TestClinvarRecordMeasure:
    @classmethod
    def setup_class(cls):
        cls.test_crm = config.get_test_clinvar_record().measure
        cls.consequence_type_dict = CT.process_consequence_type_file(config.snp_2_gene_file)

    def test_hgvs(self):
        text_hgvs = [h.text for h in self.test_crm.all_hgvs]
        assert text_hgvs == ['NM_152443.3:c.677A>G',
                             'NG_008321.1:g.32324A>G',
                             'NC_000014.9:g.67729209A>G',
                             'NC_000014.8:g.68195926A>G',
                             'NM_152443.2:c.677A>G',
                             'Q96NR8:p.Tyr226Cys',
                             'NP_689656.2:p.Tyr226Cys']

    def test_preferred_current_hgvs(self):
        assert self.test_crm.preferred_current_hgvs.text == 'NC_000014.9:g.67729209A>G'

    def test_rs(self):
        assert self.test_crm.rs_id == 'rs28940313'

    def test_nsv(self):
        assert self.test_crm.nsv_id is None

    def test_variant_type(self):
        assert self.test_crm.variant_type == 'single nucleotide variant'

    def test_measure_set_pubmed_refs(self):
        assert self.test_crm.pubmed_refs == []

    def test_so_terms(self):
        assert self.test_crm.existing_so_terms == {'SO:0001583'}
