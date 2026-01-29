#                                       #
# UCTP Benchmarker Skeleton: Evaluation #
#                                       #

# to be run after running UCTP

# === Import Required Libraries ===
import os
import time

import pandas as pd

# === Import Local Dependencies ==
from uct_benchmark.api.apiIntegration import loadDataset
from uct_benchmark.evaluation.binaryMetrics import binaryMetrics
from uct_benchmark.evaluation.evaluationReport import evaluationReport
from uct_benchmark.evaluation.orbitAssociation import orbitAssociation
from uct_benchmark.evaluation.residualMetrics import residualMetrics
from uct_benchmark.evaluation.stateMetrics import stateMetrics
from uct_benchmark.simulation.propagator import (
    ephemerisPropagator,
    monteCarloPropagator,
)
from uct_benchmark.utils.generateCov import generateCov
from uct_benchmark.utils.generatePDF import generatePDF


# === Main Execution Block ===
if __name__ == "__main__":
    start = time.perf_counter()

    # Fix potential current working dir issues
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("Reading data")
    ref_obs, obs_data, ref_track, track_data, ref_sv, ref_elset = loadDataset(
        "./data/output_dataset.json"
    )

    # Load uctp_output df
    uctp_output = pd.read_json("./data/uctp_output.json")
    uctp_output["epoch"] = pd.to_datetime(uctp_output["epoch"])
    uctp_output = generateCov(uctp_output)

    # Perform orbit association
    print("Associating orbits")
    associated_orbits, association_results, nonassociated_orbits = orbitAssociation(
        ref_sv, uctp_output, ephemerisPropagator
    )

    # Obtain binary metrics
    print("Computing binary metrics")
    binary_results = binaryMetrics(ref_obs, associated_orbits)

    # Obtain orbit state metrics
    print("Computing state metrics")
    state_results = stateMetrics(ref_sv, associated_orbits, monteCarloPropagator)

    # Obtain residual metrics
    print("Computing residual metrics")
    residual_cand_results = residualMetrics(ref_obs, uctp_output, ephemerisPropagator, False)
    residual_ref_results = residualMetrics(ref_obs, associated_orbits, ephemerisPropagator, True)

    # Output metrics
    print("Saving...")
    evals = evaluationReport(
        association_results,
        binary_results,
        state_results,
        residual_ref_results,
        residual_cand_results,
        "./data/raw_results.json",
    )

    # Output Report PDF
    print("Outputting to PDF")
    PDF_output_path = "./data/evaluation_report.pdf"
    PDF = generatePDF(evals, PDF_output_path)

    end = time.perf_counter()
    # Print time elapsed
    print(f"Elapsed time: {(end - start) / 60:.2f} minutes")
