# -*- coding: utf-8 -*-
"""
Created on Mon Jun 30 2025

@author: Louis Caves
"""

import libraries.config as config

# Define Functions for simulating observations from TLE or state vector
def simulateObs(input1, input2, timespan, sensorsDataFrame, positionNoise=config.positionNoise, angularNoise=config.angularNoise, step=10.0, satelliteParameters=[99999, 0, 0]):
    """
    Simulate RA/Dec observations from TLE using Orekit-generated ephemeris.

    Parameters:
    input1: state vector (6x1 np.array) OR TLE line 1 (string)
    input2: Epoch of state vector (datetime) OR TLE line 2 (string)
    timespan (float OR datetime list): Duration in seconds from to simulate obs for OR list of epochs to simulate observations at.
    sensorsDataFrame (pd.DataFrame): DataFrame containing sensor information with columns ['idSensor', 'senlat', 'senlon', 'senalt', 'sensorLikelihood'].
    positionNoise (float): Standard deviation of the position noise in meters (default is 0).
    angularNoise (float): Standard deviation of the angular noise in degrees (default is 1/3600 or 1 arcsecond).
    step (float): Sampling interval in seconds (default is 10s).
    satelliteParameters (list): List of satellite parameters [satNo, mass, cross-sectional area] (default is [99999, 0, 0]), only used for state vector input.

    Returns:
    pandas dataframe in UDL EOobs schema: 
    """
    import numpy as np
    import pandas as pd
    import uuid
    from datetime import datetime, timezone

    # Use ephemeris propagator functions that already exists
    if isinstance(input1, str): # TLE input
        # Convert timespan (in seconds) to a list of datetime objects centered on epoch if necessary
        if isinstance(timespan,list):
            datetimeList = timespan
        else:
        # Must extract epoch from TLE and convert to datetime
            epoch = extractTLEepoch(input1)  # Extract epoch from TLE line 1
            datetimeList = epochTimespan2DatetimeList(epoch, timespan, step)
        # Generate list of propagated state vectors using ephmerisPropagator
        _, _, propagatedStates = TLEpropagator(input1, input2, datetimeList) # state vectors are 3rd output of TLEpropagator
        satNo = int(input1[2:7])  # Extract satellite number from TLE line 1

    else: # State vector input
        # Convert timespan (in seconds) to a list of datetime objects centered on epochif necessary
        if isinstance(timespan,list):
            datetimeList = timespan
        else:
            datetimeList = epochTimespan2DatetimeList(input2, timespan, step)
        # Generate list of propagated state vectors using ephmerisPropagator
        satNo = satelliteParameters[0]  # Extract satellite number from parameters
        satelliteParameters = satelliteParameters[1:] + [0,0]
        propagatedStates = ephemerisPropagator(input1, input2, datetimeList, satelliteParameters=satelliteParameters)


    # Sample from both ephemerides
    results = []
    nSteps = len(propagatedStates)

    # Number of observations to simulate for each sensor
    groupSize = 3

    for i in range(nSteps):
        tstring = datetimeList[i].astimezone(timezone.utc).isoformat()
        x, y, z = propagatedStates[i][0:3]  # Extract position from propagated state vector
        x = float(x) + np.random.normal(0, positionNoise)
        y = float(y) + np.random.normal(0, positionNoise)
        z = float(z) + np.random.normal(0, positionNoise)
        r = np.linalg.norm([x, y, z])
        ra = (float(np.arctan2(y, x) % (2 * np.pi)) * 180.0 / np.pi) + np.random.normal(0, angularNoise)
        dec = (float(np.arcsin(z / r)) * 180.0 / np.pi) + np.random.normal(0, angularNoise)
        rangeVal = np.linalg.norm([x, y, z])  # Range in meters
        # Pick a random sensor to simulate observations for (but keep constant for debugging purposes)
        # Sample sensor every group_size observations
        if i % groupSize == 0:
            randomSensor = sensorsDataFrame.sample(weights='count', random_state=None).iloc[0]
            sensorPosition = randomSensor[['senlat', 'senlon', 'senalt']].tolist()
            sensorID = randomSensor['idSensor']
        az, el = radec2azel(ra, dec, rangeVal, sensorPosition, datetimeList[i]) # Convert RA/Dec to azimuth/elevation
        triedSensors = set()
        while (el<6): # If elevation is less than 6 degrees, try another sensor
            triedSensors.add(sensorID)
            availableSensors = sensorsDataFrame[sensorsDataFrame['idSensor'].isin(triedSensors) == False]
            if availableSensors.empty:
                break
            randomSensor = availableSensors.sample(weights='count', random_state=None).iloc[0]
            sensorPosition = randomSensor[['senlat', 'senlon', 'senalt']].tolist()
            sensorID = randomSensor['idSensor']
            az, el = radec2azel(ra, dec, rangeVal, sensorPosition, datetimeList[i]) # Convert RA/Dec to azimuth/elevation
        if(el >= 6): # Only save observation if there is a valid elevation angle          
            results.append((tstring, ra, dec, sensorID,sensorPosition[0], sensorPosition[1], sensorPosition[2], az, el, rangeVal))

    df = toObsSchema(results,satNo=satNo,noiseCharacteristics=angularNoise)

    return df

