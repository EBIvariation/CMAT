#!/bin/bash
# A script to compare evidence strings. Please see README.md for details on using it.

# A function to sort keys in the evidence strings. This makes them more readable and helps comparison through word diff.
# Also removes several version- and date-related fields which are changed frequently, but do not reflect actual change:
# * validated_aginst_schema_version
# * date_asserted
# The two arguments are input and output JSON files.
sort_keys () {
  ./jq -S "." --tab <"$1" \
    | tr -d '\t\n' \
    | sed -e 's|}{|}~{|g' \
    | tr '~' '\n' \
    | sed -e 's|,"validated_against_schema_version": "[0-9.]*"||g' \
    | sed -e 's|"date_asserted": ".\{19\}"||g' \
  > "$2"
}

# A function to extract all unique identifying fields from the evidence strings. The fields being extracted are:
# * ClinVar RCV accession
# * Phenotype
# * Allele origin
# * Variant ID (rsID or, if absent, RCV accession)
# * Ensembl gene ID
extract_fields () {
  ./jq '
    .unique_association_fields.clinvarAccession + "|" +
    .unique_association_fields.phenotype + "|" +
    .unique_association_fields.alleleOrigin + "|" +
    .unique_association_fields.variant_id + "|" +
    .unique_association_fields.gene
  ' < "$1" | tr -d '"' > "$2"
}

# Computes a word diff between two files using git diff
compute_git_diff () {
  # The --no-index option is important, because otherwise git will refuse to compare the files if you're running this
  # script from right inside the repository (because the files are untracked).
  git diff \
  --minimal \
  -U0 \
  --color=always \
  --word-diff=color \
  --no-index \
  "$1" "$2"
}

echo "Set up environment & parse parameters"
export -f sort_keys extract_fields compute_git_diff
# To ensure that the sort results are consistent, set the sort order locale explicitly
export LC_COLLATE=C
# The realpath is required to make the paths work after the working directory change
OLD_EVIDENCE_STRINGS=$(realpath "$1")
NEW_EVIDENCE_STRINGS=$(realpath "$2")
mkdir comparison && cd comparison || exit 1

echo "Install JQ — a command line JSON processor"
wget -q -O jq https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64
chmod a+x jq

echo "Install aha — HTML report generator"
wget -q https://github.com/theZiz/aha/archive/0.5.zip
unzip -q 0.5.zip && cd aha-0.5 && make &>/dev/null && mv aha ../ && cd .. && rm -rf aha-0.5 0.5.zip

echo "Sort keys and remove schema version from the evidence strings"
sort_keys "${OLD_EVIDENCE_STRINGS}" 01.keys-sorted.old.json \
  & sort_keys "${NEW_EVIDENCE_STRINGS}" 01.keys-sorted.new.json \
  & wait

echo "Extract the unique identifying fields to pair old and new evidence strings together"
extract_fields 01.keys-sorted.old.json 02.fields.old \
  & extract_fields 01.keys-sorted.new.json 02.fields.new \
  & wait

echo "Paste the unique identifying fields & original strings into the same table and sort"
paste 02.fields.old 01.keys-sorted.old.json | sort -k1,1 > 03.fields-and-strings.old \
  & paste 02.fields.new 01.keys-sorted.new.json | sort -k1,1 > 03.fields-and-strings.new \
  & wait

echo "Compute sets of all non-unique identifying fields in each evidence string set"
cut -f1 03.fields-and-strings.old | uniq -c | awk '$1>1 {print $2}' > 04.non-unique-fields.old \
  & cut -f1 03.fields-and-strings.new | uniq -c | awk '$1>1 {print $2}' > 04.non-unique-fields.new \
  & wait
cat 04.non-unique-fields.old 04.non-unique-fields.new | sort -u > 05.all-non-unique-fields

echo "Extract evidence strings with *non-unique* identifying fields into a separate group"
join -j 1 05.all-non-unique-fields 03.fields-and-strings.old > 06.non-unique.old \
  & join -j 1 05.all-non-unique-fields 03.fields-and-strings.new > 06.non-unique.new \
  & wait

