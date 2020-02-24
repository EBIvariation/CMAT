# Comparison of evidence strings

When major updates to the pipeline are implemented, an important measure of control is comparing evidence strings before and after the update for the same input data. This protocol contains commands which help do this.

## Install JQ locally & set up environment
JQ is a command line JSON processor.
```bash
wget -q -O jq https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64
chmod a+x jq
```

To ensure that the sort results are consistent, set the sort order locale directly:
```bash
export LC_COLLATE=C
```

## Sort keys in evidence strings
This makes them more readable and helps comparison through word diff. Set the paths to old and new evidence strings in the environment variables below.
```bash
sort_keys () {
  cat $1 \
    | ./jq -S "." --tab \
    | tr -d '\t\n' \
    | sed -e 's|}{|}~{|g' \
    | tr '~' '\n' \
  > $2
}
export -f sort_keys

OLD_EVIDENCE_STRINGS=...
NEW_EVIDENCE_STRINGS=...
sort_keys ${OLD_EVIDENCE_STRINGS} old.json & sort_keys ${NEW_EVIDENCE_STRINGS} new.json
```

# Extract some fields from the evidence strings
The fields being extracted are:
* ClinVar RCV accession
* Variant ID (rsID or, if absent, RCV accession)
* Functional consequence SO code
```
extract_fields () {
  cat $1 \
  | ./jq '.evidence.variant2disease.provenance_type.database.dbxref.url + ">" + .variant.id + "|" + .evidence.gene2variant.functional_consequence' \
  | tr -d '"' | tr '|' '\t' \
  | sed -e 's|http://purl.obolibrary.org/obo/||g' \
        -e 's|http://identifiers.org/clinvar.record/||g' \
        -e 's|http://identifiers.org/dbsnp/||g' \
        -e 's|http://www.ncbi.nlm.nih.gov/clinvar/||g' \
  > $1.fields
}
export -f extract_fields
extract_fields old.json & extract_fields new.json
```

## Paste fields & original strings into the same document
```bash
paste old.json.fields old.json > old
paste new.json.fields new.json > new
```

## Classify records into (disappeared; new; common)
```bash
cut -f1 old.json.fields | sort -u > old.variants
cut -f1 new.json.fields | sort -u > new.variants
comm -23 old.variants new.variants > 1_deleted
comm -13 old.variants new.variants > 2_added
comm -12 old.variants new.variants > 3_common
```

## Find common variants where functional mappings have changed
```bash
cut -f1-2 old.json.fields | sort -u > old.consequences
cut -f1-2 new.json.fields | sort -u > new.consequences
join 3_common old.consequences -j 1 | join /dev/stdin new.consequences -j1 | awk '$2 != $3' > 3_common_changed
```

## Compare the fields
```bash
sort -u old > old.sorted & sort -u new > new.sorted
git diff --minimal -U0 --color=always --word-diff=color old.sorted new.sorted
```

## Future improvements
There is a [json-diff](https://pypi.org/project/json-diff/) module which allows detailed comparison of JSON objects. If this protocol is going to be updated in the future, this module might be helpful. It provides structured overview of differences; however, it has a few limitations:
 * It can only compare individual evidence strings (so they must be sorted and matched beforehand)
 * When a field's value is updated, `json-diff` only reports the new value of the field, but not the old one, for example:
```json
{
    "_update": {
        "evidence": {
            "_update": {
                "gene2variant": {
                    "_update": {
                        "functional_consequence": "http://purl.obolibrary.org/obo/SO_0001575"
                    }
                }
            }
        }
    }
}
```

Here, the change was from SO_0001589 to SO_0001575, but only the second value is reported.