# Manual curation, part II, biological: perform manual curation

The goals of the manual curation:
* All traits which are linked to NT expansion (nucleotide repeat expansion) variants must be curated. Those are marked as "NT expansion" in the “Notes” column.
* All traits with occurrence ≥ **10** must be curated. Additionally, if there are less than **200** such terms, then the top 200 terms must be curated.
* _Suggested previous mapping_ traits should be checked for any terms that have become obsolete since the last iteration. These will be colored red and likely have a _suggested replacement mapping_ provided in the appropriate column. If no replacement is provided, curate as usual.
* For the rest of the traits, we curate as many as possible.

Good mappings must be eyeballed to ensure they are actually good. Alternative mappings for medium or low quality mappings can be searched for using OLS. If a mapping can't be found in EFO, look for a mapping to a HP, ORDO, or MONDO trait name. Most HP/MONDO terms will also be in EFO but some are not.

## Criteria to manually evaluate mapping quality
* Exact string for string matches are _good_
* Slight modifications are _good_ e.g. IRAK4 DEFICIENCY → Immunodeficiency due to interleukin-1 receptor-associated kinase-4 deficiency
* Subtype to parent are _good_ e.g ACHROMATOPSIA 3 → Achromatopsia, but **only if** there is not already a non-EFO exact string match for the subtype. If there is one, it should be prioritized and then term set as _IMPORT_
* Parent to subtype are _bad_ e.g. HEMOCHROMATOSIS → Hemochromatosis type 3
* Familial / congenital represented on only one half are _bad_ e.g. Familial renal glycosuria → Renal glycosuria
* Susceptibility on only one half is _bad_ e.g Alcohol dependence, susceptibility to → alcohol dependence
* Early / late onset on only one half is _bad_ e.g. Alzheimer disease, early-onset → Alzheimer's disease

In general, complex traits with modifiers (e.g. "autosomal recessive", "early onset", or "history of") should not be mapped to the more general term (i.e. without modifiers) because it loses important information. For now the curator should follow the same protocol as for any other term and request to import/create a new term containing the necessary modifiers.

## Unmapped trait names
Trait names that haven't been automatically mapped against any ontology term can also be searched for using OLS.
If a mapping can't be found in EFO, look for a mapping to a HP, ORDO, or MONDO trait name.
HP and MONDO terms can be imported into EFO if not present.
ORDO terms cannot be directly imported but can be used as the basis for new EFO terms.

## Curation workflow
Curation should be done by subsequently applying filters to appropriate columns, then making decisions for the traits in the filtered selection.

* 1\. **Suggested exact EFO mappings.** These are terms we can use confidently as they match the term to map perfectly and already reside in EFO. Filter options as follows:
  * 1.1. Remove "Blank" from *Suggested exact mapping* column 
  * 1.2. Filter by colour: Fill colour #B7E1CD
  * 1.3. Copy the cell contents into "Mapping to use" and mark as DONE
