#!/bin/bash
# A script to compare evidence strings. Please see README.md for details on using it.



########################################################################################################################
echo "Defining functions"

# A function to sort keys in the evidence strings. This makes them more readable and helps comparison through word diff.
# The two arguments are input and output JSON files.
sort_keys () {
  jq -c -S "." <"$1" > "$2"
}

# A function to extract all unique identifying fields from the evidence strings. The fields being extracted are:
# * ClinVar RCV accession
# * Variant ID (chr_pos_ref_alt or, if absent, RCV accession)
# * Phenotype (mapped ID or, if absent, disease from source)
# * Datatype ID
# * Functional consequence ID
# * Ensembl gene ID
extract_fields () {
  jq '
    .studyId + "|" +
    .variantId + "|" +
    (if .diseaseFromSourceMappedId? then .diseaseFromSourceMappedId else .diseaseFromSource | ascii_downcase end) + "|" +
    .datatypeId + "|" +
    .variantFunctionalConsequenceId + "|" +
    .targetFromSourceId
  ' < "$1" | tr -d '"' > "$2"
}

# Takes file $1 of pipe-delimited fields, splits index $2 into a separate tab-separated column, then sorts the output
split_and_sort () {
  awk -v c="$2" '
    BEGIN{FS="|"; OFS="|"} function mvcol(col) { tmp=$col; for (i=col; i<NF; i++) {$i = $(i+1)}  NF-- } { mvcol(c); print $0"\t"tmp }
  ' $1 | sort -k1,1
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
  --text \
  "$1" "$2"
}

export -f sort_keys extract_fields split_and_sort compute_git_diff



########################################################################################################################
echo "Preparation"

echo "  Set up environment and parse parameters"
# To ensure that the sort results are consistent, set the sort order locale explicitly
export LC_COLLATE=C
# The realpath is required to make the paths work after the working directory change
OLD_EVIDENCE_STRINGS=$(realpath "$1")
NEW_EVIDENCE_STRINGS=$(realpath "$2")
mkdir comparison && cd comparison || exit 1



########################################################################################################################
echo "Preprocess evidence strings"

echo "  Sort keys and remove non-informative fields"
sort_keys "${OLD_EVIDENCE_STRINGS}" 01.keys-sorted.old.json \
  & sort_keys "${NEW_EVIDENCE_STRINGS}" 01.keys-sorted.new.json \
  & wait

echo "  Extract the unique association fields to pair old and new evidence strings together"
extract_fields 01.keys-sorted.old.json 02.fields.old \
  & extract_fields 01.keys-sorted.new.json 02.fields.new \
  & wait

echo "  Paste the unique association fields & original strings into the same table and sort"
paste 02.fields.old 01.keys-sorted.old.json | sort -k1,1 > 03.fields-and-strings.old \
  & paste 02.fields.new 01.keys-sorted.new.json | sort -k1,1 > 03.fields-and-strings.new \
  & wait



########################################################################################################################
echo "Separate evidence strings into categories based on uniqueness of association fields and presence in files 1 and 2"

echo "  Compute sets of all non-unique association fields in each evidence string set"
cut -f1 03.fields-and-strings.old | uniq -c | awk '$1>1 {print $2}' > 04.non-unique-fields.old \
  & cut -f1 03.fields-and-strings.new | uniq -c | awk '$1>1 {print $2}' > 04.non-unique-fields.new \
  & wait
cat 04.non-unique-fields.old 04.non-unique-fields.new | sort -u > 05.all-non-unique-fields

echo "  Extract evidence strings with *non-unique* association fields into a separate group"
join -t$'\t' -j 1 05.all-non-unique-fields 03.fields-and-strings.old > 06.non-unique.old \
  & join -t$'\t' -j 1 05.all-non-unique-fields 03.fields-and-strings.new > 06.non-unique.new \
  & wait

echo "  Extract evidence strings with *unique* association fields into a separate group"
# -v 2 means "print only records from file #2 which cannot be paired"
# If records cannot be paired, it means their association fields are *not* in the list of duplicates
join -t$'\t' -j 1 -v 2 05.all-non-unique-fields 03.fields-and-strings.old > 07.unique.old \
  & join -t$'\t' -j 1 -v 2 05.all-non-unique-fields 03.fields-and-strings.new > 07.unique.new \
  & wait

echo "  Separate unique evidence strings into (deleted, common, new)"
join -t$'\t' -j 1 07.unique.old 07.unique.new > 08.common \
  & join -t$'\t' -j 1 -v 1 07.unique.old 07.unique.new > 08.deleted \
  & join -t$'\t' -j 1 -v 2 07.unique.old 07.unique.new > 08.added \
  & wait



########################################################################################################################
echo "Compute differences for certain classes of evidence strings"

echo "  Diff for evidence strings with *non-unique* association fields"
compute_git_diff 06.non-unique.old 06.non-unique.new > 09.non-unique-diff

