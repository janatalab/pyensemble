# First-time local PyEnsemble development

## Goal

The goal is for a first-time developer to clone PyEnsemble, install its
dependencies, initialize a local database, and run an example experiment
without credentials for a hosted database, AWS/S3, production SMTP, or
production Google reCAPTCHA.

The repository now includes an independent `pyensemble.settings.local_dev`
profile for core application development. It does not read the private site
configuration. The profile provides local SQLite and file storage, local
development keys, disabled CAPTCHA, and console email. The additional
recommendations below describe remaining onboarding work. The profile does not
yet seed the example definitions or supply missing stimulus assets.

## Remaining onboarding work

The production settings module reads
`pyensemble/settings/local/pyensemble_params.ini` at import time. It expects
database, encryption, media, and logging configuration, defaults to a MySQL
connection, and uses an optional `aws` section to switch storage to S3. The
older `pyensemble.settings.dev` module imports these production settings before
overriding some values, so it still requires a usable site INI file. Use
`pyensemble.settings.local_dev` for a clean local setup instead.

The standalone profile and README quickstart address core startup, migrations,
and local account creation. Remaining gaps include example seed data and
stimulus assets, setup instructions for third-party checkouts and separate
experiment repositories, and a readiness/troubleshooting check that validates
these resources.

## Recommended local developer experience

### 1. Self-contained local settings profile (implemented)

Use the independent settings module `pyensemble.settings.local_dev`. It starts
without reading production credentials or contacting a hosted service, and
provides:

- SQLite database at `.local/pyensemble.sqlite3`.
- Local filesystem media/data storage under `.local/media/` and static output
  under `.local/static/`.
- `DEBUG=True`, with `localhost` and `127.0.0.1` allowed.
- Console email; outgoing messages appear in the server terminal.
- A persistent, per-checkout Django key stored in `.local/secret_key`; the
  field-encryption key is derived from it. Keep `.local/` private and ignored.
- Optional API integrations left without credentials; AWS storage is disabled.
- CAPTCHA disabled only in this explicitly selected local profile. Production
  settings continue to require CAPTCHA validation.

The local profile points `SITE_CONFIG_FILE` to a harmless local INI containing
only `domain = localhost`, because an existing historical migration reads that
setting. It never reads the private production INI.

The full migration set has been exercised using SQLite. Local cache uses
process-local memory, so `createcachetable` is not required. This profile is
for local development only; it is not a production deployment configuration.
The generated key is persisted to preserve access to encrypted local data.
Deleting `.local/` resets the database, media, and key; encrypted values from
the deleted database cannot be recovered with a newly generated key. Set
`PYENSEMBLE_LOCAL_STATE_DIR` to use a different local state location.

### 2. Make the first run an explicit, small sequence

From the repository root, the local profile can be started with:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate --settings=pyensemble.settings.local_dev
python manage.py createsuperuser --settings=pyensemble.settings.local_dev
python manage.py runserver 127.0.0.1:8000 --settings=pyensemble.settings.local_dev
```

Open `http://127.0.0.1:8000/`. Use the superuser for local administrative
access. No Apache, production TLS setup, hosted database, AWS account, SMTP
access, cache-table creation, or production credential is needed.

### 3. Ship a useful local example dataset

Provide a repeatable way to populate a fresh local database with a minimal
example Study/Experiment, Forms, Questions, response formats, and any
relationships needed to demonstrate the main editor and participant flow.
Prefer version-controlled fixtures or an idempotent development-only seed
command. The `debug` experiment should be the primary example for
experiment-specific callbacks and templates.

Use synthetic records and small, redistributable sample assets. Do not seed
participant data, import production records, or include private stimulus files.
Document separately which debug features require assets that are deliberately
not distributed.

### 4. CAPTCHA behavior (local bypass implemented)

Local development uses `PYENSEMBLE_CAPTCHA_ENABLED = False`: the consent view
does not render a CAPTCHA widget or require a CAPTCHA response. Other settings
default CAPTCHA enforcement to enabled, and production continues to validate
consent submissions. The local settings silence the package's test-key system
check because CAPTCHA is intentionally disabled there.

Future hardening and tests should ensure this bypass remains restricted:

