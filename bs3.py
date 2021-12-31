import boto3
import botocore.exceptions
import logging

from os import environ as env, path

log = logging.getLogger(__name__)


class Bs3client:
    def __init__(self, aws_skey=None, aws_id=None):
        try:
            self.bucket = boto3.resource(
                service_name='s3',
                aws_secret_access_key=env["AWS_SECRET"] if not aws_skey else aws_skey,
                aws_access_key_id=env["AWS_ID"] if not aws_id else aws_id,
                region_name="eu-west-3"
            ).Bucket("video-dl-windows-builds")
        except KeyError as e:
            print(f"Environment variable missing {e}")
            raise KeyError

    def download(self, filename, can_fail=False) -> bool:
        try:
            self.bucket.download_file(filename, path.basename(filename))
        except botocore.exceptions.ClientError:
            log.info(f"Can't find {filename}")
            if can_fail:
                return False
            raise FileNotFoundError
        return True

    def upload(self, filename):
        self.bucket.upload_file(filename, path.basename(filename))