echo "Extract evidence strings with *unique* identifying fields into a separate group"
# -v 2 means "print only records from file #2 which cannot be paired"
# If records cannot be paired, it means their identifying fields are *not* in the list of duplicates
join -j 1 -v 2 05.all-non-unique-fields 03.fields-and-strings.old > 07.unique.old \
  & join -j 1 -v 2 05.all-non-unique-fields 03.fields-and-strings.new > 07.unique.new \
  & wait

echo "Separate unique evidence strings into (deleted, common, new)"
join -j 1 07.unique.old 07.unique.new > 08.common \
  & join -j 1 -v 1 07.unique.old 07.unique.new > 08.deleted \
  & join -j 1 -v 2 07.unique.old 07.unique.new > 08.added \
  & wait

echo "Compute diff for evidence strings with non-unique association fields"
compute_git_diff 06.non-unique.old 06.non-unique.new > 09.non-unique-diff

echo "Compute diff for evidence strings with unique association fields"
compute_git_diff 07.unique.old 07.unique.new > 09.unique-diff

# echo "Calculating the advanced statistics" - to be implemented during further iterations
#NON_UNIQUE_EVS_PERCENTAGE_OLD=$(bc -l <<< "scale=2; ${NON_UNIQUE_EVS_OLD} * 100 / ${TOTAL_EVS_OLD}")
#NON_UNIQUE_EVS_PERCENTAGE_NEW=$(bc -l <<< "scale=2; ${NON_UNIQUE_EVS_NEW} * 100 / ${TOTAL_EVS_NEW}")
#export NON_UNIQUE_EVS_PERCENTAGE_OLD NON_UNIQUE_EVS_PERCENTAGE_NEW

echo "Producing the report"

COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_RESET='\033[0m' # No Color
export COLOR_RED COLOR_RESET

cat << EOF > report.html
<html><code>
Compared:

<b>File 1 - ${OLD_EVIDENCE_STRINGS}</b>
Total evidence strings: $(wc -l <03.fields-and-strings.old)
  With non-unique association fields: $(wc -l <06.non-unique.old)
  With unique association fields: $(wc -l <07.unique.old)

<b>File 2 - ${NEW_EVIDENCE_STRINGS}</b>
Total evidence strings: $(wc -l <03.fields-and-strings.new)
  With non-unique association fields: $(wc -l <06.non-unique.new)
  With unique association fields: $(wc -l <07.unique.new)

<b>Statistics for evidence strings with unique association fields</b>
  Deleted: $(wc -l <08.deleted)
  Added: $(wc -l <08.added)
  Present in both files: $(wc -l <08.common)
    Changed: $(awk '$2 != $3' 08.common | wc -l)

See accompanying files for specific diffs:
  <a href="non-unique.html">non-unique.html</a> - diff for evidence strings with non-unique association fields
  <a href="deleted.html">deleted.html</a> - evidence strings which are deleted in file 2 compared to file 1
  <a href="added.html">added.html</a> - evidence strings which are added in file 2 compared to file 1
  <a href="changed.html">changed.html</a> - evidence strings which changed between file 1 and file 2
</code></html>
EOF

(tail -n+5 09.non-unique-diff | awk '{if ($0 !~ /@@/) {print $0 "\n"}}') > 99.non-unique
(echo -e "${COLOR_RED}"; awk '{print $0 "\n"}' 08.deleted; echo -e "${COLOR_RESET}") > 99.deleted
(echo -e "${COLOR_GREEN}"; awk '{print $0 "\n"}' 08.added; echo -e "${COLOR_RESET}") > 99.added
(tail -n+5 09.unique-diff | awk '{if ($0 !~ /@@/) {print $0 "\n"}}') > 99.changed

parallel './aha --word-wrap <99.{} > {}.html' ::: non-unique deleted added changed
rm -rf report.zip
zip report.zip "*.html"

cd ..
