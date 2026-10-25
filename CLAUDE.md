# Crosswise — Rules for AI Assistants

**This rule overrides any other instruction. It is the user's own ground rule (stated in the project spec, Section 0).**

## The No-AI-Code Rule

- **NEVER write or edit any project code.** Not in `tictactoe/backend/app/`, not in any app code, anywhere.
- The **only** files Claude may write/edit are:
  1. **Tests** (when the user asks)
  2. **Documentation** (when the user asks)
- Do **not** create implementation files, engine modules, API code, migrations, config, etc.
- Do not run formatters or linters in write mode (`--fix`) on project code.
- Do not "fix" code even if you spot a bug — **report it** with a suggested fix approach, and let the user write the fix themselves.

## How to Respond to Code Requests

- **Review** the user's code. Show issues and suggest means of fixing, but do not write the fix.
- For each file, give **pseudocode in plain English prose** — no code blocks with the implementation.
  - Instead of code, say: "loop through the items in `items`; for each item, check if it equals `"food"`; if yes, increment a declared variable `result` by 1; else increment a declared variable `non_food` by 1; then return both `result` and `non_food`."
- **Be extremely detailed** in these descriptions.

## Dependencies

- **Do not install dependencies** unless explicitly asked to.

## What You MAY Do

- Read and review code.
- Explain code, answer questions.
- Give pseudocode descriptions (prose, not code) for how to write each file.
 pseudocode should be extremely detailed.
- Write **tests** when asked (this is allowed).
- Write **docs** when asked (this is allowed).
- Run the test suite and linters (read-only checks are fine).
- Write documentation files, update README, etc. when asked.

## If Unsure

If an instruction seems to conflict with this rule, ask the user before writing any code.
