# Security Policy

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

Email: **security@aumos.io**

Include:
- Description of the vulnerability and its potential impact
- Steps to reproduce
- Proof-of-concept code if applicable
- Your recommended fix

You will receive acknowledgment within **48 hours** and a detailed response within **5 business days**.

## Scope

In scope:
- API key exposure or leakage in SDK code, logs, or error messages
- Authentication bypass or credential handling flaws
- Unsafe deserialization or injection in SDK request/response handling
- Dependency vulnerabilities with a CVSS score >= 7.0

Out of scope:
- Vulnerabilities in the AumOS API server itself (report separately)
- Denial of service attacks
- Social engineering

## Response Timeline

| Stage | Timeline |
|-------|----------|
| Acknowledgment | Within 48 hours |
| Initial assessment | Within 5 business days |
| Fix deployment (critical) | Within 7 days |
| Fix deployment (high) | Within 30 days |
| Fix deployment (medium/low) | Next scheduled release |

## Security Best Practices for SDK Users

1. **Never hardcode API keys** — use environment variables or a secrets manager
2. **Rotate API keys regularly** — especially after team member offboarding
3. **Use the minimum required scopes** — request only the permissions your app needs
4. **Keep the SDK updated** — subscribe to release notifications for security patches
5. **Validate server certificates** — do not disable TLS verification in production
6. **Log carefully** — do not log the full request/response if it may contain sensitive data

## Dependency Security

All SDK dependencies are scanned on every CI run:

```bash
# Python
pip-audit

# Node.js
npm audit

# Go
govulncheck ./...

# Java
mvn dependency-check:check
```
