# -*- coding: utf-8 -*-
"""
Created on Mon Jun 16 08:50:35 2025

@author: Gabriel Lundin
"""

import pandas as pd
import numpy as np
import time
from scipy.optimize import linear_sum_assignment
from concurrent.futures import ProcessPoolExecutor, as_completed
from uctbenchmark.src.libraries.apiIntegration import TLEToSV, parseTLE

def _compute_cost_column(j, truth_state, truth_cov, t_epoch, satPars, est_epochs, est_states, propagator):
    # Helper function to compute error between state vectors
    try:
        propagated_states = np.array(propagator(truth_state, t_epoch, est_epochs, satPars))
        deltas = est_states - propagated_states
        errors = np.linalg.norm(deltas, axis=1)
        return j, errors
    except Exception as e:
        print(f"[ERROR] Propagation failed for truth index {j}: {e}")
        return j, np.full(est_states.shape[0], np.inf)
    
def _compute_cost_column_TLE(j, truth_line1, truth_line2, t_epoch, est_epochs, est_states, propagator):
    # Helper function to compute error between TLEs
    try:
        prop_line1, prop_line2, propagated_states = propagator(truth_line1, truth_line2, est_epochs)
        deltas = np.vstack(est_states) - np.vstack(propagated_states)
        errors = np.linalg.norm(deltas, axis=1)
        return j, errors
    except Exception as e:
        print(f"[ERROR] Propagation failed for truth index {j}: {e}")
        return j, np.full(len(est_states), np.inf)

