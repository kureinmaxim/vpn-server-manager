# Support

## Docs

- [README](../README.md) — install, run, safety notes
- [BUILD.md](../BUILD.md) — Windows installer and macOS `.app` / `.dmg`
- [Monitoring](../docs/README_MONITORING_ru.md)
- [Changelog](../CHANGELOG.md)

## Common problems

### The app does not start

1. Python 3.13+ is required.
2. You need a `.env` file with `SECRET_KEY`. Create one with `python generate_key.py`.
3. Install dependencies: `python -m pip install -r requirements.txt`.

### Import fails

1. The encryption key must match the `.enc` file.
2. Use “Check key match” in Settings.
3. Confirm you are importing a `.enc` export from this app.

### Lost encryption key

Data cannot be recovered without the key. Keep a full export and the key in a safe place.

### PIN issues

Default template PIN is `1234`. Double-click the developer name to unlock. After a lockout, wait 30 seconds.

## Where to ask

- Questions and ideas: [Discussions](https://github.com/kureinmaxim/vpn-server-manager/discussions)
- Bugs and regressions: [Issues](https://github.com/kureinmaxim/vpn-server-manager/issues)
- Security: see [SECURITY.md](../SECURITY.md) — do not file a public issue

When you open an issue, include app version, OS, steps to reproduce, and what you expected.

## Contributing

Pull requests are welcome. Please keep changes focused, add tests when you touch behavior, and follow the PR template.
