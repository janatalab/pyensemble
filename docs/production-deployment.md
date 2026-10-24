# Production deployment

This guide outlines production-specific configuration. Adapt the web-server
and operating-system commands to the supported versions and deployment
environment. Do not use Django's development server for production.

## Before deployment

- Use a supported Python runtime and install `requirements.txt`.
- Choose and provision a production database. For MySQL, install
  `requirements-mysql.txt` and follow
  [MySQL integration](./mysql-integration.md).
- Put the site-specific `pyensemble_params.ini` outside version control in
  `pyensemble/settings/local/` or another protected location configured for
  the deployment.
- Configure a unique Django `SECRET_KEY`, a durable field-encryption key,
  `ALLOWED_HOSTS`, database credentials, and logging/storage paths. Never use
  example, test, or shared keys.
- Configure production Google reCAPTCHA keys and test consent validation.
- Decide whether media, data, and static files use local durable storage or
  AWS S3. S3 requires `requirements-aws.txt` and the private `[aws]` settings.
- Configure SMTP for invitations and verification messages. Local console
  email is not a production delivery service.
- Serve the site only over HTTPS and do not expose Django debug pages.

The default WSGI entry point is `pyensemble.wsgi.application`. The default
settings module is `pyensemble.settings.settings`; configure the WSGI
environment to use a different module only when the deployment has a
deliberately maintained production profile.

## Private site configuration

The shared settings expect these sections in the private INI as applicable:

- `[django]`: `secret`, `allowed_hosts` (JSON list), `field_encryption_key`,
  `domain`, `media_root`, `media_url`, and `logdir`.
- `[django-db]`: `engine`, `host`, `name`, `user`, `passwd`, and MySQL SSL
  certificate settings. The current MySQL settings require `ssl_certname`;
  `ssl_certpath` defaults to the private settings directory when omitted.
- `[google]`: `recaptcha_key` and `recaptcha_secret`.
- `[aws]`: S3 access credentials and static, media, and data bucket names
  when using S3.
- `[spotify]` and `[prolific]`: provider credentials only if those features
  are enabled.

The exact deployment may require additional logging, SMTP, and storage
configuration. Keep the private file readable only by the service account and
administrators. Do not paste secrets into docs, shell history, or support
logs.

Field encryption keys protect sensitive participant data. Back them up
securely and plan key rotation before production data exists; losing or
replacing a key can make existing encrypted values unreadable. Never copy the
local profile's generated key or test key into production.

## Migrate and collect static files

After configuration is in place, run Django migrations against the intended
production database:

```sh
python manage.py migrate --settings=pyensemble.settings.settings
python manage.py collectstatic --noinput --settings=pyensemble.settings.settings
```

Do not run `makemigrations` as a routine deployment step. Review and commit
schema migrations as code changes before deployment. The current shared
settings use a database-backed cache; create the configured cache table if it
does not already exist.

## Web server and WSGI

Run PyEnsemble behind a production web server and WSGI server. The historical
deployment used Apache and `mod_wsgi`; its module path and configuration are
specific to the exact Python, Apache, and operating-system versions. Ensure
the WSGI process uses the intended virtual environment and project path, and
that the service account can read code/configuration and write only to
required log/media/data locations.

At minimum:

- Set a production WSGI settings module explicitly.
- Require HTTPS and configure secure proxy/host handling for the deployment.
- Keep `DEBUG=False` and restrict `ALLOWED_HOSTS`.
- Keep private configuration and participant data outside static/public code
  directories.
- Configure backups, monitoring, error reporting, and restore procedures.
- Restart/reload the WSGI service after deploying code or experiment
  repositories.

## AWS storage and CAPTCHA

If using S3, install the optional packages in `requirements-aws.txt` and
configure separate buckets/prefixes and least-privilege access for static,
media, and data files. Verify object privacy, CORS, retention, backups, and
participant-data access before go-live.

Production consent forms should validate Google reCAPTCHA using production
keys bound to the deployment's hostnames. Confirm validation fails closed when
the service or keys are misconfigured; the local-only bypass in
`pyensemble.settings.local_dev` is not for production.

See [optional integrations](./optional-integrations.md) for S3, SMTP, Prolific,
Spotify, and CAPTCHA configuration, and
[account invitations](./account-invitations.md) for account administration.
