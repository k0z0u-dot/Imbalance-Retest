from __future__ import annotations

import subprocess

from scripts import check_handoff


def _write_required_files(root) -> None:
    for name in check_handoff.REQUIRED_FILES:
        (root / name).write_text("", encoding="utf-8")


def test_build_pytest_command_uses_quick_marker_by_default() -> None:
    command = check_handoff.build_pytest_command()

    assert command[1:] == ["-m", "pytest", "-m", "not integration"]


def test_build_pytest_command_supports_full_mode() -> None:
    command = check_handoff.build_pytest_command(full=True)

    assert command[1:] == ["-m", "pytest"]


def test_missing_required_file_returns_nonzero_without_running_pytest(tmp_path, monkeypatch) -> None:
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("", encoding="utf-8")

    def fail_if_called(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("pytest should not run when required files are missing")

    monkeypatch.setattr(check_handoff.subprocess, "run", fail_if_called)

    assert check_handoff.run_handoff_check(repo_root=tmp_path) == 1


def test_successful_handoff_check_runs_quick_pytest(tmp_path, monkeypatch) -> None:
    _write_required_files(tmp_path)
    calls = []

    def fake_run(command, cwd):  # noqa: ANN001
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(check_handoff.subprocess, "run", fake_run)

    assert check_handoff.run_handoff_check(repo_root=tmp_path) == 0
    assert calls == [(check_handoff.build_pytest_command(), tmp_path.resolve())]


def test_failing_pytest_result_is_returned(tmp_path, monkeypatch) -> None:
    _write_required_files(tmp_path)

    def fake_run(command, cwd):  # noqa: ANN001
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(check_handoff.subprocess, "run", fake_run)

    assert check_handoff.run_handoff_check(repo_root=tmp_path) == 7
