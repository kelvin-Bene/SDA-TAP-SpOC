# -*- coding: utf-8 -*-
"""
Created on Mon July 2 2025

@author: Binyamin J. Stivi & Louis Caves
"""

import os, sys, subprocess

import numpy as np
import pandas as pd
import time as time
import base64
from libraries.dataManipulation import binTracks
from libraries.gauss import gaussSorter


#initialize orekit and JVM
#import orekit
#orekit.initVM()
import orekit_jpype as orekit

from orekit_jpype.pyhelpers import setup_orekit_curdir, absolutedate_to_datetime
setup_orekit_curdir()

from org.orekit.frames import FramesFactory, TopocentricFrame
from org.orekit.estimation.measurements import GroundStation, ObservableSatellite
from org.orekit.estimation.measurements import AngularRaDec, AngularAzEl
from org.orekit.bodies import OneAxisEllipsoid, GeodeticPoint, CelestialBodyFactory
from org.orekit.estimation.iod import IodLambert, IodGibbs, IodGooding, IodGauss 
from org.orekit.time import TimeScalesFactory, AbsoluteDate, DateComponents, TimeComponents
from org.orekit.utils import IERSConventions, Constants, PVCoordinates, PVCoordinatesProvider, AbsolutePVCoordinates
from org.hipparchus.geometry.euclidean.threed import Vector3D, SphericalCoordinates
from org.orekit.orbits import KeplerianOrbit, CartesianOrbit, OrbitType
from org.orekit.propagation.analytical.tle import TLE, TLEPropagator
from org.orekit.propagation import SpacecraftState
from org.orekit.orbits import KeplerianOrbit
from org.orekit.propagation.analytical.tle.generation import FixedPointTleGenerationAlgorithm
from org.orekit.utils import IERSConventions, Constants, PVCoordinates, PVCoordinatesProvider, AbsolutePVCoordinates, TimeStampedPVCoordinates
from org.orekit.estimation.measurements import PV
from org.hipparchus.optim.nonlinear.vector.leastsquares import LevenbergMarquardtOptimizer
from org.orekit.estimation.leastsquares import BatchLSEstimator
from org.orekit.orbits import OrbitType, PositionAngleType
from org.orekit.propagation.conversion import TLEPropagatorBuilder


