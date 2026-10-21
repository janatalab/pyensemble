# First-time local PyEnsemble development

## Goal

A first-time developer should be able to clone PyEnsemble, install its
dependencies, create a private local configuration, initialize a local
database, and run the example experiment without needing credentials for a
hosted database, AWS/S3 assets, production SMTP, or production Google
reCAPTCHA.

This document recommends a development experience; it does not describe
features that are already implemented. No production service credentials or
participant data should be required or copied into a local setup.

## Current setup friction

The current shared settings module reads
`pyensemble/settings/local/pyensemble_params.ini` at import time. It expects
database, encryption, media, and logging configuration, defaults to a MySQL
connection, and uses an optional `aws` section to switch storage to S3. The
development settings module imports these shared settings before overriding
some values. As a result, a local developer may still need a local INI file
with a `django-db` section and usable paths, even when they do not intend to
use hosted services.

Other onboarding friction:

- The shared settings enable `django_recaptcha`, and the consent path refers to
  `RECAPTCHA_PUBLIC_KEY`. A developer without Google keys may be unable to
  render or test that path consistently.
- `dev.py` already uses the console email backend by default, which is useful
  for local testing, but the local workflow and invitation-email expectations
  should be explained.
- Local file storage is available when `USE_AWS_STORAGE` is false, but local
  media paths and the need for sample stimulus files are not presented as a
  complete setup.
- Third-party checkouts and experiment repositories are separate from the
  PyEnsemble source. New developers need clear instructions for setting up
  `thirdparty/jsPsych` and for the distinct experiment repository convention.
- The README's deployment-oriented setup currently mixes development and
  production needs, making it difficult to tell which services are optional
  for local work.

## Recommended local developer experience

### 1. Provide a self-contained local settings profile

Create a documented local profile that can start without reading production
credentials or contacting a hosted service. Prefer an explicit settings
module, for example `pyensemble.settings.local_dev`, with isolated,
development-only defaults:

- SQLite database stored in an ignored local state directory.
- Local filesystem media and data storage in ignored directories.
- Local static-file serving and `DEBUG=True`.
- `localhost` and `127.0.0.1` as the only default development hosts.
- Console or in-memory email backend; no SMTP credentials.
- A generated, developer-specific Django `SECRET_KEY` and field-encryption
  key, never a shared production key.
- Optional integrations disabled unless a developer explicitly configures
  them.

Do not make `settings.py` silently fall back to a production database or to
credentials found in another developer's local file. Local, test, and
production settings should be visibly distinct, and local credentials or
private configuration should remain ignored by Git.

SQLite is a practical onboarding default because the existing isolated Django
test settings already use it. Before declaring the full application
SQLite-compatible, exercise migrations and the local workflows against it;
if MySQL-only behavior prevents this, offer a documented local MySQL option
without requiring access to the shared hosted database.

### 2. Make the first run an explicit, small sequence

The first-time guide should offer one copyable sequence that:

1. Creates and activates a virtual environment using a currently supported
   Python version.
2. Installs the repository's declared dependencies.
3. Initializes ignored local state/configuration from a safe example or a
   management command.
4. Applies migrations and creates any required database cache table.
5. Creates a local administrative account and assigns an application role.
6. Starts the local development server bound to loopback.
7. Opens the editor and the tracked `debug` example.

Clearly separate required steps from optional integrations. Do not require
Apache, a production-style TLS setup, external database provisioning, AWS
accounts, SMTP access, or production credentials for this workflow.

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

### 4. Make CAPTCHA behavior safe and predictable locally

Local development should not depend on production Google reCAPTCHA keys. Add
an explicit local-only behavior for consent-form testing, such as a setting
that uses provider-documented test credentials or a development bypass that
does not render a CAPTCHA and accepts the local test path.

The bypass must:

- Be off by default outside the dedicated local/test settings.
- Fail closed in production if CAPTCHA is configured as required but
  misconfigured.
- Be covered by tests proving the local path works without keys and the
  production path still enforces CAPTCHA.
- Avoid printing or committing CAPTCHA secrets.

Make missing configuration errors actionable. In particular, local consent
rendering should not fail just because a production public key is absent when
the local profile explicitly disables CAPTCHA.

### 5. Provide local media and data storage

The local profile should store uploaded media and data under ignored,
project-local directories (or a documented user data directory), without
loading AWS credentials or selecting an S3 backend. Document how to configure
the local media URL and where developers should place or upload debug
stimulus assets.

Provide a small sample asset pack or an asset-download step only where the
assets can be distributed and their source/license is clear. Missing optional
assets should produce clear instructions rather than an unexplained participant
page error. Keep production S3 settings separate from local media paths.

### 6. Document email and optional integrations

Explain that local email uses the console backend: invitation or verification
messages appear in the development server output and are not delivered. No
SMTP host, account, or password should be necessary for ordinary local
development.

Document Prolific, Spotify, AWS, SMTP, and other integrations as optional
capabilities. Each should state:

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

Provide a single local readiness command or checklist that verifies:

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

1. **Separate settings profiles.** Introduce and document local settings that
   do not require hosted credentials; prove startup and migrations work with a
   clean local checkout.
2. **Local-first integrations.** Make CAPTCHA, SMTP, S3, and external APIs
   explicit opt-ins locally. Add tests for local defaults and production
   enforcement.
3. **First-run data and assets.** Add synthetic seed data and clearly licensed
   debug assets or document their separate acquisition.
4. **Onboarding and diagnostics.** Replace the development path in the README
   with a concise quickstart, preserve production deployment instructions in
   a separate section, and add readiness checks and troubleshooting.
5. **Fresh-machine acceptance test.** Have a developer without shared database,
   AWS, CAPTCHA, SMTP, or experiment-repository credentials follow the guide
   from a clean clone and complete the editor-to-participant debug flow.

## Acceptance criteria

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