def orbitAssociation(truth, est, propagator, elset_mode=False):
    """
    Associates a list of candidate state vectors with a list of reference ones via linear sum assignment.
    This is globally optimized, so the lowest possible error assignments are performed for all candidates.

    Args:
        truth (Pandas DataFrame): A dataframe of reference orbits. State vectors must contain a "satNo" column, TLEs must contain a valid NORAD ID. 
        est (Pandas DataFrame): A dataframe of candidate orbits.
        propagator (function): An ephemeris orbit propagator to propagate orbits.
            SV Inputs: 6D state, 6x6 cov matrix, initial time, list of final times, satellite parameters (list of [mass,area,dragCoeff,solarRadPresCoeff])
            SV Outputs: Lists of 6D state, 6x6 cov matrix
            TLE Inputs: TLE line 1, TLE line 2, list of final times
            TLE Outputs: Lists of TLE line 1, TLE line 2, 6D state
        elset_mode (bool): If True, takes in TLE inputs. Defaults to False/state vector mode.

    Returns:
        associated_orbits (Pandas DataFrame): The associated orbits from "est" with a correctly filled "satNo" field 
                                              and an "error" field with the error between it and its associated state.
        results (dict): A dict containing information on the association process.
        nonassociated_orbits (Pandas DataFrame): If there are more candidate states than reference states, this contains 
                                         the non-associated states. If there are equal or more reference states, this is empty. 
    """

    # Start timer
    start_time = time.perf_counter()

    # Number of states
    n_est = len(est)
    n_truth = len(truth)

    # Initialize results dictionary
    results = {"Expected State Count": n_truth}

    if elset_mode:
        # Generate arrays of truth and est TLE lines
        est_line1 = est['line1'].tolist() 
        est_line2 = est['line2'].tolist() 
        
        truth_line1 = truth['line1'].tolist() 
        truth_line2 = truth['line2'].tolist() 
        
        # Parse TLEs and obtain epochs (+ satNo)
        est_parsed = est['elset']
        truth_parsed = truth['elset']
        est_epochs = [d['epoch'] for d in est_parsed]
        truth_epochs = [d['epoch'] for d in truth_parsed]
        truth_satnos = [d['NORAD_ID'] for d in truth_parsed]
        
        # Sort est by chronological order
        sorted_indices = sorted(range(len(est_epochs)), key=lambda i: est_epochs[i])
        
        # Apply that order to est and the lists
        est = est.iloc[sorted_indices].reset_index(drop=True)
        est_line1 = [est_line1[i] for i in sorted_indices]
        est_line2 = [est_line2[i] for i in sorted_indices]
        est_epochs = [est_epochs[i] for i in sorted_indices]
        
        # Generate state vectors of est TLEs (needed for cost)
        est_states = [TLEToSV(l1,l2) for l1, l2 in zip(est_line1, est_line2)]
        
        # Initialize cost matrix for assignment [n_est x n_truth]
        cost_matrix = np.zeros((n_est, n_truth))
        
        # Parallel propagate and compute cost
        
        with ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(
                    _compute_cost_column_TLE,
                    j,
                    truth_line1[j],
                    truth_line2[j],
                    truth_epochs[j],
                    est_epochs,
                    est_states,
                    propagator
                ) for j in range(n_truth)
            ]
    
            for future in as_completed(futures):
                j, errors = future.result()
                cost_matrix[:, j] = errors
            
        # Solve assignment problem using the Hungarian algorithm
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
                
        # Prepare associated and unassociated (bogus) output dataframes
        associated_orbits = []
        nonassociated_orbits = []
        
        # Create a fast lookup dictionary from estimated orbit index to truth orbit index
        # This replaces repeated np.where() calls in the loop with constant-time access
        assignment = dict(zip(row_ind, col_ind))
        
        for i in range(n_est):
            e_row = est.iloc[i].copy()
    
            if i in assignment:
                # Matched with reference orbit (truth index is assignment[i])
                j = assignment[i]
                e_row['satNo'] = truth_satnos[j]
                e_row['error'] = cost_matrix[i, j]
                e_row['uct'] = False
                norad_id = truth_line1[j][2:7]
                cospar_id = truth_line1[j][9:17]
                e_row['line1'] = (
                    e_row['line1'][:2] +            # "1 "
                    norad_id +                  # New NORAD
                    e_row['line1'][7:9] +           # Classification + space
                    cospar_id +                 # New COSPAR ID
                    e_row['line1'][17:]             # Remainder of line unchanged
                )
                e_row['line2'] = (
                    e_row['line2'][:2] +            # "1 "
                    norad_id +                  # New NORAD
                    e_row['line2'][7:]           # Remainder of line unchanged
                )
                e_row["elset"] = parseTLE(e_row['line1'], e_row['line2'])
                associated_orbits.append(e_row)
            else:
                # No associated reference orbit
                e_row['uct'] = True
                nonassociated_orbits.append(e_row)
    else:
        # State vector columns
        state_cols = ['xpos', 'ypos', 'zpos', 'xvel', 'yvel', 'zvel']
    
        # Convert to arrays for computation speed
        est_epochs = pd.to_datetime(est['epoch'].values).to_list()
        est_states = est[state_cols].values
    
        truth_epochs = pd.to_datetime(truth['epoch'].values)
        truth_states = truth[state_cols].values
        truth_covs = truth['cov_matrix'].values
        truth_satnos = truth['satNo'].values
    
        # Satellite physical parameters
        mass  = truth['mass'].values
        area  = truth['crossSection'].values
        drag  = truth['dragCoeff'].values
        solar = truth['solarRadPressCoeff'].values
    
        # Initialize cost matrix for assignment [n_est x n_truth]
        cost_matrix = np.zeros((n_est, n_truth))
    
        # Parallel propagation and cost computation
        with ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(
                    _compute_cost_column,
                    j,
                    truth_states[j],
                    truth_covs[j],
                    truth_epochs[j],
                    [mass[j], area[j], drag[j], solar[j]],
                    est_epochs,
                    est_states,
                    propagator
                ) for j in range(n_truth)
            ]
    
            for future in as_completed(futures):
                j, errors = future.result()
                cost_matrix[:, j] = errors
    
        # Solve assignment problem using the Hungarian algorithm
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
        # Prepare associated and unassociated (bogus) output dataframes
        associated_orbits = []
        nonassociated_orbits = []
    
        # Create a fast lookup dictionary from estimated orbit index to truth orbit index
        # This replaces repeated np.where() calls in the loop with constant-time access
        assignment = dict(zip(row_ind, col_ind))
    
        for i in range(n_est):
            e_row = est.iloc[i].copy()
    
            if i in assignment:
                # Matched with reference orbit (truth index is assignment[i])
                j = assignment[i]
                e_row['satNo'] = truth_satnos[j]
                e_row['mass'] = mass[j]
                e_row['crossSection'] = area[j]
                e_row['dragCoeff'] = drag[j]
                e_row['solarRadPressCoeff'] = solar[j]
                e_row['error'] = cost_matrix[i, j]
                e_row['uct'] = False
                associated_orbits.append(e_row)
            else:
                # No associated reference orbit
                e_row['uct'] = True
                nonassociated_orbits.append(e_row)
    
    # Convert result lists to DataFrames
    associated_orbits = pd.DataFrame(associated_orbits)
    associated_orbits = associated_orbits.sort_values(by='satNo', ascending=True)
    nonassociated_orbits = pd.DataFrame(nonassociated_orbits)

    # Populate results dictionary
    results['Associated Orbit Count']     = len(associated_orbits)
    results['Non-Associated Orbit Count'] = len(nonassociated_orbits)
    results['Undiscovered Reference Orbits']  = n_truth - len(associated_orbits)
    results['Time Elapsed']               = time.perf_counter() - start_time

    return associated_orbits, results, nonassociated_orbits