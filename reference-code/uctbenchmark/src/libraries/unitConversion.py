# -*- coding: utf-8 -*-
'''
Created on Tue 10 June 2025

@author: Binyamin J. Stivi
'''


import pandas as pd
import numpy as np
from uctbenchmark.src.libraries.generateCov import generateCov

import orekit_jpype as orekit
import jdk4py
import os

os.environ["JAVA_HOME"] = str(jdk4py.JAVA_HOME) #Setting JDK environment variable association
orekit.initVM() #Initiating JVM to enable package/class imports


from orekit_jpype.pyhelpers import setup_orekit_data
setup_orekit_data(filenames=os.path.join(os.getenv("EXT_DIR"), "orekit-data"), from_pip_library=False)



from org.orekit.frames import FramesFactory
from orekit_jpype import JArray_double
from orekit_jpype.pyhelpers import JArray
from org.orekit.time import AbsoluteDate
from org.orekit.utils import PVCoordinates
from org.hipparchus.geometry.euclidean.threed import Vector3D
from org.orekit.frames import Predefined
from org.orekit.time import TimeScalesFactory
from org.orekit.propagation import StateCovariance
from org.hipparchus.linear import Array2DRowRealMatrix, MatrixUtils
from org.orekit.orbits import OrbitType
from org.orekit.orbits import PositionAngleType
from org.orekit.bodies import CelestialBodyFactory
from org.orekit.orbits import CartesianOrbit



