# -*- coding: utf-8 -*-# -*- coding: utf-8 -*-
"""
Created on Tue Jun 10 2025

@author: Gabriel Lundin
"""

import numpy as np
import pandas as pd
import ast



# Import Orekit
import orekit_jpype as orekit
import jdk4py
import os

os.environ["JAVA_HOME"] = str(jdk4py.JAVA_HOME) #Setting JDK environment variable association
orekit.initVM() #Initiating JVM to enable package/class imports


from orekit_jpype.pyhelpers import setup_orekit_data
setup_orekit_data(from_pip_library=True)

from org.orekit.utils import PVCoordinates
from org.orekit.orbits import EquinoctialOrbit, PositionAngleType
from org.orekit.time import AbsoluteDate, DateComponents, TimeComponents, TimeScalesFactory
from org.orekit.frames import FramesFactory
from org.orekit.bodies import CelestialBodyFactory
from orekit_jpype import JArray_double


from orekit_jpype.pyhelpers import JArray_double2D

FRAME = FramesFactory.getEME2000()
earth = CelestialBodyFactory.getEarth()
MU_EARTH = earth.getGM()

from org.hipparchus.geometry.euclidean.threed import Vector3D

def _safe_parse_array(x):
    if isinstance(x, (np.ndarray, list)):
        return x
    elif isinstance(x, str):
        return ast.literal_eval(x)
    return np.nan

def _lower_triangular_to_symmetric(lower_vals):
    if not isinstance(lower_vals, (list, np.ndarray)) or len(lower_vals) != 21:
        return np.nan
    #Building 6x6 matrix
    mat = np.zeros((6, 6))
    idx = 0
    #Loading lower triangle covariance vector into matrix
    for row in range(6):
        for col in range(row + 1):
            val = lower_vals[idx]
            mat[row, col] = val
            idx += 1
    #Building symmetric covariance matrix 
    ##HAVE NOT VERIFIED DATA TRANSFORMATION YET: Needs further evaluation to ensure nothing was changed
    symmetric_matrix = mat + mat.T - np.diag(np.diag(mat))
    return mat

def _datetime_to_orekit_date(dt):
    date = DateComponents(dt.year, dt.month, dt.day)
    time = TimeComponents(dt.hour, dt.minute, dt.second + dt.microsecond * 1e-6)
    utc = TimeScalesFactory.getUTC()
    return AbsoluteDate(date, time, utc)

def _convert_eq_to_cartesian(row):
    try:
        if not row['isEq']:
            return row['cov_matrix']  # Already Cartesian

        # Extract state vector and epoch
        r = np.array([row['xpos'], row['ypos'], row['zpos']]) * 1e3  # km → m
        v = np.array([row['xvel'], row['yvel'], row['zvel']]) * 1e3  # km/s → m/s
        epoch = _datetime_to_orekit_date(row['epoch'])

        r_vec = Vector3D(float(r[0]), float(r[1]), float(r[2]))
        v_vec = Vector3D(float(v[0]), float(v[1]), float(v[2]))
        pv = PVCoordinates(r_vec, v_vec)
        orbit = EquinoctialOrbit(pv, FRAME, epoch, MU_EARTH)

        # Get Jacobian of Cartesian w.r.t Equinoctial
        J = JArray_double2D(6, 6)
        orbit.getJacobianWrtCartesian(PositionAngleType.MEAN, J)

        # Convert to numpy
        J2 = np.zeros((6,6))

        for i in range(6):
            temp = JArray_double.cast_(J[i])
            for j in range(6):
                J2[i,j] = temp[j]

        # Define unit scalings
        KM_TO_M = 1e3
        DEG_TO_RAD = np.pi / 180
        M_TO_KM = 1e-3
        RAD_TO_DEG = 180 / np.pi

        # Convert original covariance matrix to SI units
        scale_eq = np.diag([
            1,  # Af (unitless)
            1,  # Ag (unitless)
            DEG_TO_RAD,  # L (deg → rad)
            1,  # N (unitless)
            DEG_TO_RAD,  # Chi (deg → rad)
            DEG_TO_RAD   # Psi (deg → rad)
        ])
        cov_eq_si = scale_eq @ row['cov_matrix'] @ scale_eq.T

        # Transform covariance: Cartesian = J * Equinoctial * J.T
        cov_cart_si = J2 @ cov_eq_si @ J2.T

        # Convert back to km/s/deg (cartesian)
        scale_cart = np.diag([
            M_TO_KM,      # x
            M_TO_KM,      # y
            M_TO_KM,      # z
            M_TO_KM,      # vx
            M_TO_KM,      # vy
            M_TO_KM       # vz
        ])
        cov_cart = scale_cart @ cov_cart_si @ scale_cart.T

        return cov_cart

    except Exception as e:
        print(f"[ERROR] Covariance conversion failed for row: {e}")
        return np.nan

def generateCov(vectors):
    """
    Generates 6x6 Cartesian covariance matrices using multiprocessing.

    Args:
        vectors (Pandas DataFrame): DataFrame of state vectors from UDL.

    Returns:
        Pandas DataFrame: The inputted DataFrame with an additional "cov_matrix" column.      
    """
    
    # Since UDL has 2 different methods of using covs, filter correctly
    try:
        eqCov = vectors['eqCov'].apply(_safe_parse_array)
        eqCov.name = 'cov'
    except KeyError:
        eqCov = pd.Series([None] * len(vectors), index=vectors.index, name='cov')
    
    try:
        cov = vectors['cov'].apply(_safe_parse_array)
    except KeyError:
        cov = pd.Series([None] * len(vectors), index=vectors.index)
        
    vectors['cov_matrix'] = cov.fillna(eqCov)
    vectors['isEq'] = ~vectors['cov'].notna()
    
    vectors['cov_matrix'] = vectors['cov_matrix'].apply(_lower_triangular_to_symmetric)
    vectors['cov_matrix'] = vectors.apply(_convert_eq_to_cartesian, axis=1)
    
    vectors = vectors.drop(labels='isEq',axis=1)
    return vectors