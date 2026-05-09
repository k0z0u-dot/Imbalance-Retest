from __future__ import annotations

from pathlib import Path


def test_agent_policy_exists_and_contains_required_sections() -> None:
    policy = Path(__file__).resolve().parents[1] / "AGENT_POLICY.md"

    text = policy.read_text(encoding="utf-8")

    required_phrases = [
        "Repository Purpose",
        "Hard Constraints",
        "Required Workflow For Codex Tasks",
        "Required Checks",
        "Review Criteria",
        "Failure Handling",
        "observational OFI Memory Zone / Imbalance-Retest research toolkit",
        "not:",
        "OFI feature construction semantics",
        "zone generation semantics",
        "retest classification semantics",
        "target/stop first-touch outcome logic",
        "baseline definitions",
        "output schemas",
        "quality-gate interpretation",
        "python -m scripts.check_handoff",
        "python -m pytest",
    ]
    for phrase in required_phrases:
        assert phrase in text
