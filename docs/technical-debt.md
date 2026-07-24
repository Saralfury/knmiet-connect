# Technical Debt

## Mandatory privileged-account 2FA

HOD, director, and administrator accounts still use password-only authentication.
Implement encrypted TOTP credentials, recovery codes, and a short-lived pre-authentication
token before issuing full session cookies. This was intentionally deferred from Phase 2 by
product decision on 2026-07-06 and must be completed before production deployment.
