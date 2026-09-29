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