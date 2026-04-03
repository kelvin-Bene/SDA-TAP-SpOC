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
from uct_benchmark.utils.unitConversion import unitConversion
from loguru import logger


# === Main Execution Block ===
if __name__ == "__main__":
    start = time.perf_counter()

    # Fix potential current working dir issues
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("Reading data")
    ref_obs, obs_data, ref_track, track_data, ref_sv, ref_elset = loadDataset(
        "./data/output_dataset.json"
    )

    # Extract non-reference observations for True Negative calculation
    # Non-reference observations are those in obs_data that are NOT in the reference set
    ref_obs_ids = set(ref_obs["id"].unique())
    non_ref_obs = obs_data[~obs_data["id"].isin(ref_obs_ids)].copy()
    if not non_ref_obs.empty:
        # Add source_norad_id column (required by binaryMetrics) -- these are unknown
        # in the decorrelated output, so we mark them as -1 (non-reference placeholder)
        if "source_norad_id" not in non_ref_obs.columns:
            non_ref_obs["source_norad_id"] = -1
        logger.info(
            f"Found {len(non_ref_obs)} non-reference observations for TN calculation"
        )
    else:
        non_ref_obs = None
        logger.info("No non-reference observations found in dataset")

    # Load uctp_output df
    uctp_output = pd.read_json("./data/uctp_output.json")
    uctp_output["epoch"] = pd.to_datetime(uctp_output["epoch"])
    uctp_output = generateCov(uctp_output)

    # Convert UCTP output state vectors to J2000 if needed
    if "referenceFrame" in uctp_output.columns:
        non_j2000 = uctp_output[
            ~uctp_output["referenceFrame"].isin(["J2000", "EME2000"])
        ]
        if not non_j2000.empty:
            frames_found = non_j2000["referenceFrame"].unique().tolist()
            logger.info(
                f"Converting {len(non_j2000)} UCTP state vectors from "
                f"{frames_found} to J2000"
            )
            uctp_output = unitConversion(uctp_output)
        else:
            logger.info("All UCTP state vectors already in J2000/EME2000 frame")
    else:
        logger.info("No referenceFrame column in UCTP output; assuming J2000")

    # Perform orbit association
    print("Associating orbits")
    associated_orbits, association_results, nonassociated_orbits = orbitAssociation(
        ref_sv, uctp_output, ephemerisPropagator
    )

    # Obtain binary metrics (with True Negatives from non-reference observations)
    print("Computing binary metrics")
    binary_results = binaryMetrics(
        ref_obs, associated_orbits, non_ref_observations=non_ref_obs
    )

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
