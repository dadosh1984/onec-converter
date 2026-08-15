# Proposal — critical-high-priority-security

## Goal
Fix critical and high-priority security/correctness issues in onec-converter found by audit: 1. Replace input() with getpass() in cli.py:_resolve_secret (secret leak to shell history) 2. Add SSRF filter to HttpClient83 (block private/localhost IP ranges) 3. Add WAL atomicity to write_8x.py (prevent corruption on crash) 4. Improve jwt_auth.py: validate iat, nbf, jti; fix kid confusion (dont fallback to all secrets on unknown kid) 5. Close ThreadPoolExecutor in _run_timeout (thread leak) 6. Fix asyncio.run inside sync tool - use get_running_loop fallback 7. Fix field_is_pii in pii_scanner.py - word boundaries instead of substring 8. Fix _redact in audit.py - dont mask guid field 9. Fix WHERE parser in query.py - handle semicolons inside string literals

## Context

| Aspect | Value |
|--------|-------|
| Platform | any |
| Budget | compact |
| Constraints | none |

- **Lessons applied (v0.12):** find-bugs-and-improvement-suggestions-for-project-veridia:shield:9363a0a767f3, find-bugs-and-improvement-suggestions-for-project-veridia:shield:57848fcfb788, скилл-onec-converter-migration:forge:d89d5187918c, improve-orion-s-own-workflow-tooling-make-orion-draft-derive-mai:out:50f74a0c2da1, improve-orion-s-own-workflow-tooling-make-orion-draft-derive-mai:out:1dfadda6ba87
