# -*- coding: utf-8 -*-
"""
Created on Thu Jun 12 16:35:21 2025

@author: Gabriel Lundin
"""

import numpy as np, matplotlib.pyplot as plt, pandas as pd

from scipy.optimize import minimize_scalar

def _rotation_matrix(i_deg, RAAN_deg, w_deg):
    """Rotation matrix from PQW frame to ECI frame."""
    i = np.radians(i_deg)
    RAAN = np.radians(RAAN_deg)
    w = np.radians(w_deg)

    cosRAAN, sinRAAN = np.cos(RAAN), np.sin(RAAN)
    cosw, sinw = np.cos(w), np.sin(w)
    cosi, sini = np.cos(i), np.sin(i)

    R = np.array([
        [cosRAAN*cosw - sinRAAN*sinw*cosi, -cosRAAN*sinw - sinRAAN*cosw*cosi, sinRAAN*sini],
        [sinRAAN*cosw + cosRAAN*sinw*cosi, -sinRAAN*sinw + cosRAAN*cosw*cosi, -cosRAAN*sini],
        [sinw*sini, cosw*sini, cosi]
    ])
    return R

def _orbit_position(a, e, ν_rad):
    """Position in PQW frame for given true anomaly."""
    r = a*(1-e**2) / (1 + e*np.cos(ν_rad))
    x = r*np.cos(ν_rad)
    y = r*np.sin(ν_rad)
    return np.array([x, y, 0.0])

def _radec_to_los(ra_deg, dec_deg):
    """Convert RA and Dec into a LoS vector."""
    ra = np.radians(ra_deg)
    dec = np.radians(dec_deg)
    x = np.cos(dec)*np.cos(ra)
    y = np.cos(dec)*np.sin(ra)
    z = np.sin(dec)
    return np.array([x, y, z])

def _closest_approach_to_los(orbit_params, los_vec):
    """Determine the point on a given orbit corresponding to closest approach of a LoS vector."""
    a = orbit_params['Semi-Major Axis']
    e = orbit_params['Eccentricity']
    i = orbit_params['Inclination']
    RAAN = orbit_params['RAAN']
    argp = orbit_params['Argument of Perigee']

    R = _rotation_matrix(i, RAAN, argp)

    def angular_error(nu):
        r_pqw = _orbit_position(a, e, nu)
        r_eci = R @ r_pqw
        r_hat = r_eci / np.linalg.norm(r_eci)
        cos_angle = np.clip(np.dot(r_hat, los_vec), -1.0, 1.0)
        angle = np.arccos(cos_angle)
        return angle**2

    result = minimize_scalar(angular_error, bounds=(-0.1, 2*np.pi+0.1), method='bounded') # Bounds extended for rounding reasons
    ν_best = result.x
    r_pqw_best = _orbit_position(a, e, ν_best)
    r_eci_best = R @ r_pqw_best
    return r_eci_best

def _obs_projections(obs,orbElems):
    """Generate closest-approach vectors for each observation to orbit and circumscribing cirle."""
    
    # Generate obs vectors based on closest fit to orbit (Nx3 array)
    vectors_ellipse = []
    for _, row in obs.iterrows():
        los = _radec_to_los(row['ra'], row['declination'])
        closest = _closest_approach_to_los(orbElems, los)
        vectors_ellipse.append(closest)
    
    # Now have vectors on ellipse, need to project to circumscribed circle
    a = orbElems['Semi-Major Axis']
    e = orbElems['Eccentricity']
    i = orbElems['Inclination']
    RAAN = orbElems['RAAN']
    w = orbElems['Argument of Perigee']

    R = _rotation_matrix(i, RAAN, w)
    perigee_dir = R @ np.array([1, 0, 0])
    #plane_normal = R @ np.array([0, 0, 1]) 
    
    c_vec = -a * e * perigee_dir  # geometric center of ellipse

    vectors = []
    for p in vectors_ellipse:
        d = p - c_vec
        d_norm = np.linalg.norm(d)
        if d_norm == 0:
            vectors.append(c_vec)
        else:
            intersection = c_vec + (a / d_norm) * d
            vectors.append(intersection)

    return np.array(vectors), np.array(vectors_ellipse)



