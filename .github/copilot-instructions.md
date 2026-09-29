# Project instructions for AI assistants

These are mandatory workspace requirements for every AI assistant or coding agent working in this repository.

## Visual design is a requirement

Before changing any frontend, layout, content presentation, CSS, JavaScript interaction, or user-facing flow, read `DESIGN-SPEC.md` in the repository root. Treat it as a binding specification, not optional advice.

- Follow its palette, contrast, typography, spacing, responsive, interaction, print, and accessibility rules.
- Use the existing global CSS tokens before adding a new color, shadow, radius, or component pattern.
- Never introduce dark text on a dark background, low-contrast placeholder text, invisible focus states, clipped text, overlapping controls, or desktop-only layouts.
- Validate the generated Hugo output, not only the template source.
- Run the design checklist in `DESIGN-SPEC.md` for meaningful UI changes.

## Personal data and secrets are never public

This repository is public. Do not place personal data, secrets, credentials, authentication material, or private operational data in Git, generated public output, examples, logs, screenshots, tests, prompts, or commit messages.

Never commit or print:

- real student or teacher names, school email addresses, usernames, or identifiers
- user allowlists, invitation lists, account exports, or private CSV files
- passwords, password hashes, reset tokens, session tokens, API keys, webhook secrets, or OAuth secrets
- detailed loan history, private comments, device serial numbers, or other student-linked records

Use `example.invalid`, synthetic names, and clearly fake identifiers in examples. Keep local/private files ignored by `.gitignore`. If a file containing personal data is found, stop propagating it, avoid repeating the data in chat or logs, remove it from the working tree, and report that Git history may need cleanup. Do not assume `.gitignore` removes data already committed.

Password rules:

- Passwords must be collected only by a protected application flow and hashed server-side with a password-specific algorithm such as Argon2id or bcrypt.
- Never store passwords or password hashes in Markdown, CSV, frontend JavaScript, browser local storage, logs, or Git.
- A client-side hash demonstration must be clearly separated from authentication and must never be used as the login credential.

## Data handling and privacy review

Before implementing authentication, imports, uploads, analytics, AI assistance, lending, or student tracking, identify what data is collected, where it is stored, who can access it, and whether it is public. Prefer data minimization and role-based access. Public Hugo pages may contain only deliberately public catalogue information.

When working with real data supplied by the user:

- do not echo it back or include it in tool output unnecessarily
- do not copy it into repository files or test fixtures
- use placeholders while developing
- keep private data outside the repository and outside generated Hugo output
- validate ignore rules with `git check-ignore` before creating local files

## Required validation

After changes, run the narrowest relevant checks available. For frontend changes, run `hugo --minify` and inspect generated output. For data or privacy changes, run `git diff --check`, inspect tracked files, and verify that private paths are ignored. Do not claim a privacy property without checking the relevant Git history or generated output.

When an operation requires `sudo`, a force-push, history rewriting, external service configuration, or access to secrets, explain the impact and ask the user to perform or explicitly confirm the operation.
