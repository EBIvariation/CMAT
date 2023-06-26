# Manual curation, part II, biological: perform manual curation

The goals of the manual curation:
* All traits which are linked to NT expansion (nucleotide repeat expansion) variants must be curated. Those are marked as "NT expansion" in the “Notes” column.
* All traits with occurrence ≥ **10** must be curated. Additionally, if there are less than **200** such terms, then the top 200 terms must be curated.
* _Suggested previous mapping_ traits should be checked for any terms that have become obsolete since the last iteration. These will be colored red and likely have a _suggested replacement mapping_ provided in the appropriate column. If no replacement is provided, curate as usual.
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

* 1\. **Suggested exact EFO mappings.** These are terms we can use confidently as they match the term to map perfectly and already reside in EFO. Filter options as follows:
  * 1.1. Remove "Blank" from *Suggested exact mapping* column 
  * 1.2. Filter by colour: Fill colour #B7E1CD
  * 1.3. Use these mappings and mark as DONE
* 2\. **Suggested previous mappings.** All of these are the decisions that we made in the past, so we trust them unless they have been made obsolete. In this case there will be a suggested replacement, or we can find an entirely new mapping. Filter options as follows:
  * 2.1. Remove "Blank" from *Suggested previous mapping* column
  * 2.2. Filter by colour: Fill colour light red 3
  * 2.3. Determine if *Suggested replacement mapping* is suitable, if not find a new term to use as mapping
  * 2.4. Remove Fill colour light red 3 filter and check all other *Suggested previous mapping* using the following ruleset:
    * 2.4.1. **The previously assigned mapping is in EFO and is exact.** Mark as finished immediately. (It's extremely unlikely that a better mapping could be found).
    * 2.4.2. **The previously assigned mapping is in EFO and IS NOT exact.** Review the mappings to see if a better (more accurate/specific, non-obsolete) mapping is available. Then mark as finished.
    * 2.4.3. **The previously assigned mapping is not contained in EFO and is not exact.** We need to either find a mapping which is already in EFO, or import these terms into EFO.
    * 2.4.4. **The previously used mapping IS NOT contained in EFO and is exact.** These are good candidates to mark as finished and them import in EFO afterwards.
    * 2.4.5. **The previously assigned mapping IS NOT contained in EFO and IS NOT exact.** Similarly to 2.4.3, attempt to find an acceptable EFO mapping; if not found, use any acceptable mapping (with subsequent import to EFO).
* 3\. **Mapping blank ontology terms** Once the options from the suggested exact & previous mappings is complete, we can begin the process of finding mappings for "blank" terms. Filter options as follows:
  * 3.1. Set the Status column to only include "blank" entries
  * 3.2. Search for suitable mappings using OLS - https://www.ebi.ac.uk/ols4/

### Time-saving options
The new manual workflow can be shortened if necessary, while the quality of the results will be _at least as good as for the old workflow_ (because we're reusing the results of previous curations):
* Complete steps from 1.\*
* All subsections 2.\* involve review of mappings previously selected by ourselves. Because we trust them (to an extent), this review can be applied not to all mappings, but only to some (selected on a basis of frequency, or just randomly sampled/eyeballed).

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