def unitConversion(ref_orbit):
    """
    Converts the reference orbit and covariance data from various coordinate frames
    (TEME, GCRF, ITRF, ECEF, TDR) provided by the UDL API
    to J2000 coordinates .
    
    input:
        ref_orbit: pd.DataFrame containing the reference orbit data with columns:

    output:
        df: pd.DataFrame with converted coordinates and covariance matrices in J2000 frame
    
    """
    def convert_to_j2000(x,y,z,vx,vy,vz,date,cov,frame):
        """
        Convert position and velocity to J2000 using Orekit.
        
        Parameters:
            position_km (list or tuple): [x, y, z] in kilometers
            velocity_kmps (list or tuple): [vx, vy, vz] in km/s
            date (AbsoluteDate): Orekit AbsoluteDate object in UTC
            covariance: numpy matrix 
            
        Returns:
            pos_j2000, vel_j2000: numpy array in kilometers and kilometers/second
            covariance in kilometers & kilometers/second
        """

        

        if frame == 'ITRF':
            target_frame = FramesFactory.getITRF(Predefined.ITRF_2014, True)
        else:
            frame_string = "FramesFactory.get" + frame + "()"
            initial_frame = eval(frame_string)
        
        target_frame = FramesFactory.getEME2000()

        # Convert inputs to meters
        utc = TimeScalesFactory.getUTC()
        date = pd.to_datetime(date)
        absdate = AbsoluteDate(date.year, date.month, date.day,
                            date.hour, date.minute, date.second + date.microsecond / 1e6,
                            utc)

        position_initial = Vector3D(float(x)*1000, float(y)*1000, float(z)*1000)
        velocity_initial = Vector3D(float(vx)*1000, float(vy)*1000, float(vz)* 1000)

        pv_initial = PVCoordinates(position_initial, velocity_initial)

        # Get the transform
        transform = initial_frame.getTransformTo(target_frame, absdate)

        # Apply the transformation
        pv_J2000 = transform.transformPVCoordinates(pv_initial)

        # Return position and velocity in J2000
        pos_J2000 = pv_J2000.getPosition()
        vel_J2000 = pv_J2000.getVelocity()

        ################## Covariance Conversion 
        cov = cov * 1e9
        cov_data = cov.tolist()

        num_rows = len(cov_data)
        num_cols = len(cov_data[0]) if num_rows > 0 else 0

        # Create an empty Array2DRowRealMatrix using its dimensions constructor
        initial_covariance = Array2DRowRealMatrix(num_rows, num_cols)

        # Manually fill the matrix entries
        for i in range(num_rows):
            for j in range(num_cols):
                initial_covariance.setEntry(i, j, cov_data[i][j])

        state_cov = StateCovariance(initial_covariance, absdate, initial_frame,  OrbitType.CARTESIAN, PositionAngleType.TRUE) 
        
        earth = CelestialBodyFactory.getEarth()
        mu = earth.getGM()  # [m^3/s^2]

        state_orbit = CartesianOrbit(pv_initial, initial_frame, absdate, mu)
        change_state_cov = state_cov.changeCovarianceFrame(state_orbit,target_frame )
        Cov_array = change_state_cov.getMatrix()
        
        output_cov = np.zeros((num_rows, num_cols))
        # Manually fill the matrix entries
        for i in range(num_rows):
            for j in range(num_cols):
                output_cov[i,j] = Cov_array.getEntry(i,j)
        
        output_cov = output_cov / 1e9

        return np.array([pos_J2000.getX(), pos_J2000.getY(),pos_J2000.getZ(),
                        vel_J2000.getX(),vel_J2000.getY(),vel_J2000.getZ()])/1000, output_cov
                        
    df = ref_orbit
    df = generateCov(df)

    if 'referenceFrame' in df.columns:

        TEME_match = np.array(df[df['referenceFrame'] == 'TEME'].index.tolist()).astype(int)
        for i in TEME_match: # Convert TEME --> J2000 
            PosVel, Covariance = convert_to_j2000(df.at[i,'xpos'],
                                df.at[i,'ypos'],
                                df.at[i,'zpos'],
                                df.at[i,'xvel'],
                                df.at[i,'yvel'],
                                df.at[i,'zvel'],
                                df.at[i, 'epoch'],
                                df.at[i, 'cov_matrix'], 'TEME')
            df.loc[i, ['xpos', 'ypos','zpos','xvel','yvel','zvel']] = PosVel
            df.at[i,'cov_matrix'] = Covariance
        

        GCRF_match = np.array(df[df['referenceFrame'] == 'GCRF'].index.tolist()).astype(int)
        for i in GCRF_match: # Convert GCRF --> J2000 
            PosVel, Covariance = convert_to_j2000(df.at[i,'xpos'],
                                df.at[i,'ypos'],
                                df.at[i,'zpos'],
                                df.at[i,'xvel'],
                                df.at[i,'yvel'],
                                df.at[i,'zvel'],
                                df.at[i, 'epoch'],
                                df.at[i, 'cov_matrix'], 'GCRF')
            df.loc[i, ['xpos', 'ypos','zpos','xvel','yvel','zvel']] = PosVel
            df.at[i,'cov_matrix'] = Covariance


        ITRF_match = np.array(df[df['referenceFrame'] == 'ITRF'].index.tolist()).astype(int)
        for i in ITRF_match: # Convert ITRF --> J2000 
            PosVel, Covariance = convert_to_j2000(df.at[i,'xpos'],
                                df.at[i,'ypos'],
                                df.at[i,'zpos'],
                                df.at[i,'xvel'],
                                df.at[i,'yvel'],
                                df.at[i,'zvel'],
                                df.at[i, 'epoch'],
                                df.at[i, 'cov_matrix'], 'ITRF')
            df.loc[i, ['xpos', 'ypos','zpos','xvel','yvel','zvel']] = PosVel
            df.at[i,'cov_matrix'] = Covariance

        ECEF_match = np.array(df[df['referenceFrame'] == 'ECR/ECEF'].index.tolist()).astype(int)
        for i in ITRF_match: # Convert ECR/ECEF --> J2000 
            PosVel, Covariance = convert_to_j2000(df.at[i,'xpos'],
                                df.at[i,'ypos'],
                                df.at[i,'zpos'],
                                df.at[i,'xvel'],
                                df.at[i,'yvel'],
                                df.at[i,'zvel'],
                                df.at[i, 'epoch'],
                                df.at[i, 'cov_matrix'], 'ITRF')
            df.loc[i, ['xpos', 'ypos','zpos','xvel','yvel','zvel']] = PosVel
            df.at[i,'cov_matrix'] = Covariance

        TDR_match = np.array(df[df['referenceFrame'] == 'EFG/TDR'].index.tolist()).astype(int)
        for i in ITRF_match: # Convert EFG/TDR --> J2000 
            PosVel, Covariance = convert_to_j2000(df.at[i,'xpos'],
                                df.at[i,'ypos'],
                                df.at[i,'zpos'],
                                df.at[i,'xvel'],
                                df.at[i,'yvel'],
                                df.at[i,'zvel'],
                                df.at[i, 'epoch'],
                                df.at[i, 'cov_matrix'], 'ITRF')
            df.loc[i, ['xpos', 'ypos','zpos','xvel','yvel','zvel']] = PosVel
            df.at[i,'cov_matrix'] = Covariance




        # Update pd array to reflect converted coordinates
        df['referenceFrame'] = 'J2000'
        df['covReferenceFrame'] = 'J2000'


    else:
        print("Warning: Column does not exist. I'm gonna make them <3")
        position = df.columns.get_loc('origNetwork') + 1  # get index of 'name' and add 1
        position_cov = df.columns.get_loc('origNetwork') + 2  # get index of 'name' and add 1
        df.insert(position, 'referenceFrame', 'J2000')
        df.insert(position_cov, 'covReferenceFrame', 'J2000')


    epoch = df['epoch']
    position = df[['xpos','ypos', 'zpos']]
    velocity = df[['xvel','yvel', 'zvel']]

    return df
