from __future__ import annotations

from pathlib import Path


def test_ci_workflow_runs_handoff_full_pytest_and_batch_smoke() -> None:
    workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"

    text = workflow.read_text(encoding="utf-8")

    assert "branches: [main]" in text
    assert "pull_request:" in text
    assert 'python-version: "3.11"' in text
    assert "python -m scripts.check_handoff" in text
    assert "python -m pytest" in text
    assert "python -m scripts.run_ofi_experiment_batch" in text
    assert "data/ofi_synthetic.csv" in text
    assert "configs/ofi_loose.json" in text
