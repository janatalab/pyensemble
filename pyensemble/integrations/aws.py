# aws.py

from pyensemble.models import Stimulus
from pyensemble.group.models import GroupSessionFile


import pdb

'''
Define a method that we can use to copy locally stored media and data files
to an appropriate AWS S3 bucket so that they can then be accessed using
our custom S3 storage backends, S3MediaStorage, and S3DataStorage.

queryset should either be Stimulus or GroupSessionFile objects
'''
def copy_local_to_S3_bucket(queryset):
    # Perform some integrity checks to make sure that this operation can succeed
    filetype = gdf.model._meta.model_name

    # Make sure that the class of the QuerySet is valid
    if filetype not in ['groupsessionfile', 'stimulus']:
        raise ValueError(f'No handling of {filetype} querysets')

    # Determine our local file root (assume it is in MEDIA_ROOT)

    for instance in queryset:
        # Check to make sure that the file exists locally

    return