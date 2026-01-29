# -*- coding: utf-8 -*-
"""
Created on Mon Jun 23 14:18:20 2025

@author: Gabriel Lundin
"""

import pandas as pd, json, numpy as np, os

from uctbenchmark.src.libraries.generateCov import generateCov

ref_obs = os.getenv("REF_OBS")
ref_orbits = os.getenv("REF_ORBITS")

def readData(ref_obs, ref_orbits, output_data, uctp_data):
    
    # Load ref_obs df
    reference_obs = pd.read_csv(ref_obs, dtype={'trackId': str, 'origin': str})
    reference_obs['obTime'] = pd.to_datetime(reference_obs['obTime'])
    
    # Load ref_orbits df
    reference_orbits = pd.read_csv(ref_orbits)
    reference_orbits['epoch'] = pd.to_datetime(reference_orbits['epoch'])
    reference_orbits['cov_matrix'] = reference_orbits['cov_matrix'].apply(lambda s: np.array(json.loads(s)))

    # Load dataset df
    dataset = pd.read_csv(dataset_path, dtype={'trackId': str, 'origin': str})
    dataset['obTime'] = pd.to_datetime(reference_obs['obTime'])

    # Load uctp_output df
    uctp_output = pd.read_json(uctp_data)
    uctp_output['epoch'] = pd.to_datetime(uctp_output['epoch'])
    uctp_output = generateCov(uctp_output)

    return reference_obs, reference_orbits, dataset, uctp_output