- Be off by default outside the dedicated local/test settings.
- Fail closed in production if CAPTCHA is configured as required but
  misconfigured.
- Be covered by tests proving the local path works without keys and the
  production path still enforces CAPTCHA.
- Avoid printing or committing CAPTCHA secrets.

Make missing configuration errors actionable. In particular, local consent
rendering should not fail just because a production public key is absent when
the local profile explicitly disables CAPTCHA.

### 5. Local media and data storage (implemented)

The local profile stores media/data under `.local/media/` and serves media
through Django's development URL route at `/media/`. Static output is under
`.local/static/`; AWS storage is disabled, and no AWS credentials are loaded.
Developers can upload local assets through the application or place files in
the relevant media subdirectory.

The profile does not include sample stimulus assets. A redistributable sample
asset pack or a documented download step remains future work; any assets must
have clear licensing. Missing optional assets should produce clear
instructions rather than an unexplained participant-page error.

### 6. Local email and optional integrations (email backend implemented)

Local email uses Django's console backend: invitation or verification messages
appear in the development server output and are not delivered. No SMTP host,
account, or password is needed for ordinary local development.

The local settings provide empty values for external integration credentials
and disable AWS storage. More complete feature-specific documentation for
Prolific, Spotify, and other integrations remains useful. It should state:

- Which feature requires it.
- Which configuration keys are needed.
- Whether a safe local mock or test mode exists.
- How to leave it disabled locally.

Avoid making application startup require secrets for integrations a developer
is not using.

### 7. Clarify experiment and jsPsych repository setup

The onboarding instructions should distinguish:

- The PyEnsemble application repository.
- The separately checked-out `thirdparty/jsPsych` repository.
- Each experiment's own Git repository under `pyensemble/experiments/`.

Experiment directories are git-ignored in the PyEnsemble repository except for
the tracked `debug` example. A first-time user can develop the application and
explore `debug` without access to a real experiment repository. To run another
group's experiment, they need that group's repository and any separately
distributed assets.

### 8. Add a local readiness check and troubleshooting guide

`manage.py check --settings=pyensemble.settings.local_dev` runs Django's
standard system checks. A dedicated readiness command or checklist could
additionally verify:

- The chosen settings profile is the local one.
- The database is local and migrations are current.
- Static and media storage resolve to local paths.
- No AWS or SMTP credentials are required.
- CAPTCHA is in the explicitly selected local mode.
- Required local directories exist and are writable.
- The debug experiment and jsPsych assets are discoverable.

Troubleshooting should map common configuration failures to remedies, including
missing INI sections, database connection attempts to a hosted hostname,
missing CAPTCHA settings, missing media, and missing jsPsych checkout.
Diagnostics must not print secrets.

## Suggested rollout

1. **Verify a fresh checkout.** Follow the quickstart without any local
   production INI file or hosted credentials.
2. **First-run data and assets.** Add synthetic seed data and clearly licensed
   debug assets or document their separate acquisition.
3. **Onboarding and diagnostics.** Add readiness checks and troubleshooting
   for local database, static/media storage, debug experiment, and jsPsych
   assets.
4. **Fresh-machine acceptance test.** Have a developer without shared database,
   AWS, CAPTCHA, SMTP, or experiment-repository credentials follow the guide
   from a clean clone and complete the editor-to-participant debug flow.

## Long-term acceptance criteria

A first-time developer following the documented local workflow from a clean
clone can, without any hosted-service credentials:

- Start PyEnsemble on loopback with a local database and local file storage.
- Sign in to the administrative interface with a local development account.
- Load or create the documented synthetic example definitions.
- Exercise the `debug` participant flow through experiment startup and form
  serving.
- Test invitation/verification behavior by reading locally emitted email.
- Test a consent form without production reCAPTCHA credentials, while the
  production configuration remains protected against accidental bypass.
- Run the project test suite without connecting to deployment services.

## Credential hygiene

Never copy values from a developer's local INI file into documentation,
fixtures, logs, or source control. Before sharing a local configuration file,
verify it contains no database passwords, encryption keys, API tokens, SMTP
credentials, or CAPTCHA secrets. Keep local configuration and generated
database/media files ignored by Git. If a credential may have been shared
outside its intended audience, treat it as exposed and rotate it.
