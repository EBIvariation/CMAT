# Manual curation, part II, biological: perform manual curation

The goal of the manual curation is to map traits in ClinVar to terms in EFO. We try to map as many as possible, but the 
following are priorities:
* Traits which are linked to NT expansion (nucleotide repeat expansion) variants. These are marked as "NT expansion" in
  the "Notes" column and ranked at the top of the spreadsheet.
* Traits with high frequency (≥ 10), as indicated in the "ClinVar Freq" column. The spreadsheet is sorted by this column
  to help with this.

Besides EFO, terms MONDO and HP are preferred, as these can be directly imported into EFO if not present.
Terms from other sources cannot be directly imported, but can be used as the basis for new EFO terms.

## Criteria to manually evaluate mapping quality

* Exact string for string matches are _good_
* Slight modifications are _good_ e.g. IRAK4 DEFICIENCY → Immunodeficiency due to interleukin-1 receptor-associated
  kinase-4 deficiency
* Subtype to parent are _good_ e.g ACHROMATOPSIA 3 → Achromatopsia, but **only if** there is not already a non-EFO exact
  string match for the subtype. If there is one, it should be prioritized and then term set as _IMPORT_
* Parent to subtype are _bad_ e.g. HEMOCHROMATOSIS → Hemochromatosis type 3
* Familial / congenital represented on only one half are _bad_ e.g. Familial renal glycosuria → Renal glycosuria
* Susceptibility on only one half is _bad_ e.g Alcohol dependence, susceptibility to → alcohol dependence
* Early / late onset on only one half is _bad_ e.g. Alzheimer disease, early-onset → Alzheimer's disease

In general, complex traits with modifiers (e.g. "autosomal recessive", "early onset", or "history of") should not be
mapped to the more general term (i.e. without modifiers) because it loses important information. For now the curator
should follow the same protocol as for any other term and request to import/create a new term containing the necessary
modifiers.

## Mapping string
The spreadsheet is populated by the pipeline with suggested mappings. The mapping strings have the format 
`URL|LABEL|MATCH_TYPE|MAPPING_SOURCE`.

* **Match type** indicates how closely the term label matches against the ClinVar trait name. Options are:
    * `EXACT_MATCH_LABEL`: the ClinVar trait matches the term label exactly
    * `EXACT_MATCH_SYNONYM`: the ClinVar trait matches a synonym of the term exactly
    * `CONTAINED_MATCH_LABEL`: the ClinVar trait is an exact substring of the term label
    * `CONTAINED_MATCH_SYNONYM`: as above but for a synonym of the term
    * `TOKEN_MATCH_LABEL`: the ClinVar trait has words in common with the term label
    * `TOKEN_MATCH_SYNONYM`: as above but for a synonym of the term
* **Mapping source** indicates where the term was found, i.e. which ontology. Options are:
    * `EFO_CURRENT`: contained in EFO and current (cell colored green)
    * `EFO_OBSOLETE`: contained in EFO but obsolete (red)
    * `MONDO_HP_NOT_EFO`: contained in Mondo or HP but not EFO (yellow)
    * `NOT_MONDO_HP_EFO`: any other (no color)

Some mappings will be in dedicated columns to help with filtering, while the rest are present in a ranked list "All
other mappings".

## Curation workflow

Curation should be done by applying filters to appropriate columns, then making decisions for the traits in
the filtered selection.

