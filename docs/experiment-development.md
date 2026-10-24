# Experiment development

PyEnsemble separates the shared Django application from experiment-specific
code and resources.

## Where experiment work belongs

Each real experiment's Python control code, templates, experiment-specific
URLs, assets, and related scripts belong in that experiment's own Git
repository. Check it out as its own directory under:

```text
pyensemble/experiments/<experiment-package>/
```

Experiment directories are Git-ignored by PyEnsemble. The tracked `debug`
package is the exception: it is the **Examples** catalog for new users and
retains its `debug` import/callback namespace for compatibility.

The PyEnsemble database stores Studies, Experiments, Forms, Questions, and
their relationships. Definition exports can be imported through the UI to
create local drafts. Experiment-specific code remains in the experiment
repository, not in the exported database definition.

## Callback discovery

The participant flow uses `run_experiment` to initialize a session and
`serve_form` to serve Forms and process responses. An Experiment's
`condition_script` and `stimulus_script` fields can refer to experiment
callbacks using a dotted path, for example:

```text
my_experiment.conditions.should_continue
my_experiment.trials.select_next
```

The first component is the experiment package directory, followed by the
Python module and callable. Callback code should use the request/session and
other supplied context as documented by the relevant handler; avoid storing
participant-specific state in process-global variables.

An experiment package can also include `urls.py` for experiment-specific
routes and templates under `templates/`. PyEnsemble discovers packages,
routes, and templates under the configured `EXPERIMENT_DIR`.

## Try the tracked Examples

The **Examples** page links to the local JSON importer. Its catalog includes
common input types, audio presentation, email callbacks, and other workflows.
Follow the import and prerequisites in
[the Examples guide](../pyensemble/experiments/debug/README.md). Use a
disposable local database when running programmatic setup examples.

## jsPsych

For client-side trials, PyEnsemble can run jsPsych timelines returned by
experiment callbacks. jsPsych is an independent checkout under `thirdparty/`,
not a submodule. Setup, plugin behavior, and plugin boundaries are described
in [jsPsych integration](./jspsych-integration.md).

## Repository boundary

Experiment-specific implementation must not enter the PyEnsemble repository,
except for the tracked `debug` Examples package. Custom client-side behavior
should be implemented as `.js` plugins under `thirdparty/jsPsych/plugins/`;
do not modify jsPsych core to add experiment features. See the
[PyEnsemble experiment development skill](../.agents/skills/pyensemble-experiment-development/SKILL.md)
for the full change policy.
