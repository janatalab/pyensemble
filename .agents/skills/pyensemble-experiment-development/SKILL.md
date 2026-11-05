---
name: pyensemble-experiment-development
description: "Use when creating or modifying a PyEnsemble experiment, working with run_experiment or serve_form, adding experiment-specific Python or templates, or implementing a jsPsych plugin for participant data collection."
---

# PyEnsemble Experiment Development

## Purpose and Scope

Use this skill when working on an experiment built with PyEnsemble. It explains
where experiment code belongs and sets strict boundaries between an experiment,
PyEnsemble itself, and jsPsych.

PyEnsemble is a Django website for authorized administrative users to define
Studies, Experiments, Forms, Questions, and response formats, and for
participants to take those experiments and submit data. Keep those two kinds of
work separate: experiment-specific implementation belongs in the experiment's
own repository, not in the PyEnsemble repository.

## Basic Architecture

- The PyEnsemble repository contains the Django application: models, views,
  forms, templates, services, and shared configuration.
- Administrative users use PyEnsemble's editor interfaces to configure
  experiment definitions and their ordered relationships. Their application
  roles include Editor, Release Manager, and Account Administrator.
- The participant flow is served by the Django views `run_experiment` and
  `serve_form` in `pyensemble/views.py`. `run_experiment` initializes a
  participant's experiment session; `serve_form` advances that session through
  its configured forms, presents participant-facing content, and handles
  submitted responses.
- When a form's handler is `form_stimulus_s`, `serve_form` obtains the
  experiment's jsPsych timeline and renders
  `pyensemble/templates/pyensemble/handlers/form_stimulus_s.html`. That
  template loads jsPsych and
  `pyensemble/static/pyensemble/js/trialrunner.js`, along with the plugins
  required by the timeline, then starts the timeline with `start_trial`.
  `trialrunner.js` initializes jsPsych, captures completed trial data in the
  form, and reveals the form questions when the timeline finishes.
- This `form_stimulus_s.html` plus `trialrunner.js` integration is the required
  path for client-side participant interactions in an experiment. Keep
  experiment-specific interaction logic in the experiment's timeline and
  plugins; do not bypass or replace this PyEnsemble-to-jsPsych flow.
- Experiment-specific Python modules, templates, URLs, and related resources
  are discovered under `pyensemble/experiments/`. The configured
  `EXPERIMENT_DIR` points there.
- `thirdparty/` contains checkouts of tools that support PyEnsemble. The most
  notable is `thirdparty/jsPsych/`, which supplies jsPsych for client-side
  stimulus presentation and data collection using plugins.

For more background on the application and jsPsych integration, see the
repository [README](../../../README.md).

## Experiment Repository Boundary

Each real experiment's information, Python control scripts, templates,
experiment-specific URLs, and other experiment resources MUST live in that
experiment's own Git repository. Clone or check out that repository into its
own directory under `pyensemble/experiments/`.

The experiment-specific directories under `pyensemble/experiments/` are
git-ignored by the PyEnsemble repository. The `debug/` package is the
exception: it is tracked as **Examples**, a quickstart and catalog of PyEnsemble
functionality for new adopters. Its internal `debug` package and callback
namespace remain stable for compatibility.

**Experiment-specific code MUST NOT be added to the PyEnsemble repository.**
The only exception is example code intentionally maintained in the `debug`
package. Do not add a new experiment package, protocol script, template, or
other experiment-specific resource elsewhere in the PyEnsemble repository.

## jsPsych Plugin Boundary

When an experiment needs custom client-side behavior that jsPsych does not
provide, create or modify `.js` plugin files in that experiment's own repository:

```text
pyensemble/experiments/<package>/static/jspsych/plugins/jspsych-<plugin>.js
```

Use `<package>/<plugin>` as both the timeline's `type` and the plugin's
`jsPsych.plugins` registration key. PyEnsemble discovers each experiment
package's public `static/` directory under the `experiments/<package>/`
static prefix. Packages must have `__init__.py`; hidden and underscore-prefixed
directories are excluded. Never store private information in `static/`.
Unqualified types retain their shared `thirdparty/jsPsych/plugins/` location;
there is no experiment-local override or fallback.

`serve_form` resolves an ordered, deduplicated plugin list, including nested
timelines and inherited types, and passes static paths to `form_stimulus_s.html`.
Use string-valued types and self-contained plugins; dynamic plugin type
selection and automatic dependency loading are not supported. Missing or
invalid references produce a logged configuration error. Restart workers
after installing repositories and collect static assets for production.
See [jsPsych integration](../../../docs/jspsych-integration.md).

Do not add experiment-specific code to jsPsych core files such as
`thirdparty/jsPsych/jspsych.js`, or to jsPsych examples, extensions, tests, or
other directories. Do not make cosmetic or unrelated edits to jsPsych. If a
custom plugin is appropriate, keep experiment configuration and usage of that
plugin in the experiment's own repository.

## Strict Change Policy

For a typical administrative-user task setting up an experiment:

1. Identify the experiment's own repository and its corresponding checkout
   under `pyensemble/experiments/`.
2. Make experiment-specific changes in that repository.
3. If custom client-side behavior is required, make the narrowly scoped `.js`
   plugin change under the experiment repository's `static/jspsych/plugins/`.
4. Do not change the PyEnsemble application or jsPsych core to add experiment
   features, improve presentation, or make cosmetic changes.

Changes to the PyEnsemble repository or to jsPsych core functions are permitted
only to fix a **blocking bug** that prevents the intended experiment from
working. A feature request, preference, convenience, or cosmetic issue is not
a blocking bug. When a blocking bug is confirmed, make the smallest focused
fix, add or update a regression test when practical, and explain why the bug
blocks the experiment.

If a request appears to require a prohibited change, first look for a solution
within the experiment repository or a custom plugin. If the only solution
would require a non-blocking PyEnsemble or jsPsych-core change, do not make
that change; explain the boundary and ask the user how they want to proceed.

## Production Definitions

Treat a locked Study or Experiment and its protected protocol dependencies as
immutable. Do not try to update a locked production protocol by editing
database records or circumventing application safeguards. If the research
group intends a changed protocol, use the supported clone/new-definition
workflow and make its identity or semantic version explicit in the definition
name according to the project's locking policy.
