# urls.py

# Each experiment package within this directory may have its own urls.py file
# in order to expose any experiment-specific endpoints.

from pathlib import Path
from importlib import import_module

from django.urls import include, path
from django.conf import settings

app_name='experiments'

# Initialize or list of urlpatterns
urlpatterns = []

# Get our current directory
p = Path(settings.EXPERIMENT_DIR)

# Get our list of experiments
experiment_dirs = [d for d in p.iterdir() if d.is_dir() and d.name != '__pycache__']

# Iterate over the subdirectories
for experiment in experiment_dirs:
    # Check for the existence of a urls.py file in the sub-directory
    url_file = experiment / 'urls.py'
    
    if url_file.exists():
        experiment_name = experiment.name

        # Import the urls module
        module = import_module('pyensemble.experiments.'+experiment_name+'.urls')

        # Include it in the url patterns
        urlpatterns.append(path(f'{experiment_name}/', include(module)))
