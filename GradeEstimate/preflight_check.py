from __future__ import annotations

import importlib
import sys
from pathlib import Path


REQUIRED_MODULES = ["streamlit", "numpy", "scipy", "matplotlib"]
LAST_REPORT_FILE = Path("GradeEstimate/.preflight_last.txt")
REQUIRED_FILES = [
    Path("GradeEstimate/app.py"),
    Path("GradeEstimate/analytics.py"),
    Path("GradeEstimate/rank_estimate.py"),
    Path("GradeEstimate/plot_visual.py"),
    Path("GradeEstimate/requirements.txt"),
    Path("GradeEstimate/pages/Cloud_Checklist.py"),
    Path("GradeEstimate/pages/Deployment_Error_Help.py"),
    Path("GradeEstimate/pages/Release_Center.py"),
]


def check_modules() -> list[str]:
    errors = []
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # pragma: no cover
            errors.append(f"[FAIL] module import: {module_name} -> {exc}")
    return errors


def check_files() -> list[str]:
    errors = []
    for path in REQUIRED_FILES:
        if not path.exists():
            errors.append(f"[FAIL] missing file: {path}")
    return errors


def check_entry_signature() -> list[str]:
    errors = []
    app_path = Path("GradeEstimate/app.py")
    if app_path.exists():
        text = app_path.read_text(encoding="utf-8")
        if "def main()" not in text:
            errors.append("[FAIL] app entry: def main() not found in GradeEstimate/app.py")
        if "if __name__ == \"__main__\"" not in text:
            errors.append("[FAIL] app entry: __main__ guard not found in GradeEstimate/app.py")
    return errors


def main() -> int:
    report_lines = ["== Preflight check for Streamlit deploy =="]
    print(report_lines[0])

    failures = []
    failures.extend(check_modules())
    failures.extend(check_files())
    failures.extend(check_entry_signature())

    if failures:
        for item in failures:
            print(item)
            report_lines.append(item)
        print("\nPreflight: FAILED")
        report_lines.append("")
        report_lines.append("Preflight: FAILED")
        LAST_REPORT_FILE.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        return 1

    print("[PASS] module imports")
    print("[PASS] required files")
    print("[PASS] app entry signature")
    print("\nPreflight: PASSED")
    report_lines.extend(
        [
            "[PASS] module imports",
            "[PASS] required files",
            "[PASS] app entry signature",
            "",
            "Preflight: PASSED",
        ]
    )
    LAST_REPORT_FILE.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