from math import radians, pi, degrees, sin, cos, sqrt, acos
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def TLEGeneration(ref_obs, ref_sv):
    """
    Takes observations and states and makes crude TLEs out of them
    
    Parameters:
        ref_obs dataframe containing all the observations
        ref_sv dataframe containing all the state vectors
        
    Returns:
    df_output dataframe containing all TLEs
    """


    def run_tle_orbit_determination(template_tle: TLE,
                                    
                                    pv_measurements: PV,
                                    ):
        """
        Performs TLE-based orbit determination.

        Args:
            TLE (TLE):  The TLE object containing the initial TLE lines.
            
            pv_measurements (PV): A list of PV measurement tuples. Each tuple should
                                    contain (AbsoluteDate, Vector3D_pos, Vector3D_vel).
            reference_pv (tuple[Vector3D, Vector3D]): A tuple containing the reference
                                                    position and velocity for comparison.
        """
        # 1. Setup Frames and Constants
        # The TLE frame is TEME (True Equator, Mean Equinox)
        teme_frame = FramesFactory.getTEME()
        utc = TimeScalesFactory.getUTC()

        # 2. Create the initial TLE object
        
        tle_epoch = template_tle.getDate()

        print("--- Initial TLE ---")
        print(template_tle.getLine1())
        print(template_tle.getLine2())
        print("-" * 21)

        # 3. Configure the Orbit Determination
        # We use a Levenberg-Marquardt optimizer for the least-squares problem
        optimizer = LevenbergMarquardtOptimizer()
        
        # The TLE builder needs the template TLE and a generation algorithm
        # The FixedPointTleGenerationAlgorithm is designed for this purpose
        tle_generation_algorithm = FixedPointTleGenerationAlgorithm()
        
        # The TLEPropagatorBuilder is the key component that connects the TLE model
        # to the estimation process. The 'positionScale' of 1000.0 is a tuning
        # parameter for the orbit parameters.
        propagator_builder = TLEPropagatorBuilder(template_tle,
                                                PositionAngleType.MEAN,
                                                1000.0,
                                                tle_generation_algorithm)

        # Configure the estimator
        estimator = BatchLSEstimator(optimizer, propagator_builder)

        # 4. Add Measurements to the Estimator
        # The estimator needs a satellite object for the measurements
        sat = ObservableSatellite(0)


        # Convert the input PV data into Orekit PV measurement objects
        for i in range(len(pv_measurements)):
            estimator.addMeasurement(pv_measurements[i])
            



        # The only parameters to estimate are the orbital elements, which are
        # handled automatically by the TLEPropagatorBuilder.
        estimator.setParametersConvergenceThreshold(1.0e-3)
        estimator.setMaxIterations(100)
        estimator.setMaxEvaluations(100)

        # 5. Run the Estimation
        print("\nRunning orbit determination...")
        estimated_propagators = estimator.estimate()
        print("Estimation complete.\n")

        # 6. Get the Estimated TLE
        # The result is a propagator, from which we can extract the new TLE
        estimated_tle_propagator = TLEPropagator.cast_(estimated_propagators[0])
        estimated_tle = estimated_tle_propagator.getTLE()
        
        print("--- Estimated TLE ---")
        print(estimated_tle.getLine1())
        print(estimated_tle.getLine2())
        print("-" * 21)



        # Get PV from the initial template TLE at its epoch
        initial_propagator = TLEPropagator.selectExtrapolator(template_tle)
        state1 = initial_propagator.propagate(tle_epoch)
        initial_pv = state1.getPVCoordinates()

        # Get PV from the final estimated TLE at its epoch
        state2 = estimated_tle_propagator.propagate(tle_epoch)
        final_pv = state2.getPVCoordinates()
        return estimated_tle




    ################# GRAB FRAMES, DATA, AND GENERATE EARTH BODY
    UTC = TimeScalesFactory.getUTC()                               # Define UTC time scale.
    ECI = FramesFactory.getEME2000()                               # Define ECI reference frame.
    ECEF = FramesFactory.getITRF(IERSConventions.IERS_2010, True)  # Define ECEF reference frame.
    TEME = FramesFactory.getTEME()                                 # Define TEME reference frame. 
    ITRF = ECEF
    Mu = Constants.WGS84_EARTH_MU # Gravitational parameter of Earth

    R_earth  = Constants.WGS84_EARTH_EQUATORIAL_RADIUS             # Radius of earth
    Mu_earth = Constants.WGS84_EARTH_MU                            # Gravitational parameter of earth
    f_earth  = Constants.WGS84_EARTH_FLATTENING                    # Earth flattening value

    earth = OneAxisEllipsoid(R_earth, f_earth, ITRF)                  # Create earth here.

    binned, _ = binTracks(ref_obs, ref_sv)

    df_output = pd.DataFrame(columns=['NORAD_ID', 'TLE1', 'TLE2',
                                'meanMotion', 'semiMajorAxis', 'eccentricity', 
                                'inclination', 'raan', 'epoch', 'bStar', 'meanMotionDot',
                                'meanMotionDDot', 'origObjectId'
                                ])

    IODresults = gaussSorter(binned) 
    # Find the states from the data
    # Pull the tuplet for each satellite
    for j in range(len(IODresults)):
        IODresult = IODresults[j]
        # Pull the state data from each tuplet
        IODstates1 = IODresult[2]
        
        if IODstates1.shape[0] == 0:
            # No state found
            df_output.loc[j,'origObjectId'] = None
            df_output.loc[j,'NORAD_ID'] = IODresult[0]   
            df_output.loc[j,'TLE1'] = None
            df_output.loc[j,'TLE2'] = None
            df_output.loc[j,'meanMotion'] = None
            df_output.loc[j,'semiMajorAxis'] = None
            df_output.loc[j,'eccentricity'] = None
            df_output.loc[j,'inclination'] = None
            df_output.loc[j,'raan'] = None
            df_output.loc[j,'epoch'] = None
            df_output.loc[j,'bStar'] = None
            df_output.loc[j,'meanMotionDot'] = None
            df_output.loc[j,'meanMotionDDot'] = None
            continue

        ################### GENERATE STATIC TLE TEMPLATE
        templateLine1 = "1 99999U 00000A   25160.00000000  .00000000  00000-0  00000-0 0  9999"
        templateLine2 = "2 99999  98.0000 000.0000 0001000 000.0000 000.0000 15.00000000  9999"
        # Create TLE template
        templateTLE = TLE(templateLine1, templateLine2)

        fixedPoint = FixedPointTleGenerationAlgorithm() # convert propagated state to TLE


        # Get the first date and state vector to make initial TLE
        first_date = IODstates1.loc[0,'obTime']
        first_date = first_date[1] 

        first_state_vector =  IODstates1.loc[0,'state'] # Assuming state is a list of [x, y, z, vx, vy, vz]

        target_frame = FramesFactory.getEME2000()
        utc = TimeScalesFactory.getUTC()
        first_date = pd.to_datetime(first_date)
        absdate = AbsoluteDate(first_date.year, first_date.month, first_date.day,
                            first_date.hour, first_date.minute, first_date.second + first_date.microsecond / 1e6,
                            utc)

        x, y, z, vx, vy, vz = first_state_vector

        position_initial = Vector3D(float(x)*1000, float(y)*1000, float(z)*1000)
        velocity_initial = Vector3D(float(vx)*1000, float(vy)*1000, float(vz)* 1000)

        TS_PV_initial = TimeStampedPVCoordinates(absdate,  position_initial, velocity_initial)
        IOD = CartesianOrbit(TS_PV_initial, target_frame, Mu_earth)
        IOD_STATE = SpacecraftState(IOD)
        try:
            IOD_TLE = TLE.stateToTLE(IOD_STATE, templateTLE, fixedPoint)
        except orekit.JavaError as e:
            print('Error in TLE Generation:', e)
            print('Skipping Window.')
            df_output.loc[j,'origObjectId'] = None
            df_output.loc[j,'NORAD_ID'] = IODresult[0]   
            df_output.loc[j,'TLE1'] = None
            df_output.loc[j,'TLE2'] = None
            df_output.loc[j,'meanMotion'] = None
            df_output.loc[j,'semiMajorAxis'] = None
            df_output.loc[j,'eccentricity'] = None
            df_output.loc[j,'inclination'] = None
            df_output.loc[j,'raan'] = None
            df_output.loc[j,'epoch'] = None
            df_output.loc[j,'bStar'] = None
            df_output.loc[j,'meanMotionDot'] = None
            df_output.loc[j,'meanMotionDDot'] = None
            continue

        PV_ALL = IODstates1['state']
        epoch_ALL = IODstates1['obTime']
        measurements = []

        for i in range(len(PV_ALL)):
            position = Vector3D(PV_ALL[i][0]*1000, PV_ALL[i][1]*1000, PV_ALL[i][2]*1000)
            #print(position)
            velocity = Vector3D(PV_ALL[i][3]*1000, PV_ALL[i][4]*1000, PV_ALL[i][5]*1000)
            #print(velocity)

            # Create TimeStampedPVCoordinates for each epoch
            epoch = pd.to_datetime(epoch_ALL[i][1])  # Assuming epoch_ALL[i] is a list with timestamps
            absdate = AbsoluteDate(epoch.year, epoch.month, epoch.day,
                                epoch.hour, epoch.minute, epoch.second + epoch.microsecond / 1e6,
                                UTC)
            
            #TS_PV = TimeStampedPVCoordinates(absdate, position, velocity)
            
            measurement = PV(absdate, position, velocity, 10.0, 1.0, 1.0, ObservableSatellite(0))
            
            measurements.append(measurement)
            # Process the measurement as needed (e.g., store it in a list or DataFrame)
            
        try: # Run the TLE-based orbit determination to refine the TLE
            TLE_Batch = run_tle_orbit_determination(IOD_TLE, measurements)
        except orekit.JavaError as e:
            print('Error in Batch Filter:', e)
            print('Using IOD as TLE.')
            TLE_Batch = IOD_TLE



        ########### ADD RESULTS TO OUTPUT
        df_output.loc[j,'origObjectId'] = str(IODstates1['stateID'][0]) + str(IODstates1['stateID'].tail(1))
        df_output.loc[j,'NORAD_ID'] = IODresult[0]   
        df_output.loc[j,'TLE1'] = TLE.getLine1(TLE_Batch)
        df_output.loc[j,'TLE2'] = TLE.getLine2(TLE_Batch)
        df_output.loc[j,'meanMotion'] = TLE.getMeanMotion(TLE_Batch)
        df_output.loc[j,'semiMajorAxis'] = TLE.computeSemiMajorAxis(TLE_Batch)
        df_output.loc[j,'eccentricity'] = TLE.getE(TLE_Batch)
        df_output.loc[j,'inclination'] = TLE.getI(TLE_Batch)
        df_output.loc[j,'raan'] = TLE.getRaan(TLE_Batch)
        df_output.loc[j,'epoch'] = TLE.getDate(TLE_Batch)
        df_output.loc[j,'bStar'] = TLE.getBStar(TLE_Batch)
        df_output.loc[j,'meanMotionDot'] = TLE.getMeanMotionFirstDerivative(TLE_Batch)
        df_output.loc[j,'meanMotionDDot'] = TLE.getMeanMotionSecondDerivative(TLE_Batch)
    return df_output
