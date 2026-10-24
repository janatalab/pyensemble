# PyEnsemble

PyEnsemble is a Django application for authorized users to define research
Studies, Experiments, Forms, Questions, and response formats, and for
participants to take those experiments and submit data. The participant flow
is served by the `run_experiment` and `serve_form` views. Experiment control
code can be written in Python, and browser-based trials can use jsPsych.

## Quickstart for local development

The default local profile is self-contained: it uses SQLite, local file
storage, console email, and local-only CAPTCHA bypass. It does not require
production database, AWS, SMTP, or Google reCAPTCHA credentials.

From a terminal:

```sh
git clone https://github.com/janatalab/pyensemble.git
cd pyensemble
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate --settings=pyensemble.settings.local_dev
python manage.py createsuperuser --settings=pyensemble.settings.local_dev
python manage.py runserver 127.0.0.1:8000 --settings=pyensemble.settings.local_dev
```

Open <http://127.0.0.1:8000/> and sign in with the superuser you created. Keep
the development server bound to loopback; do not expose it to an untrusted
network. The SQLite database, local keys, and uploaded files live under the
Git-ignored `.local/` directory. The field-encryption key is persisted there;
deleting `.local/` resets the local database and media, and encrypted values
from the deleted database cannot be recovered.

The local database starts without experiment definitions. To try the app,
open **Import → JSON definition**, validate an Experiment export, then import
it as a new draft. The tracked `debug` experiment is presented in the UI as
**Examples**. Its
[guide and catalog](pyensemble/experiments/debug/README.md) cover imports,
audio assets, Python setup examples, and prerequisites.

To check the local Django configuration, run:

```sh
python manage.py check --settings=pyensemble.settings.local_dev
```

If a command complains about missing production INI settings, make sure it
uses `--settings=pyensemble.settings.local_dev`. The audio example also
requires importing its sample Stimuli and checking out jsPsych as described in
the [Examples guide](pyensemble/experiments/debug/README.md) and
[jsPsych integration](docs/jspsych-integration.md). The audio and legacy
questionnaire examples carry copyright or license terms; see the Examples
guide for their copyright, license, and attribution information.

## jsPsych integration

jsPsych is an independent Git checkout under the ignored `thirdparty/`
directory; it is **not** a Git submodule. Clone the project fork when an
experiment requires browser-side trials:

```sh
mkdir -p thirdparty
git clone https://github.com/janatalab/jsPsych.git thirdparty/jsPsych
```

PyEnsemble can load jsPsych timelines returned by experiment callbacks and
store jsPsych response data. Detailed setup, behavior, and plugin boundaries
are in [jsPsych integration](docs/jspsych-integration.md).

## Optional MySQL

SQLite is sufficient for local application development. For an instance
configured to use MySQL, install `requirements-mysql.txt` and configure the
site-specific database settings. macOS users may need Homebrew's MySQL client
headers and a runtime dynamic-library path for `mysqlclient`.

See [MySQL integration](docs/mysql-integration.md) for setup and macOS
troubleshooting.

## Production deployment

Production deployment requires a production WSGI server, secure private
settings, HTTPS, an appropriately configured database, durable field
encryption keys, and operational backups. AWS S3 and Google reCAPTCHA are
production integrations, not requirements for the local quickstart.

Read [Production deployment](docs/production-deployment.md) before preparing
an instance. For SMTP, S3, reCAPTCHA, Prolific, and Spotify configuration, see
[Optional integrations](docs/optional-integrations.md). Account invitations
require a trusted HTTPS origin and working email delivery; see
[Account invitations](docs/account-invitations.md).

## Using the interfaces

Administrative application roles, from highest to lowest, are Account
Administrator, Release Manager, and Editor; higher roles inherit lower-role
access. Editors can define and import content, manage stimuli and tickets, and
use reporting interfaces. Accounts and participant sessions are separate.

The [UI usage guide](docs/ui-usage.md) describes the definition hierarchy,
participant flow, importing definitions, locks, deletion, group sessions, and
external participant pools. See also
[experiment locking](docs/dev/experiment-locking.md) and the
[deletion policy](docs/deletion-policy.md).

## Experiment repositories

Each real experiment's code, templates, URLs, assets, and supporting scripts
belong in that experiment's own Git repository, checked out under
`pyensemble/experiments/`. The experiment directories are ignored by this
repository. The tracked `pyensemble/experiments/debug/` package is the
exception and exists as the quickstart **Examples** catalog.

Experiment-specific implementation must not be added to PyEnsemble. When
custom browser behavior is needed, changes are limited to `.js` plugins under
`thirdparty/jsPsych/plugins/`; do not change jsPsych core for experiment
features. See [Experiment development](docs/experiment-development.md) and
the [PyEnsemble experiment development skill](.agents/skills/pyensemble-experiment-development/SKILL.md)
for the repository boundaries.

## Optional integrations

Integrations such as SONA, Prolific, Spotify imports, MySQL, and AWS S3 are
optional and require their corresponding provider setup. See
[Optional integrations](docs/optional-integrations.md) for an overview.

## Development and tests

Use the project's test suite and formatting conventions for application
changes. Run the Django suite with:

```sh
python manage.py test --settings=pyensemble.tests.settings
```

The test settings are isolated from site-specific production credentials.
