import logging
from os import path

import boto3
import botocore.exceptions
from environs import Env

log = logging.getLogger(__name__)
env = Env()


class Bs3client:
    def __init__(self):
        aws_secret = env.str("AWS_SECRET")
        aws_id = env.str("AWS_ID")
        if not (aws_id and aws_secret):
            log.error("Environment variable missing")
            raise KeyError
        self.bucket = boto3.resource(
            service_name="s3",
            region_name="eu-west-3",
            aws_access_key_id=aws_id,
            aws_secret_access_key=aws_secret,
        ).Bucket("video-dl-binaries")

    def download(self, filename, can_fail=False) -> bool:
        try:
            self.bucket.download_file(filename, path.basename(filename))
        except botocore.exceptions.ClientError as e:
            log.error(f"Can't find {filename}")
            if can_fail:
                return False
            raise FileNotFoundError(
                f"File not found. Check the filename and the AWS_ID\n{e}"
                )
        return True

    def upload(self, filename):
        self.bucket.upload_file(
            filename, path.basename(filename), ExtraArgs={"ACL": "public-read"}
        )
