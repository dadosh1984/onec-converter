# Tasks — critical-high-priority-security

- [x] [fact] 1. 🔴 Replace input() with getpass() in cli.py:_resolve_secret
- [x] [fact] 2. 🔴 Add SSRF filter to HttpClient83 (block private/localhost IP, scheme validation)
- [x] [fact] 3. 🔴 Add WAL atomicity to write_8x.py:append_records (write to .wal temp file, os.replace)
- [x] [fact] 4. 🟡 Improve jwt_auth.py: validate iat (not in future), nbf (not before), jti (replay), fix kid confusion (no fallback on unknown kid; legacy mode without kid still works)
- [x] [fact] 5. 🟡 Close ThreadPoolExecutor in _run_timeout via try/finally with shutdown(wait=False)
- [x] [fact] 6. 🟡 Fix asyncio.run inside sync tool — use get_running_loop() fallback
- [x] [fact] 7. 🟡 Fix field_is_pii in pii_scanner.py — word boundaries (\b), uppercase names
- [x] [fact] 8. 🟡 Fix _redact in audit.py — dont mask guid field
- [x] [fact] 9. 🟡 Fix WHERE parser in query.py — handle semicolons inside string literals (quote-aware split)
- [x] [fact] Verify: 65 related tests pass, 630/642 total pass (12 pre-existing failures unrelated to this change)
