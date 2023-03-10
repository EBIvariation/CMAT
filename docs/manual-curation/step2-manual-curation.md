# Manual curation, part II, biological: perform manual curation

The goals of the manual curation:
* All traits which are linked to NT expansion (nucleotide repeat expansion) variants must be curated. Those are marked as "NT expansion" in the “Notes” column.
* All traits with occurrence ≥ **10** must be curated. Additionally, if there are less than **200** such terms, then the top 200 terms must be curated.
* _Suggested previous mapping_ traits should be checked for any terms that have become obsolete since the last iteration. This can be done by filtering then searching for the string EFO\_OBSOLETE
* For the rest of the traits, we curate as many as possible.

Good mappings must be eyeballed to ensure they are actually good. Alternative mappings for medium or low quality mappings can be searched for using OLS. If a mapping can't be found in EFO, look for a mapping to a HP, ORDO, or MONDO trait name. Most HP/ORDO/MONDO terms will also be in EFO but some are not. These can be imported to EFO using the Webulous submission service.

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
Trait names that haven't been automatically mapped against any ontology term can also be searched for using OLS. If a mapping can't be found in EFO, look for a mapping to a HP, ORDO, or MONDO trait name. If these are not already in EFO they should be imported to EFO using the Webulous submission service.

## Curation workflow
Curation should be done by subsequently applying filters to appropriate columns, then making decisions for the traits in the filtered selection.

* 1\. **There is a previously assigned mapping for this trait.** All of these are the decisions that we made in the past, so we trust them (to an extent). Copy and paste previously used mappings into “Mapping to use”. Then review them according to the following steps.
  * 1.1. **The previously assigned mapping is in EFO**
    * 1.1.1. **The previously assigned mapping is in EFO and is exact.** Mark as finished immediately. (It's extremely unlikely that a better mapping could be found).
    * 1.1.2. **The previously assigned mapping is in EFO and IS NOT exact.** Review the mappings to see if a better (more accurate/specific) mapping is available. Then mark as finished.
  * 1.2. **The previously assigned mapping is not contained in EFO.** We need to either find a mapping which is already in EFO, or import these terms into EFO.
    * 1.2.1. **The previously used mapping IS NOT contained in EFO and is exact.** These are good candidates to mark as finished and them import in EFO afterwards. However, quickly check whether there are non-exact matches which are already in EFO are are as good as exact mappings.
      * E. g. if the exact mapping is “erythrocytosis 6, familial” and not in EFO, but there is an inexact mapping “familial erythrocytosis 6” which *is* in EFO, we should use the inexact mapping.
      * If a trait does not have any EFO mappings, it's probably safe to mark it as finished (with subsequent import to EFO).
    * 1.2.2. **The previously assigned mapping IS NOT contained in EFO and IS NOT exact.** Similarly to 1.2.1, attempt to find an acceptable EFO mapping; if not found, use any acceptable mapping (with subsequent import to EFO).
* 2\. **There is no previously assigned mappings for the trait, but exact mappings are available.** Because letter-to-letter matches are extremely likely to be correct, we can use them after eyeballing for correctness.
  * 2.1. **The exact mapping in the EFO.** Mark as finished immediately.
  * 2.2. **The exact mapping IS NOT in the EFO.** Similarly to 1.2.1, attempt to find an acceptable EFO mapping; if not found, use any acceptable mapping (with subsequent import to EFO).
* 3\. **There are no previously used or exact mappings for the trait.** Curate manually as usual.

### Time-saving options
The new manual workflow can be shortened if necessary, while the quality of the results will be _at least as good as for the old workflow_ (because we're reusing the results of previous curations):
* All subsections 1.\* involve review of mappings previously selected by ourselves. Because we trust them (to an extent), this review can be applied not to all mappings, but only to some (selected on a basis of frequency, or just randomly sampled/eyeballed).
* If necessary, section 1 can be skipped completely, i. e. copy-paste previous mappings into “Mapping to use” column, but skip the review.
* Sections 2.2 and 3 can only be applied to some variants (e. g. based on frequency), depending on the time available.

## Entering the curation results

### Adding new mappings
The general full format of a mapping is `URL|LABEL|ZOOMA_QUALITY|ZOOMA_SOURCE|EFO_STATUS`.

To add a new mapping which does not appear in the list of automatically generated mappings, use the following shortened format: `URL|LABEL|||EFO_STATUS`, for example: `http://www.ebi.ac.uk/efo/EFO_0006329|response to citalopram|||EFO_CURRENT`. The last value can be either `EFO_CURRENT` (trait is present in the latest EFO version available in OLS), or `NOT_CONTAINED` if the term is not contained in the EFO.

Make sure **not** to use a mixed format, `URL|LABEL|ZOOMA_QUALITY|ZOOMA_SOURCE|||EFO_STATUS`, as it would not be properly processed by the spreadsheet.

### Marking the status of curated terms
The “Status” column has the following acceptable values:
* **DONE** — an acceptable trait contained in EFO has been found for the trait
* **IMPORT** — an acceptable trait has been found from the MONDO/ORDO/HP ontologies which is not contained in EFO and must be imported
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
