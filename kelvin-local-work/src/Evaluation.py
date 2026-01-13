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
from libraries.apiIntegration import loadDataset
from libraries.generateCov import generateCov
from libraries.propagator import monteCarloPropagator, ephemerisPropagator,TLEpropagator
from libraries.orbitAssociation import orbitAssociation
from libraries.stateMetrics import stateMetrics
from libraries.binaryMetrics import binaryMetrics
from libraries.residualMetrics import residualMetrics
from libraries.evaluationReport import evaluationReport
from libraries.generatePDF import generatePDF
import libraries.config as config
#import libraries.reportGenerator


# === Main Execution Block ===
if __name__ == "__main__":

    start = time.perf_counter()

    # Fix potential current working dir issues
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("Reading data")
    ref_obs, obs_data, ref_track, track_data, ref_sv, ref_elset = loadDataset('./data/output_dataset.json')
    
    # Load uctp_output df
    uctp_output = pd.read_json('./data/uctp_output.json')
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
    evals = evaluationReport(association_results, binary_results, state_results, residual_ref_results, residual_cand_results, './data/raw_results.json')

    # Output Report PDF
    print("Outputting to PDF")
    PDF_output_path = './data/evaluation_report.pdf'
    PDF = generatePDF(evals, PDF_output_path)
    #subprocess.run([sys.executable, "libraries/reportGenerator.py"])

    end = time.perf_counter()
    # Print time elapsed
    print(f"Elapsed time: {(end - start) / 60:.2f} minutes")
