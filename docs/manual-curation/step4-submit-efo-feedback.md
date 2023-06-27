# Manual curation, part IV, biological: submit feedback to EFO

## IMPORT terms
The partially ready table for EFO import is available in the "Add EFO disease" sheet in the curation spreadsheet. The table needs to be amended manually:
* In some cases, terms will lack descriptions/parent terms/synonyms, because ontologies don't always contain these fields for a particular term. If possible, they should be added for all traits. They can be found by querying OLS using a cross reference entry (usually MONDO). A description for a term can also be found by using the terms "Description" from OMIM.

Open a new git issue with EFO to review and import these novel trait names, e.g. [https://github.com/EBISPOT/efo/issues/223](https://github.com/EBISPOT/efo/issues/223).

## NEW terms
Terms which don't have a suitable mapping cannot be added to the “Add EFO disease“ sheet and must be specified manually in PR description.
