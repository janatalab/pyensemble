# storage_backends.py

from django.conf import settings

from storages.backends.s3boto3 import S3Boto3Storage

class S3MediaStorage(S3Boto3Storage):
    bucket_name = settings.AWS_MEDIA_STORAGE_BUCKET_NAME
    location = f"{settings.INSTANCE_LABEL}/"
    file_overwrite = True


class S3DataStorage(S3Boto3Storage):
    bucket_name = settings.AWS_DATA_STORAGE_BUCKET_NAME
    location = f"{settings.INSTANCE_LABEL}/"
    file_overwrite = True