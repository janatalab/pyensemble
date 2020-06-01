# __init__.py
#
# The packages in this package should contain all methods and classes relevant to a particular experiment. These include stimulus and attribute importers as well as stimulus selectors
# 
# For the experiment's methods to be visible to PyEnsemble, the experiment package must be imported here, and each experiment package must have an __init__.py file that makes visible what needs to be made visibile, i.e. those methods that specified in ExperimentXForm.{condition_script,stimulus_script}
# Each experiment package should also have its on urls.py file in order to expose any experiment-specific endpoints.

# TODO: Have this init file auto-import any package that is placed in this location

# Whenever an experiment-specific package is added, include it in this list
__all__ = ['debug','jingles','musmemfmri']

