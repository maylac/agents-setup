---
paths:
  - "**/*.{js,jsx,ts,tsx,mjs,cjs,py,go,rs,java,kt,kts,swift,c,cc,cpp,h,hpp,cs,php,rb,scala,dart,sql,sh,bash,zsh,fish,html,css,scss,json,yaml,yml,toml,xml,env,ini,conf}"
description: Security checks for code, configuration, and secret-adjacent files.
---

# Security Guidelines

## Baseline Checks

Before completing security-relevant code or config changes, check for:
- hardcoded secrets, tokens, passwords, or private keys
- missing validation at untrusted input boundaries
- SQL or command injection risks
- unsafe HTML rendering or XSS exposure
- auth, authorization, or permission regressions
- sensitive details in user-facing errors or logs

Apply only the checks relevant to the changed surface. Do not invent unrelated security work.

## Secret Management

Never hardcode secrets in source code. Use the repository's existing secret mechanism, environment variables, or a secret manager. If a secret appears exposed, stop and call out the rotation requirement.

## Security Response

If a critical security issue is found, fix the immediate issue first, then check nearby code for the same pattern. Use a security reviewer agent when the surface area is broad or sensitive enough to justify a second pass.