* 2\. **Suggested previous mappings.** All of these are the decisions that we made in the past, so we trust them unless they have been made obsolete. In this case there will be a suggested replacement, or we can find an entirely new mapping. Filter options as follows:
  * 2.1 **The previously assigned mapping is using a term that has now been made OBSOLETE.** these can be highlighted and a new term found using the following ruleset:
    * 2.1.1. Remove "Blank" from *Suggested previous mapping* column
    * 2.1.2. Filter by colour: Fill colour light red 3 - this highlights terms where the previously used mapping has been made *OBSOLETE*
    * 2.1.3. Determine if *Suggested replacement mapping* is suitable, if not find a new term to use as mapping
  * 2.2. Remove Fill colour light red 3 filter and check all other *Suggested previous mapping* using the following ruleset:
    * 2.2.1. **The previously assigned mapping is in EFO and is exact.** Mark as finished immediately. (It's extremely unlikely that a better mapping could be found).
    * 2.2.2. **The previously assigned mapping is in EFO and IS NOT exact.** Review the mappings by filtering the "Suggested exact mapping" for text containing MONDO_ or HP_ and compare the label to see if the exact mapping is more precise. If so, copy the label for the exact mapping and set for IMPORT
    * 2.2.3. **The previously assigned mapping is not contained in EFO and IS NOT exact.** We need to either find a mapping which is already in EFO, or import these terms into EFO.
    * 2.2.4. **The previously assigned mapping is not contained in EFO and is exact.** These are good candidates to mark as finished and them import in EFO afterwards.
* 3\. **Mapping blank ontology terms** Once the options from the suggested exact & previous mappings is complete, we can begin the process of finding mappings for "blank" terms. Filter options as follows:
  * 3.1. Set the Status column to only include "blank" entries
  * 3.2. Search for suitable mappings using OLS - https://www.ebi.ac.uk/ols4/

The curator can also leverage any additional mappings provided, which have the format `URL|LABEL|ZOOMA_QUALITY|ZOOMA_SOURCE|EFO_STATUS`.
* `ZOOMA_QUALITY` indicates the confidence returned by Zooma (high/medium/low), or "not specified" if the term originates from outside Zooma.
* `ZOOMA_SOURCE` indicates the datasource of the mapping in Zooma (e.g. EVA or ClinVar Xrefs, or a specific ontology), or can indicate the source is a previously-used or replacement mapping.
* `EFO_STATUS` indicates whether the term is current, obsolete, or not present in EFO.

### Time-saving options
The manual workflow can be shortened if necessary, while the quality of the results will be _at least as good as for the old workflow_ (because we're reusing the results of previous curations):
* Complete all Step 1 instances from the Curation workflow
* All subsections of Step 2 - they involve review of mappings previously selected by ourselves. The only changes will be those where the previously mapped term has now become obsolete, however a new mapping can be found during step 2.1

## Entering the curation results

### Adding new mappings
The general full format of a mapping is `URL|LABEL|ZOOMA_QUALITY|ZOOMA_SOURCE|EFO_STATUS`.

To add a new mapping which does not appear in the list of automatically generated mappings, use the following shortened format: `URL|LABEL|||EFO_STATUS`, for example: `http://www.ebi.ac.uk/efo/EFO_0006329|response to citalopram|||EFO_CURRENT`. The last value can be either `EFO_CURRENT` (trait is present in the latest EFO version available in OLS), or `NOT_CONTAINED` if the term is not contained in the EFO.

Make sure **not** to use a mixed format, `URL|LABEL|ZOOMA_QUALITY|ZOOMA_SOURCE|||EFO_STATUS`, as it would not be properly processed by the spreadsheet.

### Marking the status of curated terms
The “Status” column has the following acceptable values:
* **DONE** — an acceptable trait contained in EFO has been found for the trait
* **IMPORT** — an acceptable trait has been found from the MONDO/HP ontologies which is not contained in EFO and must be imported
* **NEW** — new term must be created in EFO
* **SKIP** — trait is going to be skipped in this iteration, due to being too non-specific, or just having a low frequency
* **UNSURE** — temporary status; traits to be discussed with reviewers/the team

### Comment field for curation review
The "Comment" field can be used to enter arbitrary additional information which will be used by reviewers. Precede any text with initials e.g. "BK - example comment". Comments should be ordered chronologically in reverse: most recent ones at the top.
Any comments will become available in the Notes field within the next iteration.
Comments from previous iteration that needs to be kept for subsequent ones  should be copy/pasted from the Notes to the Comments cell. 

### Note on multiple mappings
Sometimes the source string contains two or more traits. In this case it is necessary to map that string to two or more ontology terms to fully represent its content. For example, “Coronary artery disease/myocardial infarction” should be mapped both to http://www.ebi.ac.uk/efo/EFO_0001645 “Coronary artery disease” and to http://www.ebi.ac.uk/efo/EFO_0000612 “Myocardial infarction”.

To do this, **duplicate** the row containing the disease string, assign different mappings in each of the rows, and mark them both with an appropriate status. This will be handled downstream during export and evidence string generation.

This provision does _not_ apply to cases where the source string contains additional semantic context, such as “susceptibility to...”, “resistance to...”, or drug response terms.

### Note on spaces and line breaks
Sometimes, especially when copy-pasting information from external sources, a mapping label or URL can contain an additional space symbol (at the beginning or end) or an accidental line break. This causes problems in the downstream processing and must be manually removed. To minimise the occurences of this, Google Sheets template includes a validation formula for the first two columns (“URI of selected mapping” and “Label of selected mapping”). If it detects an extra space symbol or a line break, the cell will be highlighted in red.

## New terms
Once a term has been marked as IMPORT or NEW, it will automatically show up in the corresponding "Add to EFO" worksheet.
Terms for import do not require any additional manual intervention, but new terms require some additional information, in particular:
* **Parent term** - Suggested parent term within EFO. This is required but does not need to be exact as it will be reviewed by EFO maintainers - a rough idea of the term hierarchy is acceptable.
* **Child terms** - Suggested children within EFO (if any), should be added if possible.
* **Description, synonyms, PubMed IDs** - Should be added if possible, for example taken from OMIM or MedGen, but can be skipped if the information cannot be found.
* **MedGen, OMIM** - Links to the specified resource, useful references if any of the above cannot be found. These are often present in the "Suggested exact mapping" column.

Any additional comments can be left in the final column, they will be passed on to EFO.

Note: It is common that new terms are required to be inserted between a general term and more specific ones. The idea being that the new term would group a subset of the specific terms but not all of them.
To help with this a script was developed: given a parent CURIE it will search for all the children of that term that matches specific keyword in their label, description or synonyms. 
This is useful for exampl when looking for all the terms that specifically labeled as "dominant" in a long list of children terms.

```bash
${PYTHON_BIN} ${CODE_ROOT}/bin/trait_mapping/get_children_with_keywords.py --ontology MONDO  --parent_curie MONDO:0100062 --keywords dominant
```