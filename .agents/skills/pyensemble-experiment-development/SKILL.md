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
git-ignored by the PyEnsemble repository. The `debug/` experiment is the
exception: it is tracked in PyEnsemble as a quickstart and example of
PyEnsemble functionality for new adopters.

**Experiment-specific code MUST NOT be added to the PyEnsemble repository.**
The only exception is example code intentionally maintained in the `debug`
experiment. Do not add a new experiment package, protocol script, template, or
other experiment-specific resource elsewhere in the PyEnsemble repository.

## jsPsych Plugin Boundary

When an experiment needs custom client-side behavior that jsPsych does not
provide, create or modify only `.js` plugin files under:

```text
thirdparty/jsPsych/plugins/
```

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
3. If custom client-side behavior is required, make the narrowly scoped plugin
   change only under `thirdparty/jsPsych/plugins/`, limited to `.js` files.
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
