# Design — фаза-36-0-19

## Overview
Deterministic plan derived from the proposal.

## Modules
- `src/tasks/*` — test-driven implementation units
- `tests/*` — RED-GREEN-REFACTOR test files

## Assumptions
- Scaffold project structure for фаза-36-0-19
- Build the CLI entry point (arg parsing, sub-commands, exit codes)
- Add format conversion: validation, edge cases, error reporting
- Add messages: command dispatch, conversation flow
- Cover the core capability with tests
- Document usage in README

## Verification
- [ ] lint (pnpm lint)
- [ ] type-check (tsc --noEmit)
- [ ] unit tests (pnpm test)
