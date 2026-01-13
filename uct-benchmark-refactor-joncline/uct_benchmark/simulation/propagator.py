# -*- coding: utf-8 -*-
"""
Created on Wed Jul 2 2025

@author: Louis Caves & Binyamin Stivi
"""

# Import varaibles from config file
import uct_benchmark.config as config


def monteCarloPropagator(
    stateVector,
    covariance,
    initialEpoch,
    finalEpoch,
    N=0,
    satelliteParameters=[1000, 13.873, 0, 0],
):
    """
    Function to propagate state vector and covariance using Monte Carlo Simulation with a specified number of sample points
    Inputs:
    stateVector: 6x1 numpy array [x,y,z,vx,vy,vz] in J2000 ECI Frame
    covariance: 6x6 numby array, value is arbitrary if N=0
    initialEpoch: datetime object giving epoch of state vector and covariance
    finalEpoch: datetime object giving epoch to propagate state vector to
    N: number of sample points for Monte Carlo simulation (default=0), no covariance output for N=0
    satelliteParameters: list of [satellite mass,crossSectionalArea]

    Outputs
    finalStateVector: 6x1 numpy array, state vector at final epoch
    finalCovariance (if N>1): 6x6 numpy array, covariance of sample points at finalEpoch

    Dependencies
    numpy
    datetime
    orekit - function will initialize orekit VM and load current parameters
    """


    import numpy as np

    # unpack parameters list
    satelliteMass, crossSectionalArea, dragCoefficient, solarCoefficient = satelliteParameters
    dragCoefficient = config.dragCoef  # Default drag coefficient
    solarCoefficient = config.solarRadPresCoef  # Default solar radiation pressure coefficient
    # Set perterbations to 0 if no mass or area given
    if satelliteMass == 0 or crossSectionalArea == 0:
        satelliteMass = 1000.0
        crossSectionalArea = 10.0
        dragCoefficient = 0.0
        solarCoefficient = 0.0
    # Typecast inputs to floats
    satelliteMass = float(satelliteMass)
    crossSectionalArea = float(crossSectionalArea)
    dragCoefficient = float(dragCoefficient)
    solarCoefficient = float(solarCoefficient)
    # Convert km to meters if necessary (if radius < 100,000)
    convertFlag = False
    if np.linalg.norm(stateVector[0:3]) < 100000:
        stateVector = stateVector * 1000
        covariance = 1e9 * covariance
        convertFlag = True

    # Set up orekit enviornment, import orekit classes
    import orekit
    from orekit.pyhelpers import setup_orekit_curdir

    orekit.initVM()
    setup_orekit_curdir()

    # orekit class imports
    from org.hipparchus.geometry.euclidean.threed import Vector3D
    from org.hipparchus.ode.nonstiff import DormandPrince853Integrator
    from org.orekit.bodies import CelestialBodyFactory, OneAxisEllipsoid
    from org.orekit.forces.drag import DragForce, IsotropicDrag
    from org.orekit.forces.gravity import HolmesFeatherstoneAttractionModel, ThirdBodyAttraction
    from org.orekit.forces.gravity.potential import GravityFieldFactory
    from org.orekit.forces.radiation import (
        IsotropicRadiationSingleCoefficient,
        SolarRadiationPressure,
    )
    from org.orekit.frames import FramesFactory
    from org.orekit.models.earth.atmosphere import NRLMSISE00
    from org.orekit.models.earth.atmosphere.data import CssiSpaceWeatherData
    from org.orekit.orbits import CartesianOrbit, OrbitType
    from org.orekit.propagation import SpacecraftState
    from org.orekit.propagation.numerical import NumericalPropagator
    from org.orekit.time import TimeScalesFactory
    from org.orekit.utils import Constants, IERSConventions, PVCoordinates

    # Convert Python datetime to orekit AbsoluteDate
    utc = TimeScalesFactory.getUTC()
    initialAbsDate = datetime2AbsDate(initialEpoch, utc)

    finalAbsDate = datetime2AbsDate(finalEpoch, utc)

    # define constant(s) and reference frame from orekit
    mu = Constants.WGS84_EARTH_MU
    inertial_frame = FramesFactory.getEME2000()  # Or GCRF, J2000, etc.

    # Rotating Reference Earth
    # Preferred: ITRF for WGS84 ellipsoid
    itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, True)

    earth = OneAxisEllipsoid(
        Constants.WGS84_EARTH_EQUATORIAL_RADIUS, Constants.WGS84_EARTH_FLATTENING, itrf
    )

    # Set up numerical integrator (tolerances can be changed to arguments if needed)
    minStep = 0.0001
    maxStep = 1000.0

    # Create Vector3D objects for position and velocity
    initial_position = Vector3D(
        float(stateVector[0]), float(stateVector[1]), float(stateVector[2])
    )
    initial_velocity = Vector3D(
        float(stateVector[3]), float(stateVector[4]), float(stateVector[5])
    )
    initial_pv = PVCoordinates(initial_position, initial_velocity)
    initial_orbit = CartesianOrbit(initial_pv, inertial_frame, initialAbsDate, mu)
    initial_state = SpacecraftState(initial_orbit, float(satelliteMass))

    # Set tolerances and define integrator type
    integrator = DormandPrince853Integrator(minStep, maxStep, 10e-14, 10e-12)

    propagator_num = NumericalPropagator(integrator)
    propagator_num.setOrbitType(OrbitType.CARTESIAN)

    # Define Force Model
    # Earth gravity + harmonics
    gravityProvider = GravityFieldFactory.getNormalizedProvider(120, 120)
    propagator_num.addForceModel(
        HolmesFeatherstoneAttractionModel(
            FramesFactory.getITRF(IERSConventions.IERS_2010, True), gravityProvider
        )
    )
    # Add third-body perturbations
    sun = CelestialBodyFactory.getSun()
    moon = CelestialBodyFactory.getMoon()
    propagator_num.addForceModel(ThirdBodyAttraction(sun))
    propagator_num.addForceModel(ThirdBodyAttraction(moon))
    # Atmospheric Drag
    cswl = CssiSpaceWeatherData("SpaceWeather-All-v1.2.txt")
    atmosphere = NRLMSISE00(cswl, sun, earth)
    isotropic_drag = IsotropicDrag(crossSectionalArea, dragCoefficient)
    drag_force = DragForce(atmosphere, isotropic_drag)
    propagator_num.addForceModel(drag_force)
    # Solar Radiation Pressure
    srp = SolarRadiationPressure(
        CelestialBodyFactory.getSun(),
        earth,
        IsotropicRadiationSingleCoefficient(crossSectionalArea, solarCoefficient),
    )
    propagator_num.addForceModel(srp)

    # Propagate mean state vector
    propagator_num.setInitialState(initial_state)
    finalMeanState = propagator_num.propagate(finalAbsDate)
    pvT = finalMeanState.getPVCoordinates()
    finalStateVector = np.concatenate(
        (np.array(pvT.getPosition().toArray()), np.array(pvT.getVelocity().toArray()))
    )
    # Convert back to km if initial state was given in km
    if convertFlag:
        finalStateVector = 1e-3 * finalStateVector

    # Propagate Monte Carlo Sample points
    if N > 1:
        # Sample Points from Initial distribution
        MCpoints = np.random.multivariate_normal(stateVector, covariance, N)
        MCstates = []
        failedProps = 0
        for state_vector in MCpoints:
            try:  # Catch inside ellipsoid errors (satellite decays to inside earth radius)
                # Set initial state for each sample point
                initial_position = Vector3D(
                    float(state_vector[0]), float(state_vector[1]), float(state_vector[2])
                )
                initial_velocity = Vector3D(
                    float(state_vector[3]), float(state_vector[4]), float(state_vector[5])
                )
                initial_pv = PVCoordinates(initial_position, initial_velocity)
                initial_orbit = CartesianOrbit(initial_pv, inertial_frame, initialAbsDate, mu)
                initial_state = SpacecraftState(initial_orbit, float(satelliteMass))
                propagator_num.setInitialState(initial_state)

                # Propagate state and recover state vectors
                finalMCstate = propagator_num.propagate(finalAbsDate)
                pvT = finalMCstate.getPVCoordinates()
                MCstates.append(
                    np.concatenate(
                        (
                            np.array(pvT.getPosition().toArray()),
                            np.array(pvT.getVelocity().toArray()),
                        )
                    )
                )
            except orekit.JavaError:  # Skip failed point, continue with rest of sample point
                failedProps += 1
                continue
        # print(failedProps)
        if not MCstates:  # Check if MCstates is empty (all propagations failed)
            finalCovariance = 0
        else:
            finalCovariance = np.cov(np.array(MCstates).transpose())

        # Conver Covariance if necessary (m^2 -> km^2)
        if convertFlag:
            finalCovariance = 1e-9 * finalCovariance
        # Return final state vector and covariance
        return finalStateVector, finalCovariance
    else:
        return finalStateVector


