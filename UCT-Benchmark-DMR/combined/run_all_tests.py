#!/usr/bin/env python3
"""
Comprehensive Test Runner for UCT-Benchmark-DMR
================================================
Runs all test categories sequentially, captures results per category,
and prints a summary table with pass/fail status.

Exit code 0 = Categories 1-4 all pass (pipeline safe)
Exit code 1 = Any category 1-4 failure (regression detected)
Category 5 (UCTP Lab) failures are reported but don't affect exit code.
"""

import subprocess
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).resolve().parent

CATEGORIES = [
    {
        "number": 1,
        "name": "Core Pipeline Integrity",
        "critical": True,
        "tests": [
            "tests/test_pipeline_integration.py",
            "tests/test_database.py",
            "tests/test_database_integration.py",
            "tests/test_evaluation.py",
            "tests/test_track_binning.py",
            "tests/test_dataset_config.py",
        ],
    },
    {
        "number": 2,
        "name": "Data Processing & Simulation",
        "critical": True,
        "tests": [
            "tests/test_downsampling_enhancements.py",
            "tests/test_simulation_enhancements.py",
            "tests/test_simulation_full.py",
            "tests/test_search_strategies.py",
        ],
    },
    {
        "number": 3,
        "name": "API & Data Sources",
        "critical": True,
        "tests": [
            "tests/test_api_enhancements.py",
            "tests/test_open_sources.py",
            "tests/test_open_source_integration.py",
            "tests/test_data_source_manager.py",
        ],
    },
    {
        "number": 4,
        "name": "Backend API",
        "critical": True,
        "tests": [
            "backend_api/tests/test_datasets.py",
            "backend_api/tests/test_dataset_pipeline.py",
            "backend_api/tests/test_workers.py",
            "backend_api/tests/test_jobs.py",
            "backend_api/tests/test_submissions.py",
            "backend_api/tests/test_results.py",
            "backend_api/tests/test_leaderboard.py",
            "backend_api/tests/test_integration.py",
        ],
    },
    {
        "number": 5,
        "name": "New UCTP Lab",
        "critical": False,
        "tests": [
            "tests/test_uctp_lab_pipeline.py",
            "tests/test_uctp_lab_clustering.py",
            "tests/test_uctp_lab_connectivity.py",
        ],
    },
]

# --------------------------------------------------------------------------- #
# ANSI colours (degrade gracefully on Windows without VT support)
# --------------------------------------------------------------------------- #

try:
    # Enable ANSI escape sequences on Windows 10+
    import os
    os.system("")  # noqa: S605 – triggers VT100 mode on Windows
