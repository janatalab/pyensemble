# jsPsych integration

PyEnsemble can use jsPsych to present browser-based trials and collect
participant responses. The PyEnsemble repository does not vendor jsPsych or
track it as a Git submodule. Check it out as a separate repository under the
ignored `thirdparty/` directory.

## Set up the jsPsych checkout

From the PyEnsemble repository root:

```sh
mkdir -p thirdparty
git clone https://github.com/janatalab/jsPsych.git thirdparty/jsPsych
```

The `janatalab/jsPsych` fork is the version this project has historically used.
It includes a Safari audio playback adjustment in
`plugins/jspsych-audio-keyboard-response.js`. Review that fork and its current
compatibility before selecting another jsPsych distribution.

`thirdparty/` is Git-ignored by PyEnsemble. The checkout is maintained
independently; update it using Git commands from inside `thirdparty/jsPsych`.
Do not add it as a submodule or commit experiment-specific code into the
PyEnsemble repository.

## How PyEnsemble uses jsPsych

An Experiment's `stimulus_script` callback can return a jsPsych timeline. The
participant page loads the needed plugin scripts and executes the timeline.
When the timeline completes, PyEnsemble can continue to its configured Forms.
Alternatively, jsPsych-collected trial data can be submitted with the form and
stored in the response's jsPsych data field.

One PyEnsemble form presentation runs its associated jsPsych timeline to
completion. For audio playback, the local **Examples** catalog includes a
Test Audio definition and sample assets; see
[the Examples guide](../pyensemble/experiments/debug/README.md).
The bundled audio examples are copyrighted by the Janata Lab at the University
of California, Davis; consult that guide before reusing or distributing them.

## Custom plugins and repository boundaries

Prefer standard jsPsych plugins where possible. When experiment-specific
client-side behavior needs a custom plugin, create or modify only `.js` plugin
files under `thirdparty/jsPsych/plugins/`. Keep experiment callbacks,
templates, definitions, and asset handling in that experiment's own repository
under `pyensemble/experiments/`.

Do not make cosmetic changes or experiment-specific modifications to jsPsych
core. The project's
[experiment development skill](../.agents/skills/pyensemble-experiment-development/SKILL.md)
documents these repository boundaries.

## Missing checkout

Some editor and participant features work without jsPsych. If a definition
uses a jsPsych timeline and its assets or plugins are missing, initialize the
separate checkout above and confirm the requested plugin exists under its
`plugins/` directory.
