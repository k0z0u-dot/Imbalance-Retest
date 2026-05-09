# Agent Policy

This document defines repository-level rules for ChatGPT, Codex, and any future
review or automation agent working on this repository.

Every agent must read this file and `AI_HANDOFF.md` before making changes.

## 1. Repository Purpose

This repository is an observational OFI Memory Zone / Imbalance-Retest research toolkit.
Its purpose is to detect order-flow-imbalance-derived zones, evaluate later
retests, compare the results against baselines, and report research quality.

This repository is not:

- an EA;
- a live trading bot;
- an order execution system;
- a position sizing system;
- a broker or exchange integration project.

## 2. Hard Constraints

Future agents must not change the following unless a GitHub Issue explicitly
asks for it:

- OFI feature construction semantics;
- zone generation semantics;
- retest classification semantics;
- target/stop first-touch outcome logic;
- baseline definitions;
- output schemas;
- quality-gate interpretation.

Agents must not add:

- live trading;
- broker or exchange integrations;
- order entry;
- position sizing;
- automated execution;
- portfolio or risk management.

## 3. Required Workflow For Codex Tasks

For each Issue-driven task:

1. Read the GitHub Issue.
2. Read `AI_HANDOFF.md`.
3. Read this `AGENT_POLICY.md`.
4. Inspect relevant files before editing.
5. Keep changes small and within scope.
6. Run the required checks.
7. Update `AI_HANDOFF.md`.
8. Push to `main` only after tests pass.
9. Report the latest commit SHA.

## 4. Required Checks

At minimum, run:

```bash
python -m scripts.check_handoff
python -m pytest
```

If a task touches the experiment batch or protocol path, also run an
appropriate batch smoke command.

If tests fail, do not broaden the implementation to make them pass. Stop,
record the failure in `AI_HANDOFF.md`, and report the blocker.

## 5. Review Criteria

ChatGPT and review agents should verify:

- scope control;
- no research-logic drift;
- no schema breakage;
- tests pass;
- docs match behavior;
- `AI_HANDOFF.md` is complete;
- CI is not made flaky or dependent on external data.

## 6. Failure Handling

If tests fail, required data is missing, or task scope is ambiguous, the agent
must stop and update `AI_HANDOFF.md` with:

- what was attempted;
- the exact failing command;
- the error or failing output summary;
- the files changed so far;
- the next question or decision needed.

Do not silently expand scope, change research semantics, or add trading-related
behavior to bypass a failure.
