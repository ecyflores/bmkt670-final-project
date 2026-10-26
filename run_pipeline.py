"""Run the F1 extraction, transformation, database load, and quality checks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

STEPS = (
    ("Extract race results", PROJECT_ROOT / "etl" / "extract_jolpica_api.py", RAW_DIR),
    ("Extract historical weather", PROJECT_ROOT / "etl" / "extract_weather_api.py", RAW_DIR),
    ("Transform raw data", PROJECT_ROOT / "etl" / "transform.py", PROJECT_ROOT),
    ("Create/reset database schema", PROJECT_ROOT / "db_check.py", PROJECT_ROOT),
    ("Load clean tables", PROJECT_ROOT / "etl" / "load.py", PROJECT_ROOT),
    ("Run quality checks", PROJECT_ROOT / "etl" / "quality_checks.py", PROJECT_ROOT),
)


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    quality_check_failed = False

    for label, script, working_directory in STEPS:
        print(f"\n=== {label}: {script.relative_to(PROJECT_ROOT)} ===", flush=True)
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=working_directory,
            check=False,
        )
        if result.returncode == 0:
            continue

        if script.name == "quality_checks.py":
            quality_check_failed = True
            print(
                "\nQuality checks completed with failures. Review the reported checks.",
                flush=True,
            )
            continue

        print(f"\nStopped: {label} failed (exit code {result.returncode}).", flush=True)
        print("Fix the error and run `python run_pipeline.py` again.", flush=True)
        return result.returncode

    if quality_check_failed:
        print(
            "\nPipeline steps completed, but one or more quality checks failed.",
            flush=True,
        )
        return 1

    print("\nPipeline finished successfully.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())