def ephemerisPropagator(
    stateVector, initialEpoch, finalEpoch, satelliteParameters=[1000, 13.873, 0, 0]
):
    """
    Function to propagate state vector to multiple epochs using Orekit Ephemeris Propagator
    Inputs:
    stateVector: 6x1 numpy array [x,y,z,vx,vy,vz] in J2000 ECI Frame
    initialEpoch: datetime object giving epoch of state vector and covariance
    finalEpoch: list of datetime object giving epoch to propagate state vector to
    satelliteParameters: list of [satellite mass,crossSectionalArea,dragCoefficient,solarCoefficient]

    Outputs
    StateList: list of state vectors at each epoch in finalEpoch, each state vector is a 6x1 numpy array

    Dependencies
    numpy
    datetime
    orekit - function will initialize orekit VM and load current parameters
    """

    import numpy as np

    # unpack parameters list
    satelliteMass, crossSectionalArea, dragCoefficient, solarCoefficient = satelliteParameters
    dragCoefficient = config.dragCoef  # Default drag coefficient for boxwing satellite
    solarCoefficient = (
        config.solarRadPresCoef
    )  # Default solar radiation pressure coefficient for boxwing
    # Set perterbations to 0 is mass or area not given
    if satelliteMass == 0 or crossSectionalArea == 0:
        satelliteMass = 1000.0
        crossSectionalArea = 10.0
        dragCoefficient = 0.0
        solarCoefficient = 0.0
    # Typecast inputs to floats
    satelliteMass = float(satelliteMass)
    crossSectionalArea = float(crossSectionalArea)
    dragCoefficient = float(dragCoefficient)
    solarCoefficient = float(solarCoefficient)
    # Convert km to meters if necessary (if radius < 100,000)
    convertFlag = False
    if np.linalg.norm(stateVector[0:3]) < 100000:
        stateVector = stateVector * 1000
        convertFlag = True

    # Set up orekit enviornment, import orekit classes
    import orekit
    from orekit.pyhelpers import setup_orekit_curdir

    orekit.initVM()
    setup_orekit_curdir()

    # orekit class imports
    from org.hipparchus.geometry.euclidean.threed import Vector3D
    from org.hipparchus.ode.nonstiff import DormandPrince853Integrator
    from org.orekit.bodies import CelestialBodyFactory, OneAxisEllipsoid
    from org.orekit.forces.drag import DragForce, IsotropicDrag
    from org.orekit.forces.gravity import HolmesFeatherstoneAttractionModel, ThirdBodyAttraction
    from org.orekit.forces.gravity.potential import GravityFieldFactory
    from org.orekit.forces.radiation import (
        IsotropicRadiationSingleCoefficient,
        SolarRadiationPressure,
    )
    from org.orekit.frames import FramesFactory
    from org.orekit.models.earth.atmosphere import NRLMSISE00
    from org.orekit.models.earth.atmosphere.data import CssiSpaceWeatherData
    from org.orekit.orbits import CartesianOrbit, OrbitType
    from org.orekit.propagation import SpacecraftState
    from org.orekit.propagation.numerical import NumericalPropagator
    from org.orekit.time import TimeScalesFactory
    from org.orekit.utils import Constants, IERSConventions, PVCoordinates

    utc = TimeScalesFactory.getUTC()

    # Convert finalEpoch to list of AbsoluteDate objects
    if isinstance(finalEpoch, list):
        t_obs = [datetime2AbsDate(o, utc) for o in finalEpoch]
    else:
        t_obs = [datetime2AbsDate(finalEpoch, utc)]

    # Split times list into backward and forward propagation lists
    initialAbsDate = datetime2AbsDate(initialEpoch, utc)
    t_obs_before = [o for o in t_obs if o.compareTo(initialAbsDate) < 0]
    t_obs_after = [o for o in t_obs if o.compareTo(initialAbsDate) >= 0]

    # define constant(s) and reference frame from orekit
    mu = Constants.WGS84_EARTH_MU
    inertial_frame = FramesFactory.getEME2000()  # Or GCRF, J2000, etc.

    # Rotating Reference Earth
    # Preferred: ITRF for WGS84 ellipsoid
    itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, True)

    earth = OneAxisEllipsoid(
        Constants.WGS84_EARTH_EQUATORIAL_RADIUS, Constants.WGS84_EARTH_FLATTENING, itrf
    )

    # Set up numerical integrator (tolerances can be changed to arguments if needed)
    minStep = 0.0001
    maxStep = 1000.0

    # Create Vector3D objects for position and velocity
    initial_position = Vector3D(
        float(stateVector[0]), float(stateVector[1]), float(stateVector[2])
    )
    initial_velocity = Vector3D(
        float(stateVector[3]), float(stateVector[4]), float(stateVector[5])
    )
    initial_pv = PVCoordinates(initial_position, initial_velocity)
    initial_orbit = CartesianOrbit(initial_pv, inertial_frame, initialAbsDate, mu)
    initial_state = SpacecraftState(initial_orbit, float(satelliteMass))

    # Set tolerances and define integrator type
    integrator = DormandPrince853Integrator(minStep, maxStep, 10e-14, 10e-12)

    propagator_num = NumericalPropagator(integrator)
    propagator_num.setOrbitType(OrbitType.CARTESIAN)

    # Define Force Model
    # Earth gravity + harmonics
    gravityProvider = GravityFieldFactory.getNormalizedProvider(120, 120)
    propagator_num.addForceModel(
        HolmesFeatherstoneAttractionModel(
            FramesFactory.getITRF(IERSConventions.IERS_2010, True), gravityProvider
        )
    )
    # Add third-body perturbations
    sun = CelestialBodyFactory.getSun()
    moon = CelestialBodyFactory.getMoon()
    propagator_num.addForceModel(ThirdBodyAttraction(sun))
    propagator_num.addForceModel(ThirdBodyAttraction(moon))
    # Atmospheric Drag
    cswl = CssiSpaceWeatherData("SpaceWeather-All-v1.2.txt")
    atmosphere = NRLMSISE00(cswl, sun, earth)
    isotropic_drag = IsotropicDrag(crossSectionalArea, dragCoefficient)
    drag_force = DragForce(atmosphere, isotropic_drag)
    propagator_num.addForceModel(drag_force)
    # Solar Radiation Pressure
    srp = SolarRadiationPressure(
        CelestialBodyFactory.getSun(),
        earth,
        IsotropicRadiationSingleCoefficient(crossSectionalArea, solarCoefficient),
    )
    propagator_num.addForceModel(srp)

    # Set up ephemeris generator to recover multiple states at different times from a single propagation call
    ephemerisGenerator = propagator_num.getEphemerisGenerator()

    t_before_state_list = []
    t_after_state_list = []
    # Propagate forward state vector
    if t_obs_after:
        # Propagate to final time in input list
        finalAbsDate = t_obs_after[-1]
        propagator_num.setInitialState(initial_state)
        finalMeanState = propagator_num.propagate(finalAbsDate)
        ephemeris = ephemerisGenerator.getGeneratedEphemeris()
        # Recoved propagated state at all times in forward list from generated ephemeris
        for t in t_obs_after:
            state = ephemeris.propagate(t)
            pv = state.getPVCoordinates()
            stateVector = np.concatenate(
                (np.array(pv.getPosition().toArray()), np.array(pv.getVelocity().toArray()))
            )
            if convertFlag:
                stateVector = 1e-3 * stateVector
            t_after_state_list.append(stateVector)
    # Propagate backward state vector
    if t_obs_before:
        # Back propagate to first time in input list
        finalAbsDate = t_obs_before[0]
        propagator_num.setInitialState(initial_state)
        finalMeanState = propagator_num.propagate(finalAbsDate)
        ephemeris = ephemerisGenerator.getGeneratedEphemeris()
        # Recover propgagted states at all times in backward list from generated ephemeris
        for t in t_obs_before:
            state = ephemeris.propagate(t)
            pv = state.getPVCoordinates()
            stateVector = np.concatenate(
                (np.array(pv.getPosition().toArray()), np.array(pv.getVelocity().toArray()))
            )
            if convertFlag:
                stateVector = 1e-3 * stateVector
            t_before_state_list.append(stateVector)

    # Append backward and forward state lists to return a list of state vectors corresponding to the times given in input list
    return t_before_state_list + t_after_state_list


