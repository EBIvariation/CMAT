# Filtering functions that can be used in multiple pipelines.

# Identified as problematic submissions, e.g. too many unmappable trait names.
submissions_to_exclude = {
    ('239772', '2024-03-16')  # Submitter ID, Creation date as a proxy for a specific submission
}


def filter_by_submission(clinvar_set):
    """Return False (i.e. filter out) if every submitted record in the set is part of an excluded submission, which we
    identify by submitter ID and SCV creation date."""
    for submitted_record in clinvar_set.scvs:
        if (submitted_record.submitter_id, submitted_record.created_date) not in submissions_to_exclude:
            return True
    return False
