# -*- coding: utf-8 -*-
"""
Created on Mon Jun 23 13:12:25 2025

@author: Gabriel Lundin
"""

import json

import numpy as np


def evaluationReport(
    association_results,
    binary_results,
    state_results,
    residual_ref_results,
    residual_cand_results,
    output_path,
):
    """
    Generates and saves the JSON result file containing performance metrics.

    Args:
        association_results (Dict): Dict of association metrics.
        binary_results (Pandas DataFrame): Dataframe of binary metrics.
        state_results (Pandas DataFrame): Dataframe of residual metrics.
        residual_ref_results (Pandas DataFrame): Dataframe of residual metrics WRT reference orbits.
        residual_cand_results (Pandas DataFrame): Dataframe of residual metrics WRT candidate orbits.
        output_path (str): Output relative path for the JSON result file.

    Outputs:
        eval (Dict): The combined raw evaluation dict.
    """

    # Convert DataFrame cell arrays to nested lists
    def _convert_arrays(df):
        return df.applymap(lambda x: x.tolist() if isinstance(x, np.ndarray) else x)

    association_results.pop("Time Elapsed", None)

    residual_ref_results["Epoch"] = residual_ref_results["Epoch"].apply(
        lambda arr: [ts.isoformat() if hasattr(ts, "isoformat") else str(ts) for ts in arr]
    )

    residual_cand_results["Epoch"] = residual_cand_results["Epoch"].apply(
        lambda arr: [ts.isoformat() if hasattr(ts, "isoformat") else str(ts) for ts in arr]
    )

    combined_dict = {
        "association_results": association_results,
        "binary_results": _convert_arrays(binary_results).to_dict(orient="records"),
        "state_results": _convert_arrays(state_results).to_dict(orient="records"),
        "residual_ref_results": _convert_arrays(residual_ref_results).to_dict(orient="records"),
        "residual_cand_results": _convert_arrays(residual_cand_results).to_dict(orient="records"),
    }

    # Save to JSON
    with open(output_path, "w") as f:
        json.dump(combined_dict, f, indent=2)

    return combined_dict
