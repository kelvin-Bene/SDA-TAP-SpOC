# -*- coding: utf-8 -*-
"""
Created on Mon Jun 23 14:18:20 2025

@author: Gabriel Lundin
"""

import json

import numpy as np
import pandas as pd

from uct_benchmark.utils.generateCov import generateCov


def readData(ref_obs_path, ref_orbits_path, dataset_path, uctp_output_path):
    # Load ref_obs df
    ref_obs = pd.read_csv(ref_obs_path, dtype={"trackId": str, "origin": str})
    ref_obs["obTime"] = pd.to_datetime(ref_obs["obTime"])

    # Load ref_orbits df
    ref_orbits = pd.read_csv(ref_orbits_path)
    ref_orbits["epoch"] = pd.to_datetime(ref_orbits["epoch"])
    ref_orbits["cov_matrix"] = ref_orbits["cov_matrix"].apply(lambda s: np.array(json.loads(s)))

    # Load dataset df
    dataset = pd.read_csv(dataset_path, dtype={"trackId": str, "origin": str})
    dataset["obTime"] = pd.to_datetime(ref_obs["obTime"])

    # Load uctp_output df
    uctp_output = pd.read_json("./data/uctp_output.json")
    uctp_output["epoch"] = pd.to_datetime(uctp_output["epoch"])
    uctp_output = generateCov(uctp_output)

    return ref_obs, ref_orbits, dataset, uctp_output