def extractTLEepoch(tle_line1):
    '''
    Extract the epoch from a TLE line 1 string and convert it to a datetime object.
    Args:
        tle_line1 (str): The first line of a TLE string.
    Returns:
        epoch (datetime): The epoch as a datetime object.
    '''
    from datetime import datetime, timedelta
    # Extract epoch year and day of year
    epoch_year = int(tle_line1[18:20])
    epoch_day = float(tle_line1[20:32])

    # Convert year to full year (assumes 2000–2099 range)
    full_year = 2000 + epoch_year if epoch_year < 57 else 1900 + epoch_year

    # Build datetime from year and day-of-year
    epoch_datetime = datetime(full_year, 1, 1) + timedelta(days=epoch_day - 1)
    return epoch_datetime

def datetime2AbsDate(datetime_obj,utc):
    """
    Convert a Python datetime object to an Orekit AbsoluteDate object.
    
    Args:
        datetime_obj (datetime): The datetime object to convert.
        
    Returns:
        AbsoluteDate: The corresponding Orekit AbsoluteDate object.
    """
    from org.orekit.time import AbsoluteDate, TimeScalesFactory

    #utc = TimeScalesFactory.getUTC()
    return AbsoluteDate(
        datetime_obj.year, 
        datetime_obj.month, 
        datetime_obj.day, 
        datetime_obj.hour, 
        datetime_obj.minute, 
        datetime_obj.second + datetime_obj.microsecond / 1e6,  # convert microseconds to fractional seconds
        utc
    )   