def TLEpropagator(input1, input2, finalEpoch):
    """
    Funciton to propagate a TLE using Orekit's SGP4 propagator.

    inputs:
    input1: str, first line of TLE OR 6x1 numpy array, state vector in J2000 ECI Frame
    input2: str, second line of TLE OR datetime object, epoch of state vector
    finalEpoch: list of datetime object, epoch to propagate to in chronological order

    outputs:
    finalTLEline1: list of str, first line of propagated TLE
    finalTLEline2: list of str, second line of propagated TLE
    finalStateList: list of 6x1 numpy array, state vector at each epoch in finalEpoch
    """
    import numpy as np
    import orekit

    orekit.initVM()

    from orekit.pyhelpers import setup_orekit_curdir

    setup_orekit_curdir()

    from org.orekit.frames import FramesFactory
    from org.orekit.propagation.analytical.tle import TLE, TLEPropagator
    from org.orekit.propagation.analytical.tle.generation import FixedPointTleGenerationAlgorithm
    from org.orekit.time import TimeScalesFactory

    utc = TimeScalesFactory.getUTC()

    # algorithm for converting state to TLE
    fixedPoint = FixedPointTleGenerationAlgorithm()

    # If input is a state vector, convert to TLE
    # convertFlag = False  # Unused variable
    if not isinstance(input1, str):
        stateVector = input1
        initialDateTime = input2
        # Convert km to m if necessary
        if np.linalg.norm(stateVector[0:3]) < 100000:
            stateVector = stateVector * 1000
            # convertFlag = True  # Unused variable
        # Convert state vector to TLE
        from org.hipparchus.geometry.euclidean.threed import Vector3D
        from org.orekit.orbits import CartesianOrbit
        from org.orekit.propagation import SpacecraftState
        from org.orekit.utils import Constants, PVCoordinates

        # Create AbsoluteDate from initialEpoch
        initialEpoch = datetime2AbsDate(initialDateTime, utc)
        # Create PVCoordinates from state vector
        position = Vector3D(float(stateVector[0]), float(stateVector[1]), float(stateVector[2]))
        velocity = Vector3D(float(stateVector[3]), float(stateVector[4]), float(stateVector[5]))
        pvCoordinates = PVCoordinates(position, velocity)
        # Create CartesianOrbit from PVCoordinates
        orbit = CartesianOrbit(
            pvCoordinates, FramesFactory.getEME2000(), initialEpoch, Constants.WGS84_EARTH_MU
        )
        # Create TLE from CartesianOrbit
        state = SpacecraftState(orbit)
        # Template TLE to model generated TLE after, will have the same NORADID and COSPARID
        templateLine1 = "1 99999U 23001A   25160.00000000  .00000000  00000-0  00000-0 0  9999"
        templateLine2 = "2 99999  98.0000 000.0000 0001000 000.0000 000.0000 15.00000000  9999"
        # Create TLE template
        templateTLE = TLE(templateLine1, templateLine2)
        # Generate TLE from state vector
        tle = TLE.stateToTLE(state, templateTLE, fixedPoint)

    # If input is a TLE, create orekit TLE object from inputs
    else:
        # Initialize
        tle = TLE(input1, input2)
        initialEpoch = tle.getDate()

    # Convert finalEpoch to list of AbsoluteDate objects
    if isinstance(finalEpoch, list):
        t_obs = [datetime2AbsDate(o, utc) for o in finalEpoch]
    else:
        t_obs = [datetime2AbsDate(finalEpoch, utc)]

    # Split times list into backward and forward propagation lists
    t_obs_before = [o for o in t_obs if o.compareTo(initialEpoch) < 0]
    t_obs_after = [o for o in t_obs if o.compareTo(initialEpoch) >= 0]

    # Set up TLE propagator and ephemeris generator
    propagator = TLEPropagator.selectExtrapolator(tle)
    ephemGen = propagator.getEphemerisGenerator()

    # Initialize empty lists to store propgated states in
    t_before_line1 = []
    t_before_line2 = []
    t_before_state_list = []
    t_after_line1 = []
    t_after_line2 = []
    t_after_state_list = []

    # Propagate forward TLE
    if t_obs_after:
        # Propagate to final time in input list
        finalAbsDate = t_obs_after[-1]
        finalState = propagator.propagate(finalAbsDate)
        ephemeris = ephemGen.getGeneratedEphemeris()
        # Recover states at all forward times using generated ephemeris
        for t in t_obs_after:
            state = ephemeris.propagate(t)
            finalTLE = TLE.stateToTLE(state, tle, fixedPoint)
            pv = state.getPVCoordinates()
            # Covert propagated state vector from meters to km
            stateVector = 1e-3 * np.concatenate(
                (np.array(pv.getPosition().toArray()), np.array(pv.getVelocity().toArray()))
            )
            # Save propagated TLE (line 1 and line 2 as seperate strings)
            t_after_line1.append(finalTLE.getLine1())
            t_after_line2.append(finalTLE.getLine2())
            # Save final state vector in km and km/s
            t_after_state_list.append(stateVector)
    # Propagate backward TLE
    if t_obs_before:
        # Propagate to first time in input list
        finalAbsDate = t_obs_before[0]
        finalState = propagator.propagate(finalAbsDate)
        ephemeris = ephemGen.getGeneratedEphemeris()
        # Recover states at all backward times using generated ephemeris
        for t in t_obs_before:
            state = ephemeris.propagate(t)
            finalTLE = TLE.stateToTLE(state, tle, fixedPoint)
            pv = state.getPVCoordinates()
            # Covert propagated state vector from meters to km
            stateVector = 1e-3 * np.concatenate(
                (np.array(pv.getPosition().toArray()), np.array(pv.getVelocity().toArray()))
            )
            # Save propagated TLE (line 1 and line 2 as seperate strings)
            t_before_line1.append(finalTLE.getLine1())
            t_before_line2.append(finalTLE.getLine2())
            # Save final state vector in km and km/s
            t_before_state_list.append(stateVector)

    # Append backward and forward state lists to return lists of TLEline1, TLEline2, and state vectors corresponding to the times given in input list
    return (
        t_before_line1 + t_after_line1,
        t_before_line2 + t_after_line2,
        t_before_state_list + t_after_state_list,
    )


