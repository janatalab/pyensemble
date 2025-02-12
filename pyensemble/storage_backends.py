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


def use_media_storage():
    if settings.USE_AWS_STORAGE:
        storage = S3MediaStorage
    else:
        storage = settings.DEFAULT_FILE_STORAGE

    return storage


def use_data_storage():
    if settings.USE_AWS_STORAGE:
        storage = S3DataStorage
    else:
        storage = settings.DEFAULT_FILE_STORAGE

    return storage