def epochTimespan2DatetimeList(epoch, timespan, step = 10):
    """
    Generate a list of datetime objects centered on the given epoch.
    
    Parameters:
    - epoch: datetime object representing the center time.
    - timespan: total span in seconds (symmetric around the epoch).
    - step: interval between datetime entries in seconds (default 10).
    
    Returns:
    - List of datetime objects.
    """
    from datetime import timedelta, datetime
    half_span = int(timespan // 2)
    return [epoch + timedelta(seconds=i) for i in range(-half_span, half_span + 1, int(step))] 

def radec2azel(ra_deg, dec_deg, rangeVal, sensorPosition, obs_time):
    """
    Convert Right Ascension and Declination to Azimuth and Elevation.

    Parameters
    ----------
    ra (float):  Right Ascension in degrees (J2000).
    dec (float): Declination in degrees (J2000).
    range (float): Range to the object in kilometers
    sensorPosition (list): sensorLat (deg), sensorLon(deg), sensorAlt (km) 
    obs_time (datetime): Observation time in UTC.

    Returns
    -------
    azimuth (float): Azimuth angle in degrees (0° = North, 90° = East).
    elevation (float): Elevation angle in degrees above the horizon.

    Notes
    -----
    This conversion accounts for the Earth's rotation and observer position at the given time.
    Assumes geodetic coordinates for the observer and equatorial coordinates for the RA/Dec input.
    """
    from org.orekit.utils import PVCoordinates
    from org.orekit.bodies import GeodeticPoint, OneAxisEllipsoid, BodyShape
    from org.orekit.frames import FramesFactory, TopocentricFrame
    from org.orekit.time import AbsoluteDate, TimeScalesFactory
    from org.orekit.utils import Constants
    from org.hipparchus.geometry.euclidean.threed import Vector3D
    from org.orekit.utils import IERSConventions
    import numpy as np

    # Unpack sensor position
    obs_lat = sensorPosition[0]  # Latitude in degrees
    obs_lon = sensorPosition[1]  # Longitude in degrees
    obs_alt_km = sensorPosition[2]  # Altitude in kilometers
    
    # RA/Dec to unit vector
    ra_rad = float(np.radians(ra_deg))
    dec_rad = float(np.radians(dec_deg))
    x = np.cos(dec_rad) * np.cos(ra_rad)
    y = np.cos(dec_rad) * np.sin(ra_rad)
    z = np.sin(dec_rad)
    radec_vec = Vector3D(float(x), float(y), float(z))

    # Convert range if necessary
    if rangeVal <500000:  # If range is less than 500,000 km, assume it's in kilometers
        rangeVal = float(rangeVal*1000)
    
    raDecRange = radec_vec.scalarMultiply(float(rangeVal))  # Scale unit vector by range

    # Time
    utc = TimeScalesFactory.getUTC()
    if isinstance(obs_time, datetime):
        obs_date = AbsoluteDate(obs_time.year, obs_time.month, obs_time.day,
                                obs_time.hour, obs_time.minute, obs_time.second + obs_time.microsecond / 1e6, utc)
    else:
        obs_date = obs_time  # already an AbsoluteDate

    # Observer frame
    earth = OneAxisEllipsoid(Constants.WGS84_EARTH_EQUATORIAL_RADIUS,
                              Constants.WGS84_EARTH_FLATTENING,
                              FramesFactory.getITRF(IERSConventions.IERS_2010, True))
    geo = GeodeticPoint(float(np.radians(obs_lat)), float(np.radians(obs_lon)), float(obs_alt_km * 1000))
    topo = TopocentricFrame(earth, geo, "observer")

    # Convert to az/el
    az = np.degrees(topo.getAzimuth(raDecRange, FramesFactory.getEME2000(), obs_date))
    el = np.degrees(topo.getElevation(raDecRange, FramesFactory.getEME2000(), obs_date))

    return az, el

def toObsSchema(results, satNo, noiseCharacteristics):
    """
    Convert results to observation schema.

    Parameters:
    results (np array): List of tuples (AbsoluteDate, RA [deg], Dec [deg]).
    satNo (int): Satellite number.
    noiseCharacteristics (float): Standard deviation of the noise [deg].
    AzEl (list): List of tuples (sensorID, sensorLat, sensorLon, sensorAlt, azimuth [deg], elevation [deg]) if available.

    Returns:
    pd.DataFrame: DataFrame with columns ['satNo', 'time', 'ra', 'dec'].
    """
    import uuid
    import pandas as pd
    import numpy as np
    from datetime import datetime, timezone
    # convert to pandas DataFrame with necessary columns
    #satNo = int(TLEline1[2:7])
    df = pd.DataFrame([{
        "id": str(uuid.uuid4()),
        "classificationMarking": "U//LOU-SIM",
        "obTime": ts + "Z",
        "idOnOrbit": str(satNo),
        "idSensor": sensorID + "_SIM",
        "satNo": satNo,
        "taskId": "0",
        "origObjectId": "Sim",
        "origSensorId": int(sensorID[3:]),
        "uct": False,
        "azimuth": float(Az),
        "elevation": float(El),
        "range": float(rangeVal),
        "ra": float(ra),
        "declination": float(dec),
        "losUnc": np.nan,
        "senlat": float(senLat),
        "senlon": float(senLon),
        "senalt": float(senAlt),
        "senx": np.nan,
        "seny": np.nan,
        "senz": np.nan,
        "senvelx": np.nan,
        "senvely": np.nan,
        "senvelz": np.nan,
        "expDuration": np.nan,
        "zeroptd": np.nan,
        "netObjSig": np.nan,
        "netObjSigUnc": np.nan,
        "mag": np.nan,
        "magUnc": np.nan,
        "geolat": np.nan,
        "geolon": np.nan,
        "geoalt": np.nan,
        "georange": np.nan,
        "solarPhaseAngle": np.nan,
        "solarEqPhaseAngle": np.nan,
        "solarDecAngle": np.nan,
        "shutterDelay": 0,
        "sensorStDev": noiseCharacteristics,
        "rawFileURI": "",
        "source": "LOU",
        "dataMode": "SIMULATED",
        "createdAt": datetime.now(timezone.utc).isoformat() + "Z",
        "createdBy": "LOU",
        "origNetwork": "N/A",
        "type": "OPTICAL"
    } for ts, ra, dec, sensorID, senLat, senLon, senAlt, Az, El, rangeVal in results])
    
    return df

# Funciton not finished, need to loop thru to find when enough epochs added to simlist
# one iteration implemented but not tested
def epochsToSim(satNo,satObs,orbElems):
    '''
    Function to determine what epochs opbervations need to be simulated at for each satellite
    Inputs:
        satNo: NORAD ID of satellite data being simulated for
        satObs: list of observations for the given satellite
        orbElems: dict with orbital Elements, orbital coverage, track gap, etc for given satNo
        
    Outputs:
        epochs[list]: list of times to be simmed at
        '''
    epochs = []

    # if has long track gap, preserve long gap
    if orbElems['Max Track Gap'] > config.longTrackGap:
        # find gap
        satObs['obTime'] = pd.to_datetime(satObs['obTime'], format='%Y-%m-%dT%H:%M:%S.%fZ')
        satObs = satObs.sort_values(by='obTime').reset_index(drop=True)
        timeDeltas = (satObs['obTime'].diff())
        maxGap = timeDeltas.max()
        timeDeltas = timeDeltas[timeDeltas != maxGap]
        idx = timeDeltas.idxmax()
        startTime, endTime = satObs['obTime'][idx-1:idx+1]

    # find midpoint between (next) longest track gap
    idxSecond = timeDeltas[timeDeltas != timeDeltas.max()].idxmax()
    start, end = satObs['obTime'][idxSecond-1:idxSecond+1]
    midpoint = (start + (end-start)/2).to_pydatetime()
    epochs.append(midpoint)

    # Find orbital coverage added by simulated point
    # eccentricity and semimajor
    a = orbElems['Semi-Major Axis']
    e = orbElems['Eccentricity']

    # location of first vertex
    temp = orbElems['Orbital Polygon']
    temp2 = temp[temp['id']==satObs.iloc[idxSecond]['id']]
    x1 = float(temp2['x'].values[0])
    x1C = x1-a*e
    y1 = float(temp2['y'].values[0])
    r1 = np.sqrt(x1C**2+y1**2)
    theta1 = np.arctan2(y1,x1C)

    # location of second vertex
    temp = orbElems['Orbital Polygon']
    temp2 = temp[temp['id']==satObs.iloc[idxSecond-1]['id']]
    x2 = float(temp2['x'].values[0])
    x2C = x2-a*e # shift origin to geometric center of circle from focus of ellipse
    y2 = float(temp2['y'].values[0])
    r2 = np.sqrt(x2C**2+y2**2)
    theta2 = np.arctan2(y2,x2C)

    # location of simulated vertex
    thetaMid = (theta1 + theta2)/2
    rMid = (r1+r2)/2
    xMid = rMid * np.cos(thetaMid)
    yMid = rMid * np.sin(thetaMid)

    # Area of triangle made by three verticies
    def triangleArea(x1, y1, x2, y2, x3, y3):
        area = abs(x1*(y2 - y3) + x2*(y3 - y1) + x3*(y1 - y2)) / 2
        return float(area)
    areaAdded = triangleArea(x1C,y1,x2C,y2,xMid,yMid)
    coverageAdded = areaAdded/(2*np.pi*a) # Normalize area of triangle by area of great circle

# Test Cases
if __name__ == "__main__":
    import numpy as np
    from datetime import datetime, timedelta
    import pandas as pd
    from propagator import TLEpropagator, ephemerisPropagator

    # Read in sensor data
    sensorCountsDf = pd.read_csv("data\\sensorCounts.csv")

    # Define test case
    testcase = "SV2"
    if testcase == "TLE":
        input1 = "1 25544U 98067A   21275.54791667  .00001264  00000-0  33463-4 0  9993"
        input2 = "2 25544  51.6455  15.0426 0002957  36.8858 323.2219 15.48920000300102"
        satelliteParameters = [99999, 0, 0]  # Dummy parameters for TLE (not used)
        timespan = 3600  # 1 hour in seconds

    elif testcase == "SV":
        input1 = np.array([-600000, -3700000, 50000000, 5659, -4211, -3616])
        input2 = datetime(2021, 10, 2, 13, 8, 57, 360000)
        satelliteParameters = [99999, 1000, 10]  # Example parameters: [satNo, mass, cross-sectional area]
        timespan = 3600

    elif testcase == "SV2":
        input1 = np.array([-600000, -3700000, 50000000, 5659, -4211, -3616])
        input2 = datetime(2021, 10, 2, 13, 8, 57, 360000)
        timespan = [datetime(2021, 10, 2, 13, 8, 57, 360000) + timedelta(seconds=i) for i in range(0, 3600, 10)]
        satelliteParameters = [99999, 1000, 10]  # Example parameters: [satNo, mass, cross-sectional area]


    results = simulateObs(input1, input2, 3600, sensorCountsDf, positionNoise=0, angularNoise=1/3600, step=10.0, satelliteParameters=satelliteParameters)

    results.to_csv("data\\simulated_observations.csv", index=False)