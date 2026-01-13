#                                       #
# UCTP Benchmarker Skeleton: Evaluation #
#                                       #

# to be run after running UCTP

# === Import Required Libraries ===
import time
import pandas as pd
import os
import sys
import numpy as np
import subprocess

# === Import Local Dependencies ==
#from libraries.readData import readData
from uctbenchmark.src.libraries.apiIntegration import loadDataset
from uctbenchmark.src.libraries.generateCov import generateCov
from uctbenchmark.src.libraries.propagator import monteCarloPropagator, ephemerisPropagator,TLEpropagator
from uctbenchmark.src.libraries.orbitAssociation import orbitAssociation
from uctbenchmark.src.libraries.stateMetrics import stateMetrics
from uctbenchmark.src.libraries.binaryMetrics import binaryMetrics
from uctbenchmark.src.libraries.residualMetrics import residualMetrics
from uctbenchmark.src.libraries.evaluationReport import evaluationReport
from uctbenchmark.src.libraries.generatePDF import generatePDF
import uctbenchmark.src.libraries.config as config
#import libraries.reportGenerator

def evaluate_results(uctp_data, output_dataset, eval_results, eval_pdf):

    start = time.perf_counter()

    print("Reading data")
    ref_obs, obs_data, ref_track, track_data, ref_sv, ref_elset = loadDataset(output_dataset)
    
    # Load uctp_output df
    uctp_output = pd.read_json(uctp_data)
    uctp_output['epoch'] = pd.to_datetime(uctp_output['epoch'])
    uctp_output = generateCov(uctp_output)

    # Perform orbit association
    print("Associating orbits")
    associated_orbits, association_results, nonassociated_orbits = orbitAssociation(ref_sv, uctp_output, ephemerisPropagator)
    #associated_orbits.to_csv("associated_orbits.csv", index=False)

    # Obtain binary metrics
    print("Computing binary metrics")
    binary_results = binaryMetrics(ref_obs,associated_orbits)

    # Obtain orbit state metrics
    print("Computing state metrics")
    state_results = stateMetrics(ref_sv, associated_orbits, monteCarloPropagator)

    # Obtain residual metrics
    print("Computing residual metrics")
    residual_cand_results = residualMetrics(ref_obs, uctp_output, ephemerisPropagator, False)
    residual_ref_results = residualMetrics(ref_obs, associated_orbits, ephemerisPropagator, True)

    # Output metrics
    print("Saving...")
    evals = evaluationReport(association_results, binary_results, state_results, residual_ref_results, residual_cand_results, eval_results)

    # Output Report PDF
    print("Outputting to PDF")
    PDF = generatePDF(evals, eval_pdf)
    #subprocess.run([sys.executable, "libraries/reportGenerator.py"])

    end = time.perf_counter()
    # Print time elapsed
    print(f"Elapsed time: {(end - start) / 60:.2f} minutes")

# === Main Execution Block ===
if __name__ == "__main__":
    evaluate_results()