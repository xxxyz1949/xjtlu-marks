from __future__ import annotations

import datetime as dt
import subprocess
from pathlib import Path


def _read_version(version_file: Path) -> tuple[int, int, int]:
    if not version_file.exists():
        return (0, 0, 0)
    text = version_file.read_text(encoding="utf-8").strip()
    parts = text.split(".")
    if len(parts) != 3:
        return (0, 0, 0)
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        return (0, 0, 0)


def _bump(version: tuple[int, int, int], level: str) -> tuple[int, int, int]:
    major, minor, patch = version
    if level == "major":
        return (major + 1, 0, 0)
    if level == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def _git_log(repo_root: Path, max_count: int = 12) -> list[str]:
    cmd = ["git", "-C", str(repo_root), "log", f"--max-count={max_count}", "--pretty=format:%h %s"]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return ["(unable to read git log)"]
    output = proc.stdout or ""
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines or ["(no commit history)"]


def generate_release_assets(project_dir: Path, bump: str = "patch") -> dict:
    version_file = project_dir / "VERSION"
    changelog_file = project_dir / "CHANGELOG_SUMMARY.md"
    repo_root = project_dir.parent

    current = _read_version(version_file)
    new_version = _bump(current, bump)
    version_text = f"{new_version[0]}.{new_version[1]}.{new_version[2]}"
    version_file.write_text(version_text + "\n", encoding="utf-8")

    logs = _git_log(repo_root, max_count=12)
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    summary_lines = [
        "# Changelog Summary",
        "",
        f"Generated at: {now}",
        f"Version: {version_text}",
        "",
        "## Recent Commits",
    ]
    summary_lines.extend([f"- {line}" for line in logs])
    summary_lines.append("")
    changelog_file.write_text("\n".join(summary_lines), encoding="utf-8")

    return {
        "version": version_text,
        "version_file": str(version_file),
        "changelog_file": str(changelog_file),
        "commit_count": len(logs),
    }


def main() -> int:
    project_dir = Path(__file__).resolve().parent
    result = generate_release_assets(project_dir, bump="patch")
    print("Release assets generated")
    print(f"Version: {result['version']}")
    print(f"Version file: {result['version_file']}")
    print(f"Changelog file: {result['changelog_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
