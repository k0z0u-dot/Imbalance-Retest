from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = ("AI_HANDOFF.md", "README.md", "pyproject.toml")


def build_pytest_command(*, full: bool = False) -> list[str]:
    command = [sys.executable, "-m", "pytest"]
    if not full:
        command.extend(["-m", "not integration"])
    return command


def find_missing_required_files(repo_root: Path) -> list[str]:
    return [name for name in REQUIRED_FILES if not (repo_root / name).is_file()]


def run_handoff_check(*, repo_root: Path, full: bool = False) -> int:
    repo_root = repo_root.resolve()
    missing = find_missing_required_files(repo_root)
    if missing:
        print("handoff check: FAIL", flush=True)
        print("missing required files:", flush=True)
        for name in missing:
            print(f"- {name}", flush=True)
        return 1

    mode = "full" if full else "quick"
    command = build_pytest_command(full=full)
    print(f"handoff check: required files OK ({', '.join(REQUIRED_FILES)})", flush=True)
    print(f"handoff check: running {mode} tests", flush=True)
    print(f"command: {' '.join(command)}", flush=True)

    result = subprocess.run(command, cwd=repo_root)
    if result.returncode != 0:
        print(f"handoff check: FAIL (pytest exited {result.returncode})", flush=True)
        return result.returncode

    print("handoff check: PASS", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the repository handoff sanity check.")
    parser.add_argument(
        "--full",
        action="store_true",
        help='Run "python -m pytest" instead of the quick non-integration test command.',
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    return run_handoff_check(repo_root=repo_root, full=args.full)


if __name__ == "__main__":
    raise SystemExit(main())
