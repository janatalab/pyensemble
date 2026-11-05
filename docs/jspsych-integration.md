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

With the `form_stimulus_s` handler, a `stimulus_script` callback returns a
jsPsych timeline and stimulus ID. `serve_form` resolves the required plugins;
`form_stimulus_s.html` loads jsPsych, `trialrunner.js`, and those plugins before
starting the timeline. This remains the required client-side interaction flow.
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

Prefer standard jsPsych plugins where possible. Store experiment-specific
plugins in the experiment's own repository:

```text
pyensemble/experiments/my_experiment/
    __init__.py
    static/
        jspsych/
            plugins/
                jspsych-custom-response.js
```

Use the qualified type in both the timeline and the plugin's registration:

```python
timeline = [
    {"type": "html-keyboard-response", "stimulus": "Instructions"},
    {"type": "my_experiment/custom-response", "stimulus": "Respond"},
]
```

```javascript
jsPsych.plugins["my_experiment/custom-response"] = (function() {
    // Return the plugin implementation using this fork's plugin API.
})();
```

The package namespace is the repository's Python package directory, not the
database Experiment title. Package names for qualified types must start with
an ASCII letter and contain only ASCII letters, digits, or underscores.
Plugin names contain ASCII letters, digits, underscores, or hyphens.

`ExperimentFinder` discovers immediate Python packages under `EXPERIMENT_DIR`
without importing them. Each package's `static/` directory is exposed under
`experiments/<package>/`. Hidden directories, underscore-prefixed directories,
and directories without `__init__.py` are excluded. Never put private
configuration, participant data, or other sensitive files in `static/`.

The example custom plugin resolves to the static path
`experiments/my_experiment/jspsych/plugins/jspsych-custom-response.js`.
Unqualified types still resolve to
`jsPsych/plugins/jspsych-<type>.js` in the shared jsPsych checkout. There is no
local override or fallback: qualifying both the static path and registration
key prevents collisions between repositories.

The resolver walks nested timelines, respects inherited types, and loads each
plugin once in first-use order. Types must be strings; dynamically computed
types and automatic JavaScript dependency discovery are not supported. Make
custom plugins self-contained. Missing or invalid plugin references produce
a logged configuration error and an error page rather than starting a broken
trial. Returning to questions after invalid form submission does not rerun
the trial or resolve its plugins.

To migrate an existing custom plugin, move it into the experiment's static
directory, qualify its registration key, and update all corresponding
timeline types. Existing shared plugins remain supported unchanged.

Restart the application after installing a repository, and run `collectstatic`
after adding or changing assets in production. Django's static storage
generates the URLs, including any deployment prefix or CDN configuration.
See [deployment](./production-deployment.md#migrate-and-collect-static-files).

Do not make cosmetic changes or experiment-specific modifications to jsPsych
core. The project's
[experiment development skill](../.agents/skills/pyensemble-experiment-development/SKILL.md)
documents these repository boundaries.

## Missing checkout

Some editor and participant features work without jsPsych. If a definition
uses a jsPsych timeline and shared assets or plugins are missing, initialize
the separate checkout above. For qualified plugins, confirm the experiment
repository and its static assets are installed. Use `findstatic` with the
resolved static path to diagnose discovery before collecting production assets.