echo "  Diff for evidence strings with *unique* association fields"
cut -f2 08.common > 10.common.old & cut -f3 08.common > 10.common.new & wait
compute_git_diff 10.common.old 10.common.new > 09.unique-diff



########################################################################################################################
echo "Identify evidence strings with changes in phenotype, datatype, or consequence type"

split_and_sort 02.fields.old 3 > 03a.phenotype.old
split_and_sort 02.fields.new 3 > 03a.phenotype.new

split_and_sort 02.fields.old 4 > 03a.datatype.old
split_and_sort 02.fields.new 4 > 03a.datatype.new

split_and_sort 02.fields.old 5 > 03a.consequence.old
split_and_sort 02.fields.new 5 > 03a.consequence.new


for field in phenotype datatype consequence
do
    cut -f1 03a.${field}.old | uniq -c | awk '$1>1 {print $2}' > 04a.non-unique-fields.old \
	& cut -f1 03a.${field}.new | uniq -c | awk '$1>1 {print $2}' > 04a.non-unique-fields.new \
	& wait
    cat 04a.non-unique-fields.old 04a.non-unique-fields.new | sort -u > 05a.all-non-unique-fields

    join -t$'\t' -j 1 -v 2 05a.all-non-unique-fields 03a.${field}.old > 07a.unique.old \
	& join -t$'\t' -j 1 -v 2 05a.all-non-unique-fields 03a.${field}.new > 07a.unique.new \
	& wait

    join -t$'\t' -j 1 07a.unique.old 07a.unique.new | awk -F$'\t' '$2 != $3' > 08a.common
    cut -f1,2 08a.common > 10a.common.old & cut -f1,3 08a.common > 10a.common.new & wait
    compute_git_diff 10a.common.old 10a.common.new > 09a.unique-diff-${field}
done


########################################################################################################################
echo "Produce the report"

COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_RESET='\033[0m' # No Color
export COLOR_RED COLOR_GREEN COLOR_RESET

cat << EOF > report.html
<html>
<style type="text/css">
  code { white-space: pre; }
</style>
<code><b><big>Evidence string comparison report</big></b>

<b>File 1</b> - ${OLD_EVIDENCE_STRINGS}
Total evidence strings: <b>$(wc -l <03.fields-and-strings.old)</b>
  Of them, with non-unique association fields: <b>$(wc -l <06.non-unique.old)</b>
  Of them, with unique association fields: <b>$(wc -l <07.unique.old)</b>

<b>File 2</b> - ${NEW_EVIDENCE_STRINGS}
Total evidence strings: <b>$(wc -l <03.fields-and-strings.new)</b>
  Of them, with non-unique association fields: <b>$(wc -l <06.non-unique.new)</b>
  Of them, with unique association fields: <b>$(wc -l <07.unique.new)</b>

<b>Evidence strings with non-unique association fields</b>
It is not easily possible to establish one-to-one relationships for these strings.
Hence, detailed analysis of changes for them is impossible.
However, you can see <a href="non-unique.html">the full diff only for those evidence strings</a>.

<b>Statistics for evidence strings with unique association fields</b>
Deleted: <b><a href="deleted.html">$(wc -l <08.deleted)</a></b>
Added: <b><a href="added.html">$(wc -l <08.added)</a></b>
  Of these, those with identifiable changes in unique association fields:
    <a href="phenotype-changed.html">Phenotype changed</a>
    <a href="datatype-changed.html">Datatype changed</a>
    <a href="consequence-changed.html">Consequence changed</a>

Present in both files: <b>$(wc -l <08.common)</b>
  Of them, changed: <b><a href="changed.html">$(awk -F$'\t' '$2 != $3' 08.common | wc -l)</a></b>

</code></html>
EOF

(tail -n+5 09.non-unique-diff | awk '{if ($0 !~ /@@/) {print $0 "\n"}}') > 99.non-unique
(echo -e "${COLOR_RED}"; awk '{print $0 "\n"}' 08.deleted; echo -e "${COLOR_RESET}") > 99.deleted
(echo -e "${COLOR_GREEN}"; awk '{print $0 "\n"}' 08.added; echo -e "${COLOR_RESET}") > 99.added
(tail -n+5 09.unique-diff | awk '{if ($0 !~ /@@/) {print $0 "\n"}}') > 99.changed
(tail -n+5 09a.unique-diff-phenotype | awk '{if ($0 !~ /@@/) {print $0 "\n"}}') > 99.phenotype-changed
(tail -n+5 09a.unique-diff-datatype | awk '{if ($0 !~ /@@/) {print $0 "\n"}}') > 99.datatype-changed
(tail -n+5 09a.unique-diff-consequence | awk '{if ($0 !~ /@@/) {print $0 "\n"}}') > 99.consequence-changed

parallel 'aha --word-wrap --title "{}" <99.{} > {}.html' ::: non-unique deleted added changed phenotype-changed datatype-changed consequence-changed
rm -rf report.zip
zip report.zip ./*.html

cd ..

echo "All done"