def orbitCoverage(obs, orbElems):
    """
    Computes an observation list's polynomial coverage percentage of an orbit.
    
    Args:
        obs (Pandas DataFrame): DataFrame of observations that have geocentric 'ra' and 'declination' fields.
        orbElems (Dict): Dictionary containing the orbital elements 'Semi-Major Axis', 'Eccentricity', 'Inclination', 'RAAN', 'Argument of Perigee', and 'Mean Anomaly'. Units are km and degrees as appropriate.
    
    Returns:
        float: Percentage of orbit coverage.
        DataFrame: Sorted 2D polygon points with observation IDs.
    """
    
    vectors, _ = _obs_projections(obs,orbElems)
    
    centroid3d = vectors.mean(axis=0)

    # PCA to get plane normal and basis
    centered = vectors - centroid3d
    _, _, vh = np.linalg.svd(centered)
    u_axis = vh[0]
    v_axis = vh[1]

    # Project into 2D in-plane coordinates
    u_coords = centered @ u_axis
    v_coords = centered @ v_axis
    polygon_2d = np.stack((u_coords, v_coords), axis=1)

    # Sort the points CCW around the 2D centroid
    centroid2d = polygon_2d.mean(axis=0)
    angles = np.arctan2(polygon_2d[:,1] - centroid2d[1],
                        polygon_2d[:,0] - centroid2d[0])
    sort_order = np.argsort(angles)
    sorted_polygon_2d = polygon_2d[sort_order]

    # Shoelace formula
    x = sorted_polygon_2d[:, 0]
    y = sorted_polygon_2d[:, 1]
    area = 0.5 * np.abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    
    # Find circumscribing circle area
    circArea = np.pi*orbElems['Semi-Major Axis']**2
    
    # Create point df for other functions
    sorted_ids = obs['id'].iloc[sort_order].reset_index(drop=True)
    polygon_df = pd.DataFrame(sorted_polygon_2d, columns=['x', 'y'])
    polygon_df['id'] = sorted_ids
    
    return area/circArea, polygon_df

def plotCoverage(obs, orbElems):
    """
    Visually displays the coverage percentage.
    
    Args:
        obs (Pandas DataFrame): A dataframe of observations in geocentric frame with "ra" and "declination" values.
        orbElems (Dict): The orbital parameters in the following form: {"Semi-Major Axis", "Eccentricity", "Inclination", "RAAN", "Arguement of Perigee", "Mean Anomaly"}
    
    Returns:
        pylot: A visual plot of orbit coverage.
    """
    circle_vecs, ellipse_vecs = _obs_projections(obs, orbElems)
    a = orbElems['Semi-Major Axis']
    e = orbElems['Eccentricity']
    i = orbElems['Inclination']
    RAAN = orbElems['RAAN']
    w = orbElems['Argument of Perigee']
    
    R = _rotation_matrix(i, RAAN, w)
    
    # Fit orbital plane using PCA (get principal axes)
    mean = np.mean(ellipse_vecs, axis=0)
    centered_e = ellipse_vecs - mean
    centered_c = circle_vecs - mean
    u, s, vh = np.linalg.svd(centered_e)
    #plane_normal = vh[2]
    
    # Define 2D basis in plane
    basis_x = vh[0]
    basis_y = vh[1]
    
    # Ellipse plotting
    
    theta = np.linspace(0, 2 * np.pi, 500)
    r = a * (1 - e**2) / (1 + e * np.cos(theta))
    
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    
    r_pqw = np.vstack([x, y, np.zeros_like(x)])
    r_eci = R @ r_pqw
    r_centered = r_eci.T - mean
    x = r_centered @ basis_x
    y = r_centered @ basis_y
    
    # Obs plotting
    
    centered_e = np.vstack([centered_e, centered_e[0,:]])
    x_2d = centered_e @ basis_x
    y_2d = centered_e @ basis_y
    
    centered_c = np.vstack([centered_c, centered_c[0,:]])
    x_c2d = centered_c @ basis_x
    y_c2d = centered_c @ basis_y

    # Circumscribing circle plotting
    
    circle_r = a
    circle_x3d = circle_r * np.cos(theta) - a*e
    circle_y3d = circle_r * np.sin(theta)
    circle_z3d = np.zeros_like(theta)
    
    circle_pqw = np.vstack([circle_x3d, circle_y3d, circle_z3d])
    
    circle_eci = R @ circle_pqw
    
    circle_centered = circle_eci.T - mean
    
    circle_x = circle_centered @ basis_x
    circle_y = circle_centered @ basis_y

    # Actual plot
    
    plt.figure(figsize=(8, 8))
    plt.plot(x, y, label='Orbit',color='green')
    plt.scatter(x_2d, y_2d, label='Observations', color='black', marker="x")
    plt.scatter(x_c2d, y_c2d, label='Obs Projections', color='black')
    plt.plot(x_c2d, y_c2d, color='blue')
    plt.plot(circle_x, circle_y, label='Circumscribing Circle', color=  'red', linestyle='--')
    plt.fill(x_c2d, y_c2d, alpha=0.1, label='Area Contained in Observations', facecolor='cyan')

    plt.gca().set_aspect('equal')
    plt.title("Coverage in PCA Orbital Plane")
    plt.xlabel("X [km]")
    plt.ylabel("Y [km]")
    plt.legend(loc='center')
    #plt.show()
    
    return plt
