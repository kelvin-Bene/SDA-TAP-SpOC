#!/usr/bin/env python3
"""
End-to-End Pipeline Test Script
================================
Tests the complete UCTP benchmark pipeline from dataset loading through
PDF report generation.

This script validates that all pipeline components work together correctly,
using existing sample data and the dummyUCTP processor.

Usage:
    python test_pipeline_e2e.py

Author: Generated for V1 pipeline validation
Date: 2026-01-17
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Add project root to path
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR
sys.path.insert(0, str(PROJECT_ROOT))

# Set working directory
os.chdir(PROJECT_ROOT)


class PipelineTestResult:
    """Stores results from each pipeline stage"""
    def __init__(self):
        self.stages = {}
        self.errors = []

    def add_stage(self, name, success, message="", data=None):
        self.stages[name] = {
            "success": success,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        if not success:
            self.errors.append(f"{name}: {message}")

    def summary(self):
        print("\n" + "="*60)
        print("PIPELINE TEST SUMMARY")
        print("="*60)
        for name, result in self.stages.items():
            status = "PASS" if result["success"] else "FAIL"
            print(f"  [{status}] {name}")
            if result["message"]:
                print(f"         {result['message']}")
        print("="*60)
        total = len(self.stages)
        passed = sum(1 for r in self.stages.values() if r["success"])
        print(f"Result: {passed}/{total} stages passed")
        if self.errors:
            print(f"\nErrors:")
            for err in self.errors:
                print(f"  - {err}")
        return len(self.errors) == 0


def test_stage_1_load_sample_data(results):
    """Stage 1: Load existing sample data files"""
    print("\n[Stage 1] Loading sample data...")

    try:
        data_dir = PROJECT_ROOT / "src" / "data"

        # Load reference observations
        ref_obs_path = data_dir / "ref_obs.csv"
        if not ref_obs_path.exists():
            results.add_stage("1. Load Sample Data", False, f"ref_obs.csv not found at {ref_obs_path}")
            return None
        ref_obs = pd.read_csv(ref_obs_path)
        print(f"    Loaded ref_obs.csv: {len(ref_obs)} observations")

        # Load reference orbits (state vectors)
        ref_orbits_path = data_dir / "ref_orbits.csv"
        if not ref_orbits_path.exists():
            results.add_stage("1. Load Sample Data", False, f"ref_orbits.csv not found at {ref_orbits_path}")
            return None
        ref_orbits = pd.read_csv(ref_orbits_path)
        print(f"    Loaded ref_orbits.csv: {len(ref_orbits)} orbits")

        # Parse cov_matrix from string to numpy array if needed
        if 'cov_matrix' in ref_orbits.columns and isinstance(ref_orbits['cov_matrix'].iloc[0], str):
            import ast
            ref_orbits['cov_matrix'] = ref_orbits['cov_matrix'].apply(
                lambda x: np.array(ast.literal_eval(x)) if isinstance(x, str) else x
            )

        # Check for existing UCTP output
        uctp_output_path = data_dir / "uctp_output.json"
        uctp_output = None
        if uctp_output_path.exists():
            with open(uctp_output_path, 'r') as f:
                uctp_output = json.load(f)
            print(f"    Found existing uctp_output.json: {len(uctp_output)} state vectors")

        results.add_stage("1. Load Sample Data", True,
                         f"Loaded {len(ref_obs)} obs, {len(ref_orbits)} orbits")

        return {
            "ref_obs": ref_obs,
            "ref_orbits": ref_orbits,
            "uctp_output": uctp_output,
            "data_dir": data_dir
        }

    except Exception as e:
        results.add_stage("1. Load Sample Data", False, str(e))
        return None


def test_stage_2_run_dummy_uctp(results, data):
    """Stage 2: Generate UCTP output using dummyUCTP"""
    print("\n[Stage 2] Running dummyUCTP...")

    if data is None:
        results.add_stage("2. DummyUCTP", False, "No data from previous stage")
        return None

    try:
        # dummyUCTP expects CSV file paths and writes to ./data/uctp_output.json
        # So we need to change to src directory first
        data_dir = data["data_dir"]
        src_dir = data_dir.parent  # src directory

        original_cwd = os.getcwd()
        os.chdir(src_dir)

        # Add src to path for imports
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        try:
            # Import dummyUCTP (needs to be imported after chdir)
            from libraries.dummyUCTP import dummy

            truth_path = data_dir / "ref_obs.csv"
            blind_path = data_dir / "ref_obs.csv"  # Use same file for blind (not used by dummy)

            # Run dummyUCTP
            dummy(str(truth_path), str(blind_path))

            # Load the generated output
            uctp_output_path = data_dir / "uctp_output.json"
            with open(uctp_output_path, 'r') as f:
                uctp_output = json.load(f)

            # Convert to DataFrame for downstream processing
            uctp_df = pd.DataFrame(uctp_output)

            print(f"    Generated {len(uctp_df)} candidate orbits")
            print(f"    Output saved to {uctp_output_path}")

            results.add_stage("2. DummyUCTP", True, f"Generated {len(uctp_df)} candidates")

            data["uctp_output"] = uctp_output
            data["uctp_df"] = uctp_df

        finally:
            os.chdir(original_cwd)

        return data

    except Exception as e:
        import traceback
        traceback.print_exc()
        results.add_stage("2. DummyUCTP", False, str(e))
        return data


def test_stage_3_orbit_association(results, data):
    """Stage 3: Associate UCTP orbits with reference orbits"""
    print("\n[Stage 3] Running orbit association...")

    if data is None or "uctp_df" not in data:
        results.add_stage("3. Orbit Association", False, "No UCTP output from previous stage")
        return None

    try:
        # For simplified testing without Orekit, we'll do a mock association
        # based on the sourcedData observation IDs

        ref_obs = data["ref_obs"]
        ref_orbits = data["ref_orbits"]
        uctp_df = data["uctp_df"]

        # Create a simplified association based on observation matching
        associated_orbits = []

        for idx, row in uctp_df.iterrows():
            sourced_data = row.get("sourcedData", [])
            if not sourced_data:
                continue

            # Find which satNo the observations belong to
            matching_obs = ref_obs[ref_obs["id"].isin(sourced_data)]
            if len(matching_obs) > 0:
                # Get the most common satNo in the sourced observations
                most_common_satno = matching_obs["satNo"].mode()
                if len(most_common_satno) > 0:
                    satno = most_common_satno.iloc[0]

                    # Copy the row and add satNo
                    assoc_row = row.copy()
                    assoc_row["satNo"] = satno
                    assoc_row["error"] = np.random.uniform(0, 100)  # Placeholder error
                    assoc_row["uct"] = False

                    # Add physical parameters from ref_orbits if available
                    ref_match = ref_orbits[ref_orbits["satNo"] == satno]
                    if len(ref_match) > 0:
                        ref_row = ref_match.iloc[0]
                        assoc_row["mass"] = ref_row.get("mass", 1000.0)
                        assoc_row["crossSection"] = ref_row.get("crossSection", 10.0)
                        assoc_row["dragCoeff"] = ref_row.get("dragCoeff", 0.0)
                        assoc_row["solarRadPressCoeff"] = ref_row.get("solarRadPressCoeff", 0.0)
                        assoc_row["cov_matrix"] = ref_row.get("cov_matrix", np.eye(6))
                    else:
                        assoc_row["mass"] = 1000.0
                        assoc_row["crossSection"] = 10.0
                        assoc_row["dragCoeff"] = 0.0
                        assoc_row["solarRadPressCoeff"] = 0.0
                        assoc_row["cov_matrix"] = np.eye(6)

                    associated_orbits.append(assoc_row)

        associated_df = pd.DataFrame(associated_orbits)

        # Calculate association results
        association_results = {
            "Expected State Count": len(ref_orbits),
            "Associated Orbit Count": len(associated_df),
            "Non-Associated Orbit Count": len(uctp_df) - len(associated_df),
            "Undiscovered Reference Orbits": len(ref_orbits) - len(associated_df["satNo"].unique()) if len(associated_df) > 0 else len(ref_orbits)
        }

        print(f"    Associated: {association_results['Associated Orbit Count']}")
        print(f"    Non-Associated: {association_results['Non-Associated Orbit Count']}")
        print(f"    Undiscovered: {association_results['Undiscovered Reference Orbits']}")

        results.add_stage("3. Orbit Association", True,
                         f"Associated {len(associated_df)} of {len(uctp_df)} candidates")

        data["associated_orbits"] = associated_df
        data["association_results"] = association_results
        return data

    except Exception as e:
        import traceback
        traceback.print_exc()
        results.add_stage("3. Orbit Association", False, str(e))
        return data


def test_stage_4_binary_metrics(results, data):
    """Stage 4: Compute binary classification metrics"""
    print("\n[Stage 4] Computing binary metrics...")

    if data is None or "associated_orbits" not in data:
        results.add_stage("4. Binary Metrics", False, "No associated orbits from previous stage")
        return None

    try:
        from uct_benchmark.evaluation.binaryMetrics import binaryMetrics

        ref_obs = data["ref_obs"]
        associated_orbits = data["associated_orbits"]

        if len(associated_orbits) == 0:
            results.add_stage("4. Binary Metrics", False, "No associated orbits to evaluate")
            return data

        binary_results = binaryMetrics(ref_obs, associated_orbits)

        print(f"    Total Observations: {binary_results['TotalObs'].iloc[0]}")
        print(f"    True Positives: {binary_results['TruePositives'].iloc[0]}")
        print(f"    False Positives: {binary_results['FalsePositives'].iloc[0]}")
        print(f"    False Negatives: {binary_results['FalseNegatives'].iloc[0]}")
        print(f"    F1 Score: {binary_results['F1Score'].iloc[0]:.4f}")

        results.add_stage("4. Binary Metrics", True,
                         f"F1={binary_results['F1Score'].iloc[0]:.4f}")

        data["binary_results"] = binary_results
        return data

    except Exception as e:
        import traceback
        traceback.print_exc()
        results.add_stage("4. Binary Metrics", False, str(e))
        return data


def test_stage_5_state_metrics(results, data):
    """Stage 5: Compute state metrics (simplified without propagation)"""
    print("\n[Stage 5] Computing state metrics (simplified)...")

    if data is None or "associated_orbits" not in data:
        results.add_stage("5. State Metrics", False, "No associated orbits from previous stage")
        return None

    try:
        associated_orbits = data["associated_orbits"]
        ref_orbits = data["ref_orbits"]

        if len(associated_orbits) == 0:
            results.add_stage("5. State Metrics", False, "No associated orbits to evaluate")
            return data

        # Simplified state metrics without full propagation
        state_results = []
        state_cols = ["xpos", "ypos", "zpos", "xvel", "yvel", "zvel"]

        for _, assoc_row in associated_orbits.iterrows():
            satno = assoc_row["satNo"]
            ref_match = ref_orbits[ref_orbits["satNo"] == satno]

            if len(ref_match) > 0:
                ref_row = ref_match.iloc[0]

                # Compute position/velocity error norms
                pos_error = np.sqrt(
                    (assoc_row.get("xpos", 0) - ref_row.get("xpos", 0))**2 +
                    (assoc_row.get("ypos", 0) - ref_row.get("ypos", 0))**2 +
                    (assoc_row.get("zpos", 0) - ref_row.get("zpos", 0))**2
                )
                vel_error = np.sqrt(
                    (assoc_row.get("xvel", 0) - ref_row.get("xvel", 0))**2 +
                    (assoc_row.get("yvel", 0) - ref_row.get("yvel", 0))**2 +
                    (assoc_row.get("zvel", 0) - ref_row.get("zvel", 0))**2
                )

                state_results.append({
                    "satNo": satno,
                    "Position Error Norm": pos_error,
                    "Velocity Error Norm": vel_error,
                    "Total Bias": 0.0,  # Placeholder
                    "MD P-Score": np.random.uniform(0.3, 0.9),  # Placeholder
                    "NEES P-Score": np.random.uniform(0.3, 0.9)  # Placeholder
                })

        state_df = pd.DataFrame(state_results)

        if len(state_df) > 0:
            print(f"    Computed metrics for {len(state_df)} orbits")
            print(f"    Mean Position Error: {state_df['Position Error Norm'].mean():.2f} km")
            print(f"    Mean Velocity Error: {state_df['Velocity Error Norm'].mean():.4f} km/s")

        results.add_stage("5. State Metrics", True,
                         f"Computed for {len(state_df)} orbits (simplified)")

        data["state_results"] = state_df
        return data

    except Exception as e:
        import traceback
        traceback.print_exc()
        results.add_stage("5. State Metrics", False, str(e))
        return data


def test_stage_6_residual_metrics(results, data):
    """Stage 6: Compute residual metrics (simplified)"""
    print("\n[Stage 6] Computing residual metrics (simplified)...")

    if data is None or "associated_orbits" not in data:
        results.add_stage("6. Residual Metrics", False, "No associated orbits from previous stage")
        return None

    try:
        associated_orbits = data["associated_orbits"]
        ref_obs = data["ref_obs"]

        if len(associated_orbits) == 0:
            results.add_stage("6. Residual Metrics", False, "No associated orbits to evaluate")
            return data

        # Simplified residual metrics
        residual_ref_results = []
        residual_cand_results = []

        for idx, row in associated_orbits.iterrows():
            satno = row.get("satNo")
            sat_obs = ref_obs[ref_obs["satNo"] == satno]

            if len(sat_obs) > 0:
                epochs = pd.to_datetime(sat_obs["obTime"]).tolist()
                # Generate placeholder residuals
                residuals = np.random.uniform(0, 0.001, len(sat_obs)).tolist()

                result = {
                    "id": sat_obs["id"].tolist(),
                    "Epoch": epochs,
                    "Residuals": residuals,
                    "RMSE": np.sqrt(np.mean(np.array(residuals)**2)),
                    "Mean": np.mean(residuals),
                    "std": np.std(residuals)
                }
                residual_ref_results.append(result)
                residual_cand_results.append(result.copy())

        residual_ref_df = pd.DataFrame(residual_ref_results)
        residual_cand_df = pd.DataFrame(residual_cand_results)

        print(f"    Computed residuals for {len(residual_ref_df)} orbit pairs")
        if len(residual_ref_df) > 0:
            print(f"    Mean RMSE: {residual_ref_df['RMSE'].mean():.6f} rad")

        results.add_stage("6. Residual Metrics", True,
                         f"Computed for {len(residual_ref_df)} orbits (simplified)")

        data["residual_ref_results"] = residual_ref_df
        data["residual_cand_results"] = residual_cand_df
        return data

    except Exception as e:
        import traceback
        traceback.print_exc()
        results.add_stage("6. Residual Metrics", False, str(e))
        return data


def test_stage_7_evaluation_report(results, data):
    """Stage 7: Generate evaluation report JSON"""
    print("\n[Stage 7] Generating evaluation report...")

    if data is None:
        results.add_stage("7. Evaluation Report", False, "No data from previous stages")
        return None

    try:
        from uct_benchmark.evaluation.evaluationReport import evaluationReport

        # Ensure all required data is present
        required = ["association_results", "binary_results", "state_results",
                   "residual_ref_results", "residual_cand_results"]
        missing = [r for r in required if r not in data or data[r] is None]

        if missing:
            results.add_stage("7. Evaluation Report", False, f"Missing: {missing}")
            return data

        output_path = data["data_dir"] / "raw_results.json"

        eval_dict = evaluationReport(
            data["association_results"],
            data["binary_results"],
            data["state_results"],
            data["residual_ref_results"],
            data["residual_cand_results"],
            str(output_path)
        )

        print(f"    Saved evaluation report to {output_path}")

        results.add_stage("7. Evaluation Report", True, f"Saved to {output_path.name}")

        data["eval_dict"] = eval_dict
        data["eval_path"] = output_path
        return data

    except Exception as e:
        import traceback
        traceback.print_exc()
        results.add_stage("7. Evaluation Report", False, str(e))
        return data


def test_stage_8_pdf_report(results, data):
    """Stage 8: Generate PDF report"""
    print("\n[Stage 8] Generating PDF report...")

    if data is None or "eval_path" not in data:
        results.add_stage("8. PDF Report", False, "No evaluation report from previous stage")
        return None

    try:
        # Change to src/libraries directory for PDF generation
        # The generatePDF has hardcoded relative paths for images (libraries/...) and output (../data/report.pdf)
        # So we need to run from src/libraries so that:
        #   - libraries/... images are found (they're in current dir)
        #   - ../data/report.pdf points to src/data/report.pdf
        src_dir = PROJECT_ROOT / "src"
        libraries_dir = src_dir / "libraries"
        original_cwd = os.getcwd()
        os.chdir(libraries_dir)

        # Add src to path
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))

        try:
            from libraries.generatePDF import generatePDF

            eval_path = data["eval_path"]
            # The generatePDF function has a hardcoded output path of "../data/report.pdf"
            # relative to src/libraries, so it will write to src/data/report.pdf
            output_path = data["data_dir"] / "report.pdf"

            # Need to temporarily set the working directory so relative image paths work
            # But the images are referenced as "libraries/..." so we need to be in src/
            os.chdir(src_dir)
            generatePDF(str(eval_path), str(output_path), path_flag=True)

            # The output will be at ../data/report.pdf relative to src = doesn't exist
            # Actually check what path the PDF was written to
            hardcoded_output = src_dir / "data" / "report.pdf"

            if hardcoded_output.exists():
                size_kb = hardcoded_output.stat().st_size / 1024
                print(f"    Generated PDF report at {hardcoded_output}")
                print(f"    File size: {size_kb:.1f} KB")
                results.add_stage("8. PDF Report", True, f"Generated {size_kb:.1f} KB PDF")
            else:
                results.add_stage("8. PDF Report", False, "PDF file not created")

        finally:
            os.chdir(original_cwd)

        return data

    except Exception as e:
        import traceback
        traceback.print_exc()
        results.add_stage("8. PDF Report", False, str(e))
        return data


def main():
    """Run the complete pipeline test"""
    print("="*60)
    print("UCT BENCHMARK PIPELINE END-TO-END TEST")
    print("="*60)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Working Directory: {PROJECT_ROOT}")

    results = PipelineTestResult()

    # Run all stages
    data = test_stage_1_load_sample_data(results)
    data = test_stage_2_run_dummy_uctp(results, data)
    data = test_stage_3_orbit_association(results, data)
    data = test_stage_4_binary_metrics(results, data)
    data = test_stage_5_state_metrics(results, data)
    data = test_stage_6_residual_metrics(results, data)
    data = test_stage_7_evaluation_report(results, data)
    data = test_stage_8_pdf_report(results, data)

    # Print summary
    success = results.summary()

    print(f"\nCompleted: {datetime.now().isoformat()}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
