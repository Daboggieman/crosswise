# Frontend Engineering

## Purpose

Build reliable plain HTML, CSS, and JavaScript interfaces that follow the Crosswise frontend architecture.

## Project Stack

Plain HTML, CSS, and JavaScript served by FastAPI; no framework unless state gets painful.

## Operating Principles

1. Inspect the existing page structure before adding pages or components.
2. Reuse existing components and design primitives before creating duplicates.
3. Keep server/client boundaries deliberate.
4. Use explicit types where beneficial (Python typing conventions for backend, plain JS for frontend).
5. Keep UI state and server-state management straightforward — no React Query needed for plain JS.
6. Use consistent patterns for form validation and user input handling.
7. Validate user input on the client for UX but never rely on client validation for security.
8. Keep loading, empty, success, and error states explicit.
9. Do not introduce unnecessary client components.
10. Preserve responsive behavior.
11. Do not claim UI behavior without browser verification when the change is visual or interactive.

## Required Workflow

1. Inspect route and component architecture.
2. Identify reusable components and existing patterns.
3. Trace required API contracts.
4. Implement the smallest coherent UI change.
5. Run lint/test checks (ruff, pytest for backend; JS syntax checks for frontend).
6. Use Playwright for important interactive or visual behavior.
7. Verify responsive and failure states.
8. Review accessibility.
9. Inspect the final diff.

## Evidence Rules

Use the strongest available evidence in this order:

1. Runtime behavior
2. Automated test results
3. Type checking, linting, and build results
4. Installed package/source behavior
5. Official framework or library documentation
6. Repository configuration
7. Static code inspection
8. General model knowledge

Never report an assumption as a verified result.

## Tool Selection

- Use built-in file tools (Read/Glob/Grep) for repository exploration and file inspection.
- Use WebFetch/WebSearch when official documentation or public web resources need to be retrieved.
- Use Playwright or a browser tool for browser behavior and UI verification, when available.
- Use GitHub CLI for repository, branch, pull request, issue, workflow, and CI operations.
- Prefer the smallest tool set that establishes reliable evidence.

## Failure Handling

When something fails:

1. Reproduce the failure.
2. Capture the exact error.
3. Identify the failing layer.
4. Check whether the failure is environmental, dependency-related, configuration-related, or caused by application code.
5. Research uncertain behavior using authoritative sources.
6. Apply the smallest appropriate fix.
7. Reproduce the original failure again.
8. Run regression checks.
9. Inspect the final diff.

Do not hide failures by weakening tests, suppressing errors, deleting evidence, or claiming success without verification.

## Security

- Never expose secrets.
- Never commit credentials.
- Treat all external input as untrusted.
- Preserve authentication and authorization boundaries.
- Avoid leaking internal implementation details through errors.
- Review security implications whenever the skill touches users, data, credentials, networking, or deployment.

## Completion Criteria

A task using this skill is complete only when:

- The requested behavior is implemented.
- Existing project conventions are preserved.
- Relevant static checks pass.
- Relevant tests pass or their absence is explicitly reported.
- Browser verification is performed when the task affects user-facing behavior.
- Security implications have been considered.
- The final diff has been inspected.
- Verified facts are clearly distinguished from assumptions or remaining uncertainty.
