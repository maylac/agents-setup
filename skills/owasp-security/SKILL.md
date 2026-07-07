---
name: owasp-security
description: Use when reviewing code for security vulnerabilities, implementing authentication/authorization, handling user input, or discussing web application security. Covers OWASP Top 10:2025, ASVS 5.0, and Agentic AI security (2026).
---

# OWASP Security Best Practices Skill

Apply these security standards when writing or reviewing code.

## Quick Reference: OWASP Top 10:2025

| # | Vulnerability | Key Prevention |
|---|---------------|----------------|
| A01 | Broken Access Control | Deny by default, enforce server-side, verify ownership |
| A02 | Security Misconfiguration | Harden configs, disable defaults, minimize features |
| A03 | Supply Chain Failures | Lock versions, verify integrity, audit dependencies |
| A04 | Cryptographic Failures | TLS 1.2+, AES-256-GCM, Argon2/bcrypt for passwords |
| A05 | Injection | Parameterized queries, input validation, safe APIs |
| A06 | Insecure Design | Threat model, rate limit, design security controls |
| A07 | Auth Failures | MFA, check breached passwords, secure sessions |
| A08 | Integrity Failures | Sign packages, SRI for CDN, safe serialization |
| A09 | Logging Failures | Log security events, structured format, alerting |
| A10 | Exception Handling | Fail-closed, hide internals, log with context |

## Security Code Review Checklist

When reviewing code, check for these issues:

### Input Handling
- [ ] All user input validated server-side
- [ ] Using parameterized queries (not string concatenation)
- [ ] Input length limits enforced
- [ ] Allowlist validation preferred over denylist

### Authentication & Sessions
- [ ] Passwords hashed with Argon2/bcrypt (not MD5/SHA1)
- [ ] Session tokens have sufficient entropy (128+ bits)
- [ ] Sessions invalidated on logout
- [ ] MFA available for sensitive operations

### Access Control
- [ ] Authorization checked on every request
- [ ] Using object references user cannot manipulate
- [ ] Deny by default policy
- [ ] Privilege escalation paths reviewed

### Data Protection
- [ ] Sensitive data encrypted at rest
- [ ] TLS for all data in transit
- [ ] No sensitive data in URLs/logs
- [ ] Secrets in environment/vault (not code)

### Error Handling
- [ ] No stack traces exposed to users
- [ ] Fail-closed on errors (deny, not allow)
- [ ] All exceptions logged with context
- [ ] Consistent error responses (no enumeration)

## Secure Code Patterns

### SQL Injection Prevention
```python
# UNSAFE
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# SAFE
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### Command Injection Prevention
```python
# UNSAFE
os.system(f"convert {filename} output.png")

# SAFE
subprocess.run(["convert", filename, "output.png"], shell=False)
```

### Password Storage
```python
# UNSAFE
hashlib.md5(password.encode()).hexdigest()

# SAFE
from argon2 import PasswordHasher
PasswordHasher().hash(password)
```

### Access Control
```python
# UNSAFE - No authorization check
@app.route('/api/user/<user_id>')
def get_user(user_id):
    return db.get_user(user_id)

# SAFE - Authorization enforced
@app.route('/api/user/<user_id>')
@login_required
def get_user(user_id):
    if current_user.id != user_id and not current_user.is_admin:
        abort(403)
    return db.get_user(user_id)
```

### Error Handling
```python
# UNSAFE - Exposes internals
@app.errorhandler(Exception)
def handle_error(e):
    return str(e), 500

# SAFE - Fail-closed, log context
@app.errorhandler(Exception)
def handle_error(e):
    error_id = uuid.uuid4()
    logger.exception(f"Error {error_id}: {e}")
    return {"error": "An error occurred", "id": str(error_id)}, 500
```

### Fail-Closed Pattern
```python
# UNSAFE - Fail-open
def check_permission(user, resource):
    try:
        return auth_service.check(user, resource)
    except Exception:
        return True  # DANGEROUS!

