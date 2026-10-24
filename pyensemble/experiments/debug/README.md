# PyEnsemble Examples

This tracked `debug` experiment package is the application's examples hub. Its
URL and callback namespace intentionally remain `debug` for compatibility with
saved definitions; use **Examples** when referring to it in the interface and
onboarding material.

## First example: import a definition

1. Start PyEnsemble with the local profile and sign in with the local
   administrative account.
2. Open **Import** and choose **JSON definition**.
3. Select an Experiment file from `assets/definition-exports/`.
4. Run **Validate only** first. Then choose **Create a new draft** and import
   it. The JSON title/name is used automatically unless it conflicts with a
   different existing definition.
5. Review the imported definition in the Experiment, Form, and Question
   editors. Experiment exports include their nested Forms, Questions, and
   response formats; separate Form and Question exports are optional examples
   of those smaller import units.
6. Create a participant ticket in the editor before opening the participant
   run URL. Do not expose the local development server to an untrusted network.

Imports create editable, unlocked local definitions. Uploaded lock fields and
release metadata are not imported as locks. Re-importing the same definition
with the same name and contents reuses the existing objects rather than
creating duplicates. If an existing object has the same identity (for example,
the same Experiment title, Form name, or Question text) but different
definition contents or relationships, the importer rejects the conflicting
import without partially applying it. To intentionally change a draft, use
**Update an existing unlocked draft** and select that draft; **Validate only**
can preview either operation.

## Catalog

| Export | Demonstrates | Requirements |
| --- | --- | --- |
| `experiment_test-input-types.json` | Experiment with nested Forms and Questions using common response controls | Local database |
| `experiment_test-audio.json` | jsPsych audio playback followed by a PyEnsemble response form | jsPsych checkout and imported example audio Stimuli |
| `experiment_example-further-participation.json` | Conditional follow-up, email collection, and notification callbacks | Local console email |
| `experiment_example-email-login.json` | Email-based participant login and follow-up callbacks | Local console email |
| `experiment_prolific-redirect-test.json` | Completion redirect parameter example | Replace the placeholder Prolific completion code |
| `form_bmrq-survey.json` | BMRQ Form with license and citation metadata | CC BY 4.0; attribution is included in the Form metadata |
| `form_stomp-survey.json` | STOMP Form with usage terms | Public domain for academic, research, and non-commercial educational use |
| `question_color-vision-screening.json`, `question_hearing-screening.json` | Standalone Question imports | Demonstration only; consider the sensitivity of screening questions in real studies |

The export filenames are generated from the object type and a normalized
version of its title, form name, or question text. The corresponding editor
**Export JSON** action emits readable, indented JSON.

## Audio example setup

The Test Audio definition's callback selects the Stimulus named `Jazz7`.
Import the audio Stimuli before running the example. The manifest
`assets/audio-stimuli.csv` maps both bundled MP3s to Stimulus names.

From the `assets` directory, create a ZIP containing the manifest and audio
files:

```sh
cd pyensemble/experiments/debug/assets
zip -j /tmp/pyensemble-example-audio.zip audio-stimuli.csv audio/*.mp3
```

In PyEnsemble, open **Stimuli → Import** and upload that ZIP. Then import
`experiment_test-audio.json`. Ensure the separate `thirdparty/jsPsych`
checkout is installed; see [jsPsych integration](../../../docs/jspsych-integration.md).

## Python setup examples

The `tasks.py`, `group.py`, and `prolific.py` modules illustrate administrative
object creation and specialized workflows. They are not participant links to
try casually. In particular, setup helpers may update existing
Experiment/Form relationships. Use them only with a disposable local database,
never a shared or production instance. Prolific examples require separately
configured Prolific credentials.

## Asset and content notes

The two bundled audio examples are copyrighted by the Janata Lab at the
University of California, Davis. The STOMP Form is public domain for academic,
research, and non-commercial educational use. The BMRQ Form is licensed under
CC BY 4.0; its citation and license are recorded in the Form metadata and
included in its JSON export. Retain the attribution when reusing the BMRQ
content. These Forms are optional examples and are not required for the local
quickstart. Do not copy participant data into this package.

The Prolific redirect example uses a placeholder completion code. Replace it
with a code issued for the intended Prolific study before use. Email addresses
in example definitions should be generic placeholders, not personal or
production contact addresses.
