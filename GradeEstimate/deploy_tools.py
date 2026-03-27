from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import webbrowser
from pathlib import Path

from release_tools import generate_release_assets


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, output.strip()


def _has_staged_changes(repo_root: Path) -> bool:
    code, _ = _run(["git", "diff", "--cached", "--quiet"], cwd=repo_root)
    return code != 0


def _has_worktree_changes(repo_root: Path, target_dir: str = "GradeEstimate") -> bool:
    code, out = _run(["git", "status", "--short", "--", target_dir], cwd=repo_root)
    return code == 0 and bool(out.strip())


def one_click_deploy(
    project_dir: Path,
    remote: str = "xjtlu-marks",
    branch: str = "master",
    app_url: str = "",
    auto_release: bool = True,
    bump: str = "patch",
    dry_run: bool = False,
) -> dict:
    repo_root = project_dir.parent
    run_log: list[str] = []

    preflight = ["python", "GradeEstimate/preflight_check.py"]
    if dry_run:
        run_log.append(f"[DRY RUN] {' '.join(preflight)}")
        preflight_ok = True
    else:
        code, out = _run(preflight, cwd=repo_root)
        run_log.append(out)
        preflight_ok = code == 0

    if not preflight_ok:
        return {
            "ok": False,
            "message": "Preflight failed. Deployment aborted.",
            "log": "\n\n".join(run_log),
        }

    release_info = None
    if auto_release:
        if dry_run:
            run_log.append(f"[DRY RUN] generate_release_assets(bump={bump})")
        else:
            release_info = generate_release_assets(project_dir, bump=bump)
            run_log.append(f"Release generated: version {release_info['version']}")

    if dry_run:
        run_log.append("[DRY RUN] git add GradeEstimate")
    else:
        code, out = _run(["git", "add", "GradeEstimate"], cwd=repo_root)
        if out:
            run_log.append(out)
        if code != 0:
            return {"ok": False, "message": "git add failed", "log": "\n\n".join(run_log)}

    commit_made = False
    if dry_run:
        if _has_worktree_changes(repo_root):
            msg = f"chore: one-click deploy {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            run_log.append(f"[DRY RUN] git commit -m \"{msg}\"")
            commit_made = True
    else:
        if _has_staged_changes(repo_root):
            msg = f"chore: one-click deploy {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            code, out = _run(["git", "commit", "-m", msg], cwd=repo_root)
            if out:
                run_log.append(out)
            if code != 0:
                return {"ok": False, "message": "git commit failed", "log": "\n\n".join(run_log)}
            commit_made = True
        else:
            run_log.append("No staged changes. Skip commit.")

    push_cmd = ["git", "push", remote, branch]
    if dry_run:
        run_log.append(f"[DRY RUN] {' '.join(push_cmd)}")
    else:
        code, out = _run(push_cmd, cwd=repo_root)
        if out:
            run_log.append(out)
        if code != 0:
            return {"ok": False, "message": "git push failed", "log": "\n\n".join(run_log)}

    if app_url.strip() and not dry_run:
        webbrowser.open(app_url.strip())
        run_log.append(f"Opened app URL: {app_url.strip()}")

    note = ""
    if not app_url.strip():
        note = (
            "Cloud app URL not set. If this is first deployment, bind repository in "
            "Streamlit Community Cloud manually once."
        )

    return {
        "ok": True,
        "message": "One-click deploy finished.",
        "commit_made": commit_made,
        "release": release_info,
        "note": note,
        "log": "\n\n".join(run_log),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="One-click deploy for GradeEstimate")
    parser.add_argument("--remote", default="xjtlu-marks")
    parser.add_argument("--branch", default="master")
    parser.add_argument("--app-url", default="")
    parser.add_argument("--bump", default="patch", choices=["patch", "minor", "major"])
    parser.add_argument("--no-release", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parent
    result = one_click_deploy(
        project_dir=project_dir,
        remote=args.remote,
        branch=args.branch,
        app_url=args.app_url,
        auto_release=not args.no_release,
        bump=args.bump,
        dry_run=args.dry_run,
    )

    print(result["message"])
    if result.get("note"):
        print(result["note"])
    print(result["log"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
