# Codex Delegation Policy

The user wants Codex to act as planner, reviewer, integrator, and overall owner, while delegating simple code edits to Claude Code whenever that saves Codex context.

## Claude Code Delegation

Use the user's DeepSeek-connected Claude Code setup for:

- Small, clearly scoped code edits.
- Mechanical fixes, formatting-conformant edits, or simple feature slices.
- Localized test additions or documentation updates.
- First-pass implementation when Codex already has a concrete plan and acceptance criteria.

Do not delegate:

- Destructive filesystem operations, disk cleanup, credential handling, or network/proxy repair.
- Ambiguous product/design decisions that need user judgment.
- Large refactors without first making a plan.
- Final verification or final user-facing claims.

Preferred command:

```powershell
claude-delegate "<task>" "<repo-or-workdir>"
```

If the current process has not refreshed PATH yet, use:

```powershell
& "$HOME\.codex\bin\claude-delegate.ps1" "<task>" "<repo-or-workdir>"
```

Codex responsibilities after every delegation:

- Inspect `git diff` or the changed files.
- Run or review targeted verification.
- Fix issues directly or send one focused follow-up to Claude.
- Summarize only the validated result to the user.

Claude task prompts should include:

- Exact files or feature area when known.
- Constraints and non-goals.
- Required verification command when known.
- Expected return format: summary, files changed, verification, risks.

## Frontend Visual Design

The user may use other APIs or tools to explore frontend visual polish because Codex's frontend aesthetics may not be the strongest fit.

Codex should still own:

- Product flow and information architecture.
- Frontend engineering structure.
- Accessibility, responsiveness, performance, and integration correctness.
- Reviewing and adapting externally generated UI code before it enters the main project.

When external UI code or designs are provided, Codex should treat them as draft input, then review for maintainability, consistency, security, and integration with the app architecture.

## Issue Tracking & Competition Reporting

Every issue discovered by the user or Codex must be written down and tracked to resolution. This is mandatory material for the final competition report.

- Log each issue in a dedicated tracking file (e.g., `docs/issues.md`), including: discovery date, description, severity, and the initial state.
- When an issue is resolved, record the root cause, the fix applied, and the verified outcome. Do not delete or overwrite the original entry; append the resolution.
- If an issue is intentionally deferred (won't-fix), note the reason and the trade-off accepted.

This ensures the final report has a complete, auditable trail of problems found, decisions made, and solutions converged.

## Knowledge Graph Persistence

The local Obsidian knowledge graph under `knowledge-graph/` is the user's study and project-memory vault. It is intentionally Git-ignored and should stay isolated from the public repository unless the user explicitly changes that policy.

- After every meaningful optimization, design correction, or problem-resolution cycle, add a short note or update the relevant existing note in `knowledge-graph/`.
- Engineering issues still belong first in `docs/issues.md`; the knowledge graph should capture the reusable learning, decision, and report material.
- Realtime/API/model lessons should update `knowledge-graph/04-概念卡/实时语音链路.md` or a related concept card.
- Interview behavior, scoring, report, and ability-tree lessons should update the corresponding notes under `knowledge-graph/02-面试问答/` or `knowledge-graph/04-概念卡/`.
- Keep knowledge graph notes readable in Obsidian with wikilinks and concise frontmatter.

## Project Ownership

Codex remains responsible for:

- Architecture and module boundaries.
- API contracts and realtime conversation flow.
- Integration with Alibaba Bailian APIs.
- RAG, Function Calling, scoring, and ability-tree design.
- Final verification and user-facing status.
