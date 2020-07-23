# __init__.py
#

# The packages under experiments should be installation- or lab-specific
# experiment scripts that are used for stimulus importing, stimulus selection,
# jsPsych timeline specification, data analysis, and any other
# experiment-specific functionality that the user wishes to enable.

# Experiments are not added to the PyEnsemble git repository. Rather, they
# should be maintained in separate repositories and simply cloned in this
# location. This init file automatically detects the directories and exposes
# them to the rest of Py#nsemble. The PyEnsemble .gitignore file contains a
# directive to ignore sub-directories within this directory.

from pathlib import Path
from django.conf import settings

# Get our current directory
p = Path(settings.EXPERIMENT_DIR)

# Generate the list of packages to expose
__all__ = [d.name for d in p.iterdir() if d.is_dir() and d.name != '__pycache__']

