# Security Policy

TrimGate is a security-auditing tool, so soundness defects (a real leak reported
as a pass, or a forgeable receipt) are treated as security issues.

## Reporting a vulnerability

Please report suspected vulnerabilities privately, **not** in a public issue:

- Use GitHub's **Report a vulnerability** button (Security Advisories) on this
  repository, or
- email the maintainer at mohamedazahrioui2006@gmail.com.

Include a description, affected version/commit, and a reproduction if possible.
You will get an acknowledgement within a few days. Please give a reasonable
window to fix before public disclosure.

## Scope

In scope: false-pass paths (a leak audited as clean), receipt forgery or
tampering that verifies, OData filter bypasses in the reference adapter,
fail-open behavior at the adapter or load boundary.

Out of scope (documented limitations, not vulnerabilities): policy shapes the
flat label model cannot express (deny rules, per-user grants), rerank/hybrid
retrieval leaks, and receipt authenticity without out-of-band key pinning. See
the README "Limitations" section.
