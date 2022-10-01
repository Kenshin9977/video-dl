import logging
from os import path, stat

import boto3
import botocore.exceptions
from environs import Env

log = logging.getLogger()
env = Env()


class Bs3client:
    def __init__(self):
        self.total = 0
        self.uploaded = 0
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

    def progress_callback(self, size):
        if self.total == 0:
            return
        self.uploaded += size
        percent_progress = int(self.uploaded / self.total * 100)
        print(f"{percent_progress}%", end="\r")

    def download(self, filename, can_fail=False) -> bool:
        try:
            self.bucket.download_file(
                filename,
                path.basename(filename),
                Callback=self.progress_callback,
            )
            print()
        except botocore.exceptions.ClientError as e:
            log.error(f"Can't find {filename}")
            if can_fail:
                return False
            raise FileNotFoundError(
                f"File not found. Check the filename and the AWS_ID\n{e}"
            )
        return True

    def upload(self, filename):
        self.uploaded = 0
        self.total = stat(filename).st_size
        self.bucket.upload_file(
            filename,
            path.basename(filename),
            ExtraArgs={"ACL": "public-read"},
            Callback=self.progress_callback,
        )
        print()