1. **High-confidence mappings:** These require minimal manual checking, as they include terms that match the trait
   perfectly or terms we've previously mapped.
    * 1.1 **Previous mappings**
        * 1.3.1 Filter "Previous mapping" column by fill colour: green (#B7E1CD)
        * 1.3.2 Copy the cell contents into "Mapping to use" and mark as `DONE`
    * 1.2 **Exact matches in Mondo/HP**
        * 1.2.1 Filter "Exact matches" column by fill colour: yellow (#FCE8B2)
        * 1.2.2 Copy the cell contents into "Mapping to use" and mark as `IMPORT`
            * Overwrite any mappings from 1.1, as we prefer more precise mappings even if they must be imported
    * 1.3 **Exact matches in EFO**
        * 1.1.1 Filter "Exact matches" column by fill colour: green (#B7E1CD)
        * 1.1.1 Copy the cell contents into "Mapping to use" and mark as `DONE`
            * Overwrite any mappings from 1.1 and 1.2, as these are our most preferred mappings
2. **Medium-confidence mappings:** These are often good suggested mappings, but must be checked manually.
    * 2.1 **Replacement mappings**
        * 2.1.1 Filter "Previous mapping" column by fill colour: red (#F4C73C)
        * 2.1.2 Determine if the mapping in "Replacement mapping" is suitable, if not find a new term to use as mapping
    * 2.2 **Exact synonym matches**
        * 2.2.1 Remove "Blank" from "Exact synonym matches" column
        * 2.2.2 Determine if the mapping is suitable, if not find a new term to use as mapping
3. **Low-confidence mappings or unmapped terms**
    * 3.1 Set the "Status" column to only include "Blank" entries
    * 3.2 Look for suitable mappings from the "All other mappings" columns, or perform your own searches
      using [OLS](https://www.ebi.ac.uk/ols4/)

## Entering the curation results

### Adding new mappings

To add a new mapping which does not appear in the list of automatically generated mappings, use the following shortened
format: `URL|LABEL||MAPPING_SOURCE`, for example:
`http://purl.obolibrary.org/obo/MONDO_0100460|tobacco addiction, susceptibility to||MONDO_HP_NOT_EFO`.
The match type does not need to be filled in, but make sure to use the right number of pipe separators (`|`) to ensure
it is properly parsed.

### Marking the status of curated terms

The “Status” column has the following acceptable values:

* **DONE** — an acceptable trait contained in EFO has been found for the trait
* **IMPORT** — an acceptable trait has been found from the MONDO/HP ontologies which is not contained in EFO and must be
  imported
* **NEW** — new term must be created in EFO
* **SKIP** — trait is going to be skipped in this iteration, due to being too non-specific, or just having a low
  frequency
* **UNSURE** — temporary status; traits to be discussed with reviewers/the team

### Comment field for curation review

The "Comment" field can be used to enter arbitrary additional information which will be used by reviewers. Precede any
text with initials e.g. "BK - example comment". Comments should be ordered chronologically in reverse: most recent ones
at the top. Any comments will become available in the "Notes" field within the next iteration.
Comments from previous iterations that need to be kept for subsequent ones should be copy/pasted from the "Notes" to
the "Comments" cell.

### Note on multiple mappings

Sometimes the source string contains two or more traits. In this case it is necessary to map that string to two or more
ontology terms to fully represent its content. For example, “Coronary artery disease/myocardial infarction” should be
mapped both to http://www.ebi.ac.uk/efo/EFO_0001645 “Coronary artery disease” and
to http://www.ebi.ac.uk/efo/EFO_0000612 “Myocardial infarction”.

To do this, **duplicate** the row containing the disease string, assign different mappings in each of the rows, and mark
them both with an appropriate status. This will be handled downstream during export and evidence string generation.

This provision does _not_ apply to cases where the source string contains additional semantic context, such as
“susceptibility to...” or “resistance to...”, or drug response terms.

### Note on spaces and line breaks

Sometimes, especially when copy-pasting information from external sources, a mapping label or URL can contain an
additional space symbol (at the beginning or end) or an accidental line break. This causes problems in the downstream
processing and must be manually removed. To minimise the occurrences of this, the Google Sheets template includes a 
validation formula for the first two columns (“URI of selected mapping” and “Label of selected mapping”). If it detects
an extra space symbol or a line break, the cell will be highlighted in red.

## New terms

Once a term has been marked as IMPORT or NEW, it will automatically show up in the corresponding "Add to EFO" worksheet.
Terms for import do not require any additional manual intervention, but new terms require some additional information,
in particular:

* **Parent term** - Suggested parent term within EFO. This is required but does not need to be exact as it will be
  reviewed by EFO maintainers - a rough idea of the term hierarchy is acceptable.
* **Child terms** - Suggested children within EFO (if any), should be added if possible.
* **Description, synonyms, PubMed IDs** - Should be added if possible, for example taken from OMIM or MedGen, but can be
  skipped if the information cannot be found.
* **MedGen, OMIM** - Links to the specified resource, useful references if any of the above cannot be found. These are
  often present in the "Suggested exact mapping" column.

Any additional comments can be left in the final column, they will be passed on to EFO.

Note: It is common that new terms are required to be inserted between a general term and more specific ones. The idea
being that the new term would group a subset of the specific terms but not all of them.
To help with this a script was developed: given a parent CURIE it will search for all the children of that term that
matches specific keyword in their label, description or synonyms.
This is useful for example when looking for all the terms that specifically labeled as "dominant" in a long list of
children terms.

```bash
${PYTHON_BIN} ${CODE_ROOT}/bin/trait_mapping/get_children_with_keywords.py --ontology MONDO --parent_curie MONDO:0100062 --keywords dominant
```

Keep in mind however that EFO is not able to modify imported ontology hierarchies such as MONDO, so suggested child 
terms may not be respected.