# Optional integrations

Core local development does not require credentials for external providers.
Configure only the integrations used by a deployment, and keep credentials
outside version control.

## AWS S3 storage

The production settings enable S3 storage when the private site INI includes
an `[aws]` section. Install its dependencies from the repository root:

```sh
pip install -r requirements-aws.txt
```

The section supplies the S3 access key, secret key, and separate bucket names
for static assets, media, and data. Use an AWS identity with only the
permissions required by these buckets. Do not add the section to local
settings when using local filesystem storage.

## Google reCAPTCHA

Production consent forms require reCAPTCHA. The private INI's `[google]`
section supplies `recaptcha_key` and `recaptcha_secret`; production CAPTCHA
validation remains enabled. Configure the provider's allowed hostnames to
match the production site and test the consent path after deployment.

The local development settings explicitly disable CAPTCHA and do not need
Google keys. Do not carry this local bypass into a production settings module.

## Prolific

Prolific integration requires an API endpoint, API token, and any experiment
or workspace identifiers required by the selected workflow. The production
settings read endpoint and token from the private `[prolific]` INI section.
Only use the Prolific admin/test workflows when credentials are configured;
ordinary development and participant testing do not require them.

The tracked Examples include a completion-redirect definition with a
placeholder completion code. Replace it with a code issued for the intended
study before use.

## SONA

For SONA participation, set the Experiment's SONA completion URL using the
provider's redirect template, with `XXXX` where the participant's SONA survey
code should be inserted. The participant starts PyEnsemble with a `sona`
query parameter; PyEnsemble carries that code through the session and redirects
to the configured completion URL at the end. No SONA SDK or API credentials
are required by the core application.

## Spotify

Spotify import features require the Spotify client ID and client secret in the
private `[spotify]` section. Leave this section absent when Spotify import is
not needed.

## SMTP email

Local development uses the console email backend; messages appear in the
development server output and are not delivered. Account invitations and
verification email in production require a configured SMTP-capable email
backend. See [account invitations](./account-invitations.md) for the required
deployment settings and trusted invitation origin.

## Optional packages

- MySQL: install `requirements-mysql.txt`; see
  [MySQL integration](./mysql-integration.md).
- AWS S3: install `requirements-aws.txt`.
- reCAPTCHA: `django-recaptcha` remains in core requirements, but local
  development does not require production keys.
