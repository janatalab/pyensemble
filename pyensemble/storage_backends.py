# storage_backends.py

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


if settings.USE_AWS_STORAGE:
    try:
        from storages.backends.s3boto3 import S3Boto3Storage
    except ModuleNotFoundError as error:
        raise ImproperlyConfigured(
            'AWS storage is enabled, but its dependencies are not installed. '
            'Install them with "pip install -r requirements-aws.txt".',
        ) from error

    class S3MediaStorage(S3Boto3Storage):
        bucket_name = settings.AWS_MEDIA_STORAGE_BUCKET_NAME
        location = f"{settings.INSTANCE_LABEL}/"
        file_overwrite = True

    class S3DataStorage(S3Boto3Storage):
        bucket_name = settings.AWS_DATA_STORAGE_BUCKET_NAME
        location = f"{settings.INSTANCE_LABEL}/"
        file_overwrite = True
else:
    class _UnavailableS3Storage:
        def __init__(self, *args, **kwargs):
            raise ImproperlyConfigured(
                'This S3 storage backend is unavailable because '
                'USE_AWS_STORAGE is False.',
            )

    class S3MediaStorage(_UnavailableS3Storage):
        pass

    class S3DataStorage(_UnavailableS3Storage):
        pass


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
