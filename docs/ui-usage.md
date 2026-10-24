# PyEnsemble UI and participant flow

PyEnsemble has administrative interfaces for defining experiments and a
participant flow for running them.

## Administrative interfaces

After signing in, authorized users can work with:

- **Editors** for Studies, Experiments, Forms, Questions, and Enums.
- **Stimuli** for searching and managing stimulus records and files.
- **Importers** for stimulus data and exported Experiment, Form, or Question
  definitions.
- **Reports** for inspecting sessions, responses, and study/experiment data.
- **Examples** for guided local definitions and demonstrations.
- **Account invitations** for Account Administrators.

Application roles, from highest to lowest, are **Account Administrator**,
**Release Manager**, and **Editor**. Higher roles inherit lower-role access.
An active Django account without an application role does not automatically
gain access to the research interfaces. See
[account invitations](./account-invitations.md) for user provisioning and
email verification.

## Definitions and participant flow

The central definition hierarchy is:

1. A Study can order multiple Experiments.
2. An Experiment orders one or more Forms.
3. A Form contains ordered Questions.
4. A Question refers to a DataFormat, which controls the response data type.

Forms can also record optional license/usage terms and citation/attribution
metadata. These fields are included in Form JSON exports and preserved when
definitions are imported or cloned.

An Experiment is started through a participant ticket. A master ticket can be
reused; a user ticket is single-use. The participant flow begins at
`run_experiment` and advances through configured Forms using `serve_form`.
Some Form handlers perform special tasks such as participant registration or
ending a session; generic handlers serve standard response forms.

Forms may be repeated using the Experiment/Form relationship's loop settings.
Experiment-specific condition and stimulus callbacks can control progression
or supply jsPsych timelines; see
[experiment development](./experiment-development.md).

## Importing definitions

Use **Import → JSON definition** for Experiment, Form, and Question exports.
Validate first when appropriate. Create mode uses the title/name in the JSON
unless it conflicts with a different existing definition. An identical repeat
import reuses the existing object; a conflicting definition fails atomically.
Update mode targets a selected unlocked draft. Uploaded lock metadata does not
lock imported definitions.

## Locks, deletion, and data protection

Locking marks production definitions as immutable. Clone a definition to
prepare a changed draft rather than editing a locked definition. See
[experiment locking](./dev/experiment-locking.md) for release and import
behavior. Release Managers can lock a Study or Experiment. Locking expires all
existing tickets for that Experiment, or for every Experiment in the Study;
create replacement tickets after the lock. The lock covers stored database
definitions and callback references, not experiment-repository code or
stimulus records/files. Locked definitions and definitions protected through a
locked Study have their editing controls disabled in the editor.

Definitions cannot be deleted if they are locked or still referenced by a
higher-level object. See the
[deletion policy](./deletion-policy.md) for blockers, confirmation, and audit
behavior.

## Group sessions

For an experiment involving participants who coordinate in a shared session,
enable **Is group** on the Experiment. An authorized experimenter starts a
group session; participants join using the participant code displayed to the
experimenter. The Start action is available only for group Experiments. Group
workflow details and experiment-specific coordination logic belong in the
experiment documentation.

## External participant pools

SONA completion callbacks and Prolific participant/session identifiers are
optional integrations. They are not required for local development. See
[optional integrations](./optional-integrations.md) for setup and credential
requirements.
