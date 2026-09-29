# Robotikk.org backend

This is the private backend foundation for authenticated student and teacher features. The Hugo catalogue remains public and static.

## Local checks

From the repository root:

```sh
ROBOTIKK_SESSION_SECRET=test-secret python3 -m unittest discover -s backend -p 'test_*.py'
```

Runtime data belongs in `backend/data/` and is ignored by Git. Never place real user lists, passwords, password hashes, API keys, reset tokens, or student records in the repository.

## Configuration

Required runtime secret:

```text
ROBOTIKK_SESSION_SECRET
```

Optional Brevo settings:

```text
BREVO_API_KEY
BREVO_SENDER_EMAIL=noreply@login.robotikk.org
BREVO_SENDER_NAME=Robotikk.org
```

The API key must be installed as a server secret, not committed or passed to frontend code.

The production service listens only on `127.0.0.1:9100`; nginx proxies the public login and activation paths to it. The service configuration belongs in `/etc/robotikk/backend.env`, which is outside the repository.

## Import of approved users

Keep the completed CSV outside Git, for example `/etc/robotikk/invited-users.csv`. Import it on the server with the service configuration loaded:

```sh
set -a
. /etc/robotikk/backend.env
set +a
python3 backend/import_users.py /etc/robotikk/invited-users.csv
```

The importer upserts the allowlist into SQLite. It does not create passwords or send email. An invitation-sending admin flow will be added separately.

For a first delivery test, when exactly one active teacher is imported:

```sh
python3 backend/send_test_invitation.py
```

The command reads the Brevo secret from the environment, sends only to that teacher, and does not print the address or invitation token.