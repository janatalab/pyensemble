"""Discover public static assets in experiment repositories."""

from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles.finders import FileSystemFinder
from django.core.files.storage import FileSystemStorage


class ExperimentFinder(FileSystemFinder):
    def __init__(self, app_names=None, *args, **kwargs):
        self.locations = []
        self.storages = {}
        root = Path(settings.EXPERIMENT_DIR)
        for package in sorted(root.iterdir()):
            if (
                not package.is_dir()
                or not package.name.isidentifier()
                or package.name.startswith('_')
                or not (package / '__init__.py').is_file()
            ):
                continue
            static_dir = package / 'static'
            if static_dir.is_dir():
                prefix = f'experiments/{package.name}'
                storage = FileSystemStorage(location=static_dir)
                storage.prefix = prefix
                self.locations.append((prefix, str(static_dir)))
                self.storages[str(static_dir)] = storage

    def check(self, **kwargs):
        # Locations are discovered, not supplied by STATICFILES_DIRS.
        return []
