# Security

## Threat model (STRIDE summary)

- Spoofing: Halyk SSO OIDC with PKCE; JWT validated against issuer JWKS; no static API keys in web.
- Tampering: TLS 1.3 only; HSTS; signed CBS payloads; idempotency keys for POSTs.
- Repudiation: append-only audit log of all mortgage and auction actions (user_id, ts, hash chain).
- Information disclosure: PII (ИИН, доход) masked in logs; response field-level masking;
  encrypted at rest (Postgres TDE / managed disk encryption); short-lived presigned URLs for photos.
- Denial of service: per-user and per-IP rate limits; circuit breakers on integrations;
  Cloud WAF in front of LB.
- Elevation of privilege: scope-based authZ on every endpoint; principle of least privilege for
  service accounts; admin endpoints separated and IP-restricted.

## OWASP Top 10 checklist

| Risk                                | Mitigation                                                        |
|-------------------------------------|-------------------------------------------------------------------|
| A01 Broken Access Control           | Scope checks per route; row-level checks on user-owned resources. |
| A02 Cryptographic Failures          | TLS 1.3; AES-256 at rest; secrets in vault, never in code.        |
| A03 Injection                       | Pydantic validation; parameterized SQL; no shell exec on input.   |
| A04 Insecure Design                 | Threat model documented; security review per feature.             |
| A05 Security Misconfiguration       | Hardened base images; CSP, X-Frame-Options, Referrer-Policy.      |
| A06 Vulnerable Components           | Dependabot + Trivy in CI; pinned versions.                        |
| A07 Identification & Auth Failures  | Halyk SSO OIDC + PKCE; short-lived tokens; refresh rotation.      |
| A08 Software & Data Integrity       | Signed releases; SBOM; image digests pinned.                      |
| A09 Logging & Monitoring Failures   | Structured logs; alerting on auth anomalies; audit log immutable. |
| A10 SSRF                            | Egress allow-list; URL validation on integration adapters.        |

## Secrets

All secrets via environment / managed secret store. `.env.example` lists keys only.
No credentials in repository. Pre-commit hook (gitleaks) recommended.

## PII

ИИН и доход обрабатываются согласно требованиям ЗРК "О персональных данных и их защите".
Маскирование в логах: ИИН -> `XXXXXX******`; доход -> диапазоны.