def datetime2AbsDate(datetime_obj, utc):
    """
    Convert a Python datetime object to an Orekit AbsoluteDate object.

    Args:
        datetime_obj (datetime): The datetime object to convert.

    Returns:
        AbsoluteDate: The corresponding Orekit AbsoluteDate object.
    """
    from org.orekit.time import AbsoluteDate

    # utc = TimeScalesFactory.getUTC()
    return AbsoluteDate(
        datetime_obj.year,
        datetime_obj.month,
        datetime_obj.day,
        datetime_obj.hour,
        datetime_obj.minute,
        datetime_obj.second
        + datetime_obj.microsecond / 1e6,  # convert microseconds to fractional seconds
        utc,
    )


def orbit2OE(input1, input2):
    """
    Convert position and velocity vectors into Keplerian orbital elements using Orekit.

    Parameters:
    - input 1: State vector (6x1 numpy array) OR TLE line1 (str)
    - input 2: epoch (datetime) or TLE line2 (str)

    Returns:
    - Keplerian Orbital Elements (dict): Dictionary containing the orbital elements 'Semi-Major Axis', 'Eccentricity', 'Inclination', 'RAAN', 'Argument of Perigee', and 'Mean Anomaly'. Units are km and degrees as appropriate.
    - Period (float): Orbital Period in seconds
    """

    import numpy as np
    from org.hipparchus.geometry.euclidean.threed import Vector3D
    from org.orekit.frames import FramesFactory
    from org.orekit.orbits import CartesianOrbit, KeplerianOrbit
    from org.orekit.propagation.analytical.tle import TLE, TLEPropagator
    from org.orekit.time import TimeScalesFactory
    from org.orekit.utils import Constants, PVCoordinates

    utc = TimeScalesFactory.getUTC()

    # If TLE input, use to create Keplerian Orbit object
    if isinstance(input1, str):
        tle = TLE(input1, input2)
        initialEpoch = tle.getDate()
        propagator = TLEPropagator.selectExtrapolator(tle)
        pvCoord = propagator.getPVCoordinates(initialEpoch)
        kep_orbit = KeplerianOrbit(
            pvCoord, FramesFactory.getEME2000(), initialEpoch, Constants.WGS84_EARTH_MU
        )

    # If state vector input, used to create Keplerian Orbit object
    else:
        # Convert to meters if necessary
        stateVector = input1
        epoch = input2
        if np.linalg.norm(stateVector[:3]) < 100000:
            stateVector = stateVector * 1000.0  # Convert km to m
        # Create orekit PVcoordinates object from state vector components
        position = Vector3D(float(stateVector[0]), float(stateVector[1]), float(stateVector[2]))
        velocity = Vector3D(float(stateVector[3]), float(stateVector[4]), float(stateVector[5]))
        pvCoordinates = PVCoordinates(position, velocity)

        # Create Keplerian Orbit object from state vector and initial epoch
        initialEpoch = datetime2AbsDate(epoch, utc)
        orbit = CartesianOrbit(
            pvCoordinates, FramesFactory.getEME2000(), initialEpoch, Constants.WGS84_EARTH_MU
        )
        kep_orbit = KeplerianOrbit(orbit)

    # Find period from semi major axis using kepler laws
    period = 2 * np.pi * np.sqrt(kep_orbit.getA() ** 3 / Constants.WGS84_EARTH_MU)

    # Build return dictionary of orbital elements and period
    return {
        "Semi-Major Axis": float(kep_orbit.getA() / 1000),  # semi-major axis (meters)
        "Eccentricity": float(kep_orbit.getE()),  # eccentricity
        "Inclination": float(np.degrees(kep_orbit.getI())),  # inclination (degrees)
        "RAAN": float(np.degrees(kep_orbit.getRightAscensionOfAscendingNode())),  # RAAN (degrees)
        "Argument of Perigee": float(
            np.degrees(kep_orbit.getPerigeeArgument())
        ),  # Argument of perigee (degrees)
        "Mean Anomaly": float(np.degrees(kep_orbit.getMeanAnomaly())),  # Mean anomaly (degrees)
        "Period": float(period),
        "Epoch": initialEpoch,  # Epoch of state vector or TLE
    }


