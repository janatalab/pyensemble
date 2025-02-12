# aws.py
import os

from django.conf import settings

from pyensemble.models import Stimulus
from pyensemble.group.models import GroupSessionFile

from pyensemble.storage_backends import S3MediaStorage, S3DataStorage

import pdb

'''
Define a method that we can use to copy locally stored media and data files
to an appropriate AWS S3 bucket so that they can then be accessed using
our custom S3 storage backends, S3MediaStorage, and S3DataStorage.

queryset should either be Stimulus or GroupSessionFile objects
'''

def copy_local_to_S3_bucket(queryset, local_file_root = settings.MEDIA_ROOT):
    # Perform some integrity checks to make sure that this operation can succeed
    filetype = queryset.model._meta.model_name

    # Make sure that the class of the QuerySet is valid
    if filetype not in ['groupsessionfile', 'stimulus']:
        raise ValueError(f'No handling of {filetype} querysets')

    # Determine our local file root (assume it is in MEDIA_ROOT)
    if not os.path.exists(local_file_root):
        raise ValueError(f'Path to local files not present: {local_file_root}')

    # Get ourselves an S3 storage object
    if filetype == 'stimulus':
        s3 = S3MediaStorage()
    elif filetype == 'groupsessionfile':
        s3 = S3DataStorage()

    for instance in queryset:
        # Get the originating database file
        if filetype == 'stimulus':
            file = instance.location
            name = instance.name

        elif filetype == 'groupsessionfile':
            file = instance.file
            name = instance.groupsession.id

        # Verify that we have a file
        if not file:
            print(f'WARNING: No file available for {filetype} {name}')
            continue

        # Get the local file name
        if file.name.startswith(os.path.sep):
            clean_name = file.name[1:]
        else:
            clean_name = file.name

        local_fname = os.path.join(local_file_root, clean_name)

        # Check to make sure that the file exists locally
        if not os.path.exists(local_fname):
            print(f'WARNING: {local_fname} does not exist! Skipping ...')
            continue

        # Check for existence in S3
        if s3.exists(file.name):
            print(f'{file.name} already exists in f{s3.bucket_name} bucket')
            continue

        # Copy the file
        with open(local_fname, 'rb') as local_file:
            written_file = s3.save(file.name, local_file)
            print(f'Copied {written_file}')

    return