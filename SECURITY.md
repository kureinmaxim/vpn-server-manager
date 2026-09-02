# Security Policy

## Supported versions

Please report issues against the latest release on
[Releases](https://github.com/kureinmaxim/vpn-server-manager/releases).

## Reporting a vulnerability

Do **not** open a public issue for security problems.

Use [GitHub private vulnerability reporting](https://github.com/kureinmaxim/vpn-server-manager/security/advisories/new)
so the report stays private until a fix is ready.

Include:

- VPN Server Manager version
- OS
- What an attacker could do
- Steps or a minimal proof of concept

You should hear back within a few days. If the report is valid, a fix will be
prepared before any public disclosure.

## What this app stores

Server credentials live in a local Fernet-encrypted file. The `SECRET_KEY` in
`.env` is the only way to read them. There is no cloud sync and no key recovery.
Treat `.env` and full exports like a password database.
