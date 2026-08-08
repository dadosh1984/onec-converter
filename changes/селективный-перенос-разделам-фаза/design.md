# Design — селективный-перенос-разделам-фаза

## Overview
Deterministic plan derived from the proposal.

## Modules
- `src/tasks/*` — test-driven implementation units
- `tests/*` — RED-GREEN-REFACTOR test files

## Assumptions
- Scaffold project structure for селективный-перенос-разделам-фаза
- Build the CLI entry point (arg parsing, sub-commands, exit codes)
- Add format conversion: validation, edge cases, error reporting
- Add parsing: tokenizer/grammar, syntax errors
- Cover the core capability with tests
- Document usage in README

## Verification
- [ ] lint (pnpm lint)
- [ ] type-check (tsc --noEmit)
- [ ] unit tests (pnpm test)
