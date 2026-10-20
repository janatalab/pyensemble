# Account invitations

## Policy and roles

Administrative users are separate from experiment participants. Account
administrators and active superusers can invite new users through **Account
invitations** on the PyEnsemble home page, or at `/accounts/invitations/`.
Django admin access is not required to use this page.

An inviter may choose any of these roles, highest first:

| Group | Access |
|---|---|
| Account administrator | Invitation management and all Release manager/Editor access |
| Release manager | All Editor access; reserved for future release actions |
| Editor | Editing, imports, stimuli, reports, exports, data management, tickets, and experimenter/group management |

Higher roles inherit lower-role access. The invitation supplies approval and
role assignment. Possession of its emailed link, followed by submission of the
account-creation form, verifies ownership of the invited email address. No
second verification email or approval step is required.

Accepting an Account administrator invitation does **not** grant Django
`is_staff`, superuser status, or Django model permissions.

## Sending and accepting an invitation

1. Sign in as an Account administrator or active superuser.
2. Open **Account invitations**, enter the recipient's email address, choose a
   role, and submit.
3. The recipient follows the emailed link and chooses a username and password.
   The email address and role cannot be changed by the recipient.
4. A CSRF-protected POST creates the user, records verification/acceptance, and
   assigns the role in one transaction.
5. The recipient signs in normally. Acceptance does not automatically log them
   in.

GET requests, including email-scanner prefetches, do not consume invitations or
create accounts. Django's password validators and username uniqueness rules
apply. No user account is created merely by sending an invitation.

Only a digest of the random, 256-bit token is stored. Links expire after 24
hours and can be used once. Acceptance is serialized with resend/revoke
operations using a locked invitation row on databases supporting row locks.
No account is created for invalid, expired, revoked, unsent, or consumed links.

Invitations are also unusable while the issuing administrator is inactive,
deleted, or lacks Account administrator access. Suspending an inviter does not
automatically suspend users who already accepted invitations.

## Resending, revoking, and delivery failures

To resend, submit the same email address through the invitation form. The
selected role replaces the prior role and the new link invalidates the old link.
Email addresses are stripped and lowercased; a unique invitation row reserves
each canonical address. This application intentionally treats email addresses
case-insensitively.

Wait at least 60 seconds between sends to the same address. Each administrator
may attempt at most 20 sends per hour, including failed deliveries. These limits
are persisted in the database, not reset by restarting web workers.

The invitation list shows pending, not-sent, expired, revoked, and accepted
states. **Revoke** requires a CSRF-protected POST and blocks an unaccepted link.
Resending after the cooldown can replace a revoked or expired invitation.

Sending is synchronous, using Django's configured email backend and the existing
multipart email helper. SMTP failures or a zero-message submission produce an
explicit form error and a server log entry without the token or SMTP exception
details. No account is created; correct configuration and resend after the
cooldown. The digest-only design intentionally does not retain a recoverable
token for background retry. There is no automatic delivery queue in this phase.

A successful submission means the configured backend accepted the message; it
does not guarantee delivery or inbox placement. In particular, console and
in-memory backends do not send external mail.

Existing account addresses cannot be invited to reset a password or change a
role. An account created through another path after invitation issuance also
blocks acceptance. Already accepted invitations remain consumed even if the
associated account is later deleted.

## Configuration

Run migrations before deploying the feature:

```sh
python manage.py migrate
```

Migration [0028_account_invitations.py](../pyensemble/migrations/0028_account_invitations.py)
creates the invitation and delivery-attempt tables. It does not change existing
users, roles, or participant records.

### Trusted link origin

Configure the origin explicitly in the web application's environment:

```sh
export PYENSEMBLE_ACCOUNT_INVITATION_ORIGIN=https://ensemble.example.org
```

This sets `ACCOUNT_INVITATION_ORIGIN`. It must contain the scheme, hostname, and
optional port only, without credentials, a path, query, or fragment. Production
requires HTTPS. A missing/invalid value blocks sending with an actionable error;
the incoming request's Host header is never used to construct invitation links.

