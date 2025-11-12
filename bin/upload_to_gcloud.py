#!/usr/bin/env python3

import argparse
import logging
import os
from datetime import datetime

from google.cloud import storage


logger = logging.getLogger(__package__)


def upload_evidence_to_gcloud_bucket(source_file_name, destination_folder):
    """Uploads source_file_name to destination_folder in the Google Cloud Storage bucket.
    File will be renamed to cttv012-[yyyy]-[mm]-[dd].json.gz"""
    if 'OT_BUCKET_NAME' not in os.environ or 'OT_CREDS_FILE' not in os.environ:
        logger.error('Environment variables OT_BUCKET_NAME and OT_CREDS_FILE must be set')
        return
    bucket_name = os.environ['OT_BUCKET_NAME']
    creds_json_file = os.environ['OT_CREDS_FILE']

    date_string = datetime.today().strftime('%Y-%m-%d')
    destination_blob_name = f'{destination_folder}/cttv012-{date_string}.json.gz'

    storage_client = storage.Client.from_service_account_json(creds_json_file)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    logger.info(f'File {source_file_name} uploaded to gs://{bucket_name}/{destination_blob_name}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Upload file to Open Targets Google Cloud Storage')
    parser.add_argument('--input-file', required=True, help='File to upload')
    parser.add_argument('--destination-folder', required=True, help='Destination folder within bucket')
    args = parser.parse_args()
    upload_evidence_to_gcloud_bucket(args.input_file, args.destination_folder)