# SAFE - Fail-closed
def check_permission(user, resource):
    try:
        return auth_service.check(user, resource)
    except Exception as e:
        logger.error(f"Auth check failed: {e}")
        return False  # Deny on error
```

## Agentic AI Security (OWASP 2026)

When building or reviewing AI agent systems, check for:

| Risk | Description | Mitigation |
|------|-------------|------------|
| ASI01: Goal Hijack | Prompt injection alters agent objectives | Input sanitization, goal boundaries, behavioral monitoring |
| ASI02: Tool Misuse | Tools used in unintended ways | Least privilege, fine-grained permissions, validate I/O |
| ASI03: Privilege Abuse | Credential escalation across agents | Short-lived scoped tokens, identity verification |
| ASI04: Supply Chain | Compromised plugins/MCP servers | Verify signatures, sandbox, allowlist plugins |
| ASI05: Code Execution | Unsafe code generation/execution | Sandbox execution, static analysis, human approval |
| ASI06: Memory Poisoning | Corrupted RAG/context data | Validate stored content, segment by trust level |
| ASI07: Agent Comms | Spoofing between agents | Authenticate, encrypt, verify message integrity |
| ASI08: Cascading Failures | Errors propagate across systems | Circuit breakers, graceful degradation, isolation |
| ASI09: Trust Exploitation | Social engineering via AI | Label AI content, user education, verification steps |
| ASI10: Rogue Agents | Compromised agents acting maliciously | Behavior monitoring, kill switches, anomaly detection |

### Agent Security Checklist

- [ ] All agent inputs sanitized and validated
- [ ] Tools operate with minimum required permissions
- [ ] Credentials are short-lived and scoped
- [ ] Third-party plugins verified and sandboxed
- [ ] Code execution happens in isolated environments
- [ ] Agent communications authenticated and encrypted
- [ ] Circuit breakers between agent components
- [ ] Human approval for sensitive operations
- [ ] Behavior monitoring for anomaly detection
- [ ] Kill switch available for agent systems

## ASVS 5.0 Key Requirements

### Level 1 (All Applications)
- Passwords minimum 12 characters
- Check against breached password lists
- Rate limiting on authentication
- Session tokens 128+ bits entropy
- HTTPS everywhere

### Level 2 (Sensitive Data)
- All L1 requirements plus:
- MFA for sensitive operations
- Cryptographic key management
- Comprehensive security logging
- Input validation on all parameters

### Level 3 (Critical Systems)
- All L1/L2 requirements plus:
- Hardware security modules for keys
- Threat modeling documentation
- Advanced monitoring and alerting
- Penetration testing validation

## Language-Specific Security Quirks

Per-language injection/RCE/DoS quirks and safe patterns (Python, Ruby, Perl, Bash, Elixir, PowerShell, etc.) are in [references/language-risks.md](references/language-risks.md). Load it when reviewing code in a specific language.

## Deep Security Analysis Mindset

When reviewing any language, think like a senior security researcher:

1. **Memory Model:** How does the language handle memory? Managed vs manual? GC pauses exploitable?
2. **Type System:** Weak typing = type confusion attacks. Look for coercion exploits.
3. **Serialization:** Every language has its pickle/Marshal equivalent. All are dangerous.
4. **Concurrency:** Race conditions, TOCTOU, atomicity failures specific to the threading model.
5. **FFI Boundaries:** Native interop is where type safety breaks down.
6. **Standard Library:** Historic CVEs in std libs (Python urllib, Java XML, Ruby OpenSSL).
7. **Package Ecosystem:** Typosquatting, dependency confusion, malicious packages.
8. **Build System:** Makefile/gradle/npm script injection during builds.
9. **Runtime Behavior:** Debug vs release differences (Rust overflow, C++ assertions).
10. **Error Handling:** How does the language fail? Silently? With stack traces? Fail-open?

**For any language not listed:** Research its specific CWE patterns, CVE history, and known footguns. The examples above are entry points, not complete coverage.
