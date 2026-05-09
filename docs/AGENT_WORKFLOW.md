# ChatGPT-Codex Development Workflow

This document describes the current semi-automated development loop used for
this repository. It is a coordination protocol for humans, ChatGPT, Codex,
GitHub, and GitHub Actions.

This workflow does not add automatic trading, automatic code execution by
Codex, or autonomous repository changes.

## Roles

| Role | Responsibility |
|---|---|
| ChatGPT | Helps turn user intent into scoped GitHub Issues, reviews results, checks handoff notes, and decides next tasks. |
| Codex | Reads Issues and repository policy, implements bounded changes, runs required checks, updates `AI_HANDOFF.md`, commits, pushes, and reports the commit SHA. |
| GitHub | Stores Issues, commits, repository files, and the audit trail for completed work. |
| GitHub Actions | Runs CI checks after pushes and pull requests. It verifies handoff, tests, and smoke workflows, but does not decide product or research direction. |

## Standard Loop

The standard loop is:

1. User and ChatGPT define a small task.
2. ChatGPT creates or drafts a GitHub Issue.
3. Codex reads the Issue, `AGENT_POLICY.md`, and `AI_HANDOFF.md`.
4. Codex inspects relevant files before editing.
5. Codex implements only the requested scope.
6. Codex runs required local checks.
7. Codex updates `AI_HANDOFF.md`.
8. Codex commits and pushes to `main` when tests pass.
9. Codex reports the latest commit SHA.
10. ChatGPT reviews the commit, handoff notes, and GitHub Actions status.
11. ChatGPT decides whether to close the Issue, request a follow-up, or open a new Issue.

Completion is tracked by commit SHA and `AI_HANDOFF.md`. If GitHub Issue close
or comment actions are unavailable, the commit and handoff file remain the
source of truth.

## Codex Preflight Checklist

Before editing, Codex should verify:

- the GitHub Issue has been read;
- `AGENT_POLICY.md` has been read;
- `AI_HANDOFF.md` has been read;
- the worktree state is known via `git status --short`;
- the current branch is known;
- relevant README, docs, scripts, source files, and tests have been inspected;
- the task does not require research logic, output schema, CI, or automation
  changes unless explicitly requested;
- the implementation plan is small and reversible.

## Codex Completion Checklist

Before reporting completion, Codex should verify:

- the requested files or behavior were implemented;
- no unrelated files were changed;
- no research logic changed unless explicitly requested;
- no output schema changed unless explicitly requested;
- no EA, trading, execution, broker, exchange, position sizing, or risk
  management behavior was added;
- `AI_HANDOFF.md` was updated with changed files, commands, test results,
  concerns, and next questions;
- required checks passed;
- changes were committed and pushed to `main` when the Issue requires it or the
  agent policy applies;
- the latest commit SHA was reported.

Required checks are defined in `AGENT_POLICY.md`. The default checks are:

```bash
python -m scripts.check_handoff
python -m pytest
```

Some tasks may also require:

```bash
python -m pytest -m "not integration"
python -m scripts.run_ofi_experiment_batch --input data/ofi_synthetic.csv --output-root output/smoke --config configs/ofi_loose.json
```

## ChatGPT Review Checklist

When reviewing a Codex completion, ChatGPT should check:

- the commit SHA exists on GitHub;
- `AI_HANDOFF.md` matches the completed work;
- README/docs changes match actual commands;
- tests listed in handoff were actually run;
- GitHub Actions passed or any failure is understood;
- no research logic changed outside the Issue scope;
- no output schema changed outside the Issue scope;
- no trading, execution, broker, exchange, position sizing, or risk management
  behavior was added;
- the Issue can be closed or needs a follow-up.

## Known GitHub Tool Limitations

Current GitHub tool behavior is useful but not perfectly reliable:

- Issue creation generally works.
- Repository, file, and commit reads work.
- Issue comments are unreliable.
- Issue close or update actions may be intermittent.
- If commenting or closing fails, completion should be tracked by the latest
  commit SHA plus the updated `AI_HANDOFF.md`.

Do not block implementation solely because an Issue comment or close action
fails. Record the completion evidence in the final response and handoff file.

## Safety Rules

All agents must follow [AGENT_POLICY.md](../AGENT_POLICY.md).

The most important safety rules are:

- keep tasks small and Issue-scoped;
- do not change research logic unless explicitly requested;
- do not change output schemas unless explicitly requested;
- do not add EA, trading, broker, exchange, execution, position sizing, or risk
  management behavior;
- do not add Codex auto-triggering or autonomous repository mutation unless a
  future Issue explicitly requests it;
- record failures and unresolved concerns in `AI_HANDOFF.md`.

This workflow is a human-reviewed semi-automated development loop, not an
autonomous development system.