except Exception:
    pass

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def colour(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"


# --------------------------------------------------------------------------- #
# Pytest output parsing
# --------------------------------------------------------------------------- #

def parse_pytest_output(output: str):
    """Extract passed/failed/error counts and failed test names from pytest output."""
    passed = failed = errors = 0
    failed_tests: list[str] = []

    for line in output.splitlines():
        # Collect FAILED lines like "FAILED tests/test_foo.py::test_bar - ..."
        stripped = line.strip()
        if stripped.startswith("FAILED "):
            failed_tests.append(stripped.split(" ")[1].split(" - ")[0] if " - " in stripped else stripped[7:])

    # Parse the summary line, e.g. "3 passed, 1 failed, 1 error in 2.34s"
    for line in reversed(output.splitlines()):
        lower = line.lower()
        if "passed" in lower or "failed" in lower or "error" in lower:
            parts = lower.replace("=", "").strip().split(",")
            for part in parts:
                part = part.strip()
                tokens = part.split()
                if len(tokens) >= 2:
                    try:
                        count = int(tokens[0])
                    except ValueError:
                        continue
                    label = tokens[1]
                    if "passed" in label:
                        passed = count
                    elif "failed" in label:
                        failed = count
                    elif "error" in label:
                        errors = count
            break

    return passed, failed, errors, failed_tests


# --------------------------------------------------------------------------- #
# Run one category
# --------------------------------------------------------------------------- #

def run_category(category: dict) -> dict:
    """Run all tests in a category and return results."""
    num = category["number"]
    name = category["name"]
    test_files = category["tests"]

    # Verify test files exist
    missing = [t for t in test_files if not (BASE_DIR / t).exists()]
    if missing:
        print(colour(f"  WARNING: Missing test files: {missing}", YELLOW))

    existing = [t for t in test_files if (BASE_DIR / t).exists()]
    if not existing:
        return {
            "number": num,
            "name": name,
            "critical": category["critical"],
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "failed_tests": [],
            "returncode": 1,
            "elapsed": 0.0,
            "skipped": True,
        }

    cmd = ["uv", "run", "pytest", "-v", "--tb=short", "--no-header"] + existing
    print(f"\n{'='*72}")
    print(colour(f"  Category {num}: {name}", CYAN + BOLD))
    print(f"  Running: {len(existing)} test file(s)")
    print(f"{'='*72}")

    start = time.monotonic()
    result = subprocess.run(
        cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
    )
    elapsed = time.monotonic() - start

    output = result.stdout + "\n" + result.stderr
    print(output)

    passed, failed, errors, failed_tests = parse_pytest_output(output)

    return {
        "number": num,
        "name": name,
        "critical": category["critical"],
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "failed_tests": failed_tests,
        "returncode": result.returncode,
        "elapsed": elapsed,
        "skipped": False,
    }


# --------------------------------------------------------------------------- #
# Summary
# --------------------------------------------------------------------------- #

def print_summary(results: list[dict]) -> bool:
    """Print summary table. Returns True if all critical categories passed."""
    print(f"\n\n{'='*72}")
    print(colour("  TEST SUMMARY", BOLD))
    print(f"{'='*72}\n")

    header = f"  {'Cat':>3}  {'Category':<30}  {'Passed':>6}  {'Failed':>6}  {'Errors':>6}  {'Time':>8}  {'Status':<10}"
    print(header)
    print(f"  {'-'*3}  {'-'*30}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*8}  {'-'*10}")

    all_critical_pass = True

    for r in results:
        if r["skipped"]:
            status = colour("SKIP", YELLOW)
        elif r["returncode"] == 0:
            status = colour("PASS", GREEN)
        else:
            status = colour("FAIL", RED)
            if r["critical"]:
                all_critical_pass = False

        critical_marker = "*" if r["critical"] else " "
        elapsed_str = f"{r['elapsed']:.1f}s"

        print(
            f"  {r['number']:>3}{critical_marker} {r['name']:<30}  {r['passed']:>6}  "
            f"{r['failed']:>6}  {r['errors']:>6}  {elapsed_str:>8}  {status}"
        )

    print(f"\n  * = critical category (affects exit code)\n")

    # Print failed test details
    any_failures = False
    for r in results:
        if r["failed_tests"]:
            if not any_failures:
                print(colour("  FAILED TESTS:", RED + BOLD))
                any_failures = True
            print(colour(f"    Category {r['number']} ({r['name']}):", RED))
            for t in r["failed_tests"]:
                print(f"      - {t}")

    if any_failures:
        print()

    # Overall verdict
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failed"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    total_time = sum(r["elapsed"] for r in results)

    print(f"  Total: {total_passed} passed, {total_failed} failed, {total_errors} errors in {total_time:.1f}s\n")

    if all_critical_pass:
        print(colour("  >>> PIPELINE SAFE - All critical categories passed <<<", GREEN + BOLD))
    else:
        print(colour("  >>> REGRESSION DETECTED - Critical category failure <<<", RED + BOLD))

    print()
    return all_critical_pass


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    print(colour("\n  UCT-Benchmark-DMR Comprehensive Test Runner", BOLD))
    print(f"  Base directory: {BASE_DIR}\n")

    results = []
    for category in CATEGORIES:
        result = run_category(category)
        results.append(result)

    pipeline_safe = print_summary(results)
    sys.exit(0 if pipeline_safe else 1)


if __name__ == "__main__":
    main()
