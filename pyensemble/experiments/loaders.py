# loaders.py
from pathlib import Path

from django.conf import settings
from django.template.loaders.filesystem import Loader as FilesystemLoader

class Loader(FilesystemLoader):

    def get_dirs(self):
        if self.dirs:
            return self.dirs
        else:
            # Get our base experiment dir
            p = Path(settings.BASE_DIR,'pyensemble','experiments')

            # Get our sub-directories
            dirs = [d for d in p.iterdir() if d.is_dir()]

            for d in dirs:
                # Construct the putative template directory path
                template_dir = d / 'templates'

                # Append to our directory list if it exists
                if template_dir.exists():
                    if not self.dirs:
                        self.dirs = []

                    self.dirs.append(template_dir)

            return self.dirs