if __name__ == "__main__":
    from datetime import datetime

    import numpy as np

    testCase = "SV-tle"

    # Arbitrary Values from Orekit Example Files
    if testCase == 1:
        initialEpoch = datetime(2025, 6, 11, 12, 0, 0)
        finalEpoch = datetime(2025, 6, 11, 13, 0, 0)

        initialState = 1e3 * np.array([7000, 0, 0, 0, 7.500, 0])
        initialCov = np.array(
            [
                [10.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # dx uncertainty (e.g., 10 m^2 variance)
                [0.0, 10.0, 0.0, 0.0, 0.0, 0.0],  # dy
                [0.0, 0.0, 10.0, 0.0, 0.0, 0.0],  # dz
                [0.0, 0.0, 0.0, 0.001, 0.0, 0.0],  # dvx uncertainty (e.g., 0.001 (m/s)^2 variance)
                [0.0, 0.0, 0.0, 0.0, 0.001, 0.0],  # dvy
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.001],  # dvz
            ]
        )

    # Values from UDL, satNo 1328
    if testCase == 2:
        initialEpoch = datetime(2025, 6, 8, 8, 10, 17, 342000)
        finalEpoch = [
            datetime(2025, 6, 8, 9, 10, 17, 341000),
            datetime(2025, 6, 8, 9, 10, 17, 341500),
            datetime(2025, 6, 8, 9, 10, 17, 342500),
            datetime(2025, 6, 8, 9, 10, 17, 343000),
            datetime(2025, 6, 8, 9, 10, 17, 342000),
        ]

        initialState = 1e-3 * np.array(
            [
                -7365971.28111,
                -1331399.7084,
                1514249.14205,
                1976.71138257,
                -5225.284848027,
                4472.66176583,
            ]
        )
        initialCov = 1e9 * np.array(
            [
                [
                    2.79656e-12,
                    -1.66714e-12,
                    1.3131e-13,
                    4.48328e-13,
                    -5.45997e-9,
                    -4.98079e-12,
                ],  # dx uncertainty (e.g., 10 m^2 variance)
                [
                    -1.66714e-12,
                    1.15089e-12,
                    1.37069e-13,
                    -2.02594e-15,
                    4.86833e-10,
                    7.70187e-13,
                ],  # dy
                [
                    1.3131e-13,
                    1.37069e-13,
                    4.68529e-13,
                    4.36053e-13,
                    -4.55737e-9,
                    -3.56265e-12,
                ],  # dz
                [
                    4.48328e-13,
                    -2.02594e-15,
                    4.36053e-13,
                    5.70924e-13,
                    -5.5708e-9,
                    -4.50443e-12,
                ],  # dvx uncertainty (e.g., 0.001 (m/s)^2 variance)
                [
                    -5.45997e-9,
                    4.86833e-10,
                    -4.55737e-9,
                    -5.5708e-9,
                    0.0000647153,
                    5.25295e-8,
                ],  # dvy
                [
                    -4.98079e-12,
                    7.70187e-13,
                    -3.56265e-12,
                    -4.50443e-12,
                    5.25295e-8,
                    4.28811e-11,
                ],  # dvz
            ]
        )
        solarCoefficient = 0.0277269
        dragCoefficient = 0.067718
        satelliteMass = 55
        crossSection = 2.996

    # Values from Ben's test function satNo 22314
    if testCase == 3:
        initialEpoch = datetime(2024, 6, 17, 22, 8, 42, 425880)
        finalEpoch = datetime(2024, 6, 18, 7, 27, 12, 129134)
        initialState = np.array(
            [
                -41105.92780995852e3,
                -9050.561409355181e3,
                -1809.49929235732e3,
                0.671176665193438e3,
                -2.910029484561473e3,
                -0.741988755546521e3,
            ]
        )
        initialCov = 1e9 * np.array(
            [
                [
                    2.79656e-12,
                    -1.66714e-12,
                    1.3131e-13,
                    4.48328e-13,
                    -5.45997e-9,
                    -4.98079e-12,
                ],  # dx uncertainty (e.g., 10 m^2 variance)
                [
                    -1.66714e-12,
                    1.15089e-12,
                    1.37069e-13,
                    -2.02594e-15,
                    4.86833e-10,
                    7.70187e-13,
                ],  # dy
                [
                    1.3131e-13,
                    1.37069e-13,
                    4.68529e-13,
                    4.36053e-13,
                    -4.55737e-9,
                    -3.56265e-12,
                ],  # dz
                [
                    4.48328e-13,
                    -2.02594e-15,
                    4.36053e-13,
                    5.70924e-13,
                    -5.5708e-9,
                    -4.50443e-12,
                ],  # dvx uncertainty (e.g., 0.001 (m/s)^2 variance)
                [
                    -5.45997e-9,
                    4.86833e-10,
                    -4.55737e-9,
                    -5.5708e-9,
                    0.0000647153,
                    5.25295e-8,
                ],  # dvy
                [
                    -4.98079e-12,
                    7.70187e-13,
                    -3.56265e-12,
                    -4.50443e-12,
                    5.25295e-8,
                    4.28811e-11,
                ],  # dvz
            ]
        )
        satelliteMass = 2511.4
        crossSection = 13.873
        dragCoefficient = 0.0
        solarCoefficient = 0.0345417
        satPar = [satelliteMass, crossSection, dragCoefficient, solarCoefficient]

    if testCase == "tle":
        initialEpoch = datetime(2025, 6, 8, 8, 10, 17, 342000)
        finalEpoch = [
            datetime(2025, 6, 8, 9, 10, 17, 342000),
            datetime(2025, 6, 8, 10, 10, 17, 342000),
        ]
        TLEline1 = "1 01328U 65001A   25159.34000000  .00000000  00000-0  00000-0 0  9992"
        TLEline2 = "2 01328   13.8730  45.1234 0001234 123.4567 234.5678 15.12345678901234"

    if testCase == "SV-tle":
        initialEpoch = datetime(2025, 6, 8, 8, 10, 17, 342000)
        finalEpoch = [
            datetime(2025, 6, 8, 9, 10, 17, 342000),
            datetime(2025, 6, 8, 10, 10, 17, 342000),
        ]
        initialState = np.array(
            [
                -7365971.28111,
                -1331399.7084,
                1514249.14205,
                1976.71138257,
                -5225.284848027,
                4472.66176583,
            ]
        )
        TLEline1 = initialState
        TLEline2 = initialEpoch

    _, _, finalState = TLEpropagator(initialState, initialEpoch, finalEpoch)
    print(finalState)
    # print(finalCov)
