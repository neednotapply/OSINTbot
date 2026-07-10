# Maintenance checklist

- Review upstream release notes and licensing before changing a pinned version.
- Update exactly one manifest revision or dependency pin at a time.
- Refresh sanitized parser fixtures for changed upstream output.
- Run pytest, Ruff, mypy, package build, and the maintenance verifier.
- Exercise setup and update from a clean checkout on Windows and Linux.
- Smoke-test `/help`, `/osint-status`, and every `/osint` category in a test guild.
- Confirm partial results survive a failed and a timed-out source.
- Confirm INFO logs contain metadata only; treat DEBUG logs as sensitive data.
- Inspect the Git tree after setup and verification; generated files must remain ignored.