For applications mounted at a URL prefix, configure Django's normal script
prefix handling (for example `FORCE_SCRIPT_NAME='/pyensemble'`) so `reverse()`
includes it. Do not append the prefix to the origin setting.

### Manual local testing without SMTP

[Development settings](../pyensemble/settings/dev.py) default to the console
email backend and `http://localhost:8000` as the invitation origin:

```sh
python manage.py runserver localhost:8000 --settings=pyensemble.settings.dev
```

This uses your configured development database; migrate it and provision an
administrator first. Do not point development settings at production data.

Sign in, send an invitation, and copy the URL printed in the server terminal
into a private browser window. Create the account and sign in normally.
No SMTP server or external email delivery is needed.

If using `runsslserver`, a different host, or a different port, set
`PYENSEMBLE_ACCOUNT_INVITATION_ORIGIN` accordingly. HTTP is accepted only for
localhost/loopback while `DEBUG=True`. Console output contains live tokens;
treat it as sensitive and do not share it.

### Production SMTP, including an unauthenticated relay

Production settings default to Django's SMTP backend. Configure the existing
private INI file's `[email]` section, for example:

```ini
[email]
host = smtp.internal.example.org
port = 25
host_user =
host_password =
use_tls = false
use_ssl = false
timeout = 10
default_from_email = ensemble@example.org
```

Empty credentials support a relay that authorizes the application server without
SMTP authentication. Use the TLS/SSL policy required by the real relay; the
example does not establish a recommended transport policy. Do not enable both
TLS and SSL. Port, timeout, and TLS/SSL flags are parsed as their proper types.
Restrict relay access to authorized infrastructure; do not expose an open relay.

To choose a backend explicitly:

```sh
export PYENSEMBLE_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
```

The same override works in development. Development now defaults all Django mail
to the console backend to avoid accidentally sending real participant or account
messages during local work.

## Verification and operations

Run both invitation and access regression tests without production settings or
external services:

```sh
python manage.py test pyensemble.tests.test_access pyensemble.tests.test_account_invitations --settings=pyensemble.tests.settings --noinput
```

The isolated settings use in-memory SQLite and Django's in-memory email outbox.
Tests follow actual emailed links and cover role assignment/inheritance,
password policy, token lifecycle, safe GET behavior, CSRF, delivery failures,
origin validation, throttling, and existing interface access.

SQLite tests do not prove concurrent row-lock behavior. Before production
rollout, verify concurrent acceptance/resend/revocation using the deployed
database backend (normally MySQL/InnoDB).

Do not log request bodies containing passwords or full invitation URLs. Redact
the `/accounts/accept/` token path in reverse-proxy, application request/error,
analytics, and monitoring logs; default web-server access logs may otherwise
capture it. Acceptance responses use no-store caching, same-origin referrer, and noindex
headers, but infrastructure logging still needs deployment configuration.
The same-origin referrer policy suppresses referrers to external sites while
preserving browser origin information needed for CSRF-protected form submission.
Do not use `no-referrer` on this form: browsers can send `Origin: null` on POST,
which Django correctly rejects. `ALLOWED_HOSTS` does not override CSRF origin
checks, and `null` must not be trusted to work around this error.

Apply infrastructure-level request limits to public account-acceptance
endpoints, and set appropriate retention/access policies for invitation email
addresses and audit records. Database delivery records retain sender and timing;
acceptance records retain the verified address, user, and acceptance timestamp.
Application logs identify issuance attempts, acceptance, and revocation by IDs,
not usable tokens.

The current implementation assumes Django's existing username-based user model.
Invitation email uniqueness is enforced within this workflow; privileged Django
admin/shell writes still need operational controls to avoid introducing
duplicate user emails through other paths.

Password recovery, changing verified email addresses, a general account
suspension/role-management UI, MFA, durable automatic mail retry, and experiment
locking remain separate work.
