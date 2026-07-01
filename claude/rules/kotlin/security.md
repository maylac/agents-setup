---
paths:
  - "**/*.kt"
  - "**/*.kts"
---
# Kotlin Security

> This file extends [common/security.md](../common/security.md) with Kotlin and Android/KMP-specific content.

## Project Judgment Calls

- Never hardcode secrets; use `local.properties` (git-ignored) for local dev, `BuildConfig` fields from CI secrets for release, and `EncryptedSharedPreferences`/Keychain for runtime storage.
- Use HTTPS exclusively; block cleartext traffic; pin certificates for sensitive endpoints.
- Use parameterized queries for Room/SQLDelight — never concatenate user input into SQL.
- Store auth tokens in secure storage, not plain SharedPreferences; clear all auth state on logout.
- Test release builds with ProGuard/R8 enabled — obfuscation can silently break serialization.

## Reference

See skill: `owasp-security` for general web/application security guidelines.
