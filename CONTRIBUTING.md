# Contributing to Guardia AI

Thanks for contributing to Guardia AI.

This document defines a lightweight workflow so we can move fast while keeping quality high.

## Scope and Current Status
The current repository contains planning and backend support files. As the full backend and frontend folders are added, this process still applies.

## Development Workflow
1. Create a branch from main.
2. Make focused changes.
3. Validate locally.
4. Open a pull request with clear notes.

## Branch Naming
Use one of these prefixes:
- feat/<short-description>
- fix/<short-description>
- docs/<short-description>
- chore/<short-description>
- test/<short-description>

Examples:
- feat/fusion-controller-thresholds
- fix/websocket-reconnect-loop
- docs/readme-demo-assets

## Commit Message Convention
Use simple conventional-style prefixes:
- feat: Add Gemini analysis fallback handling
- fix: Prevent empty attribution serialization
- docs: Update API highlights and setup notes
- test: Add analytics summary endpoint tests
- chore: Clean lint and type hints

## Pull Request Checklist
Before opening a PR, confirm all items:
- [ ] Branch is up to date with main
- [ ] Change is scoped and intentional
- [ ] No sensitive keys, tokens, or secrets committed
- [ ] README/docs updated if behavior changed
- [ ] Manual validation completed
- [ ] Screenshots or GIFs added for UI changes
- [ ] API examples added for endpoint changes

## Testing Guidance
At minimum, run relevant checks for changed areas.

Suggested checks:
- Backend:
  - Endpoint sanity checks via curl or HTTP client
  - Validation checks for schema changes
  - WebSocket connect and alert event smoke test
- Frontend (when present in repo):
  - Basic page load and navigation
  - Live alert list rendering
  - Responsive layout sanity check

## Security and Secrets
Never commit:
- .env files with real values
- API keys
- Access tokens
- Credentials in code snippets

Use placeholders in docs and examples.

## Documentation Expectations
Update docs when you change:
- API routes
- Request/response shape
- Setup steps
- Environment variables
- Architecture assumptions

## Code Review Expectations
PRs should be easy to review:
- Keep changes focused
- Explain why the change was made
- Include before/after behavior in PR description

## Getting Help
If unsure about architecture or scope, open a draft PR early and ask for direction in the description.
