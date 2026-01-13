# -*- coding: utf-8 -*-
'''
gauss.py is the main driver file for TLE generation for UCTP input. To do this, the 
file calls the gaussSorter() function to find a list of states for each of the sets
of angular data passed to it in list form. The general flow is as follows:
--> Loop through each set of data
--> Generate triplets of observations
--> Call Gauss for each of the triplets and determine the state
--> Cull any outliers based on the semimajor axes
--> Return the set of culled states for TLE generation after batch filter refinement

Created: 16 July 2025

@author: Miles Puchner

Updated: 31 July 2025
'''


import numpy as np
import pandas as pd
from astropy.time import Time
import base64
from concurrent.futures import ProcessPoolExecutor
import multiprocessing


def generateTriplets(obs):
    '''
    The following function pulls triplets of observation indices to be used in Gauss' 
    IOD. It does so by using a running midpoint that spans the observations and checks 
    the angular distance between an observation before and after this midpoint. All 
    triplets whose angular separations satisfy the thresholds are saved.

    INPUTS
    obs :  dataframe containing the angular observations and epochs for that satellite, 
    relevant column titles include:
        --> "satNo" :  int of the NORAD ID
        --> "obTime" :  string of the observation epoch
        --> "ra" :  right ascension (deg)
        --> "declination" :  declination (deg)
        --> "senlon" :  sensor longitude (deg)
        --> "senlat" :  sensor latitude (deg)
        --> "senalt" :  sensor altitude (km)

    OUTPUTS
    triplets :  a list of triplet indices (in list format) that correspond to 
            observations; i.e. [[ob_a, ob_b, ob_c], ..., [ob_x, ob_y, ob_z]]
    '''
    
    # Determine number of obs
    n = len(obs)
    satNo = obs.loc[0, "satNo"]
    
    # Define flag for first pass criteria (whether or not angle criteria needs to be dropped)
    firstPass = True

    # Define the triplet function
    def tripletFunc(obs, firstPass):

        # Initialize the triplets list
        triplets = []

        # Determine midpoint index
        for mid in range(1, n):

            # Pull the ra and dec for the mid ob
            ra2 = obs.loc[mid, "ra"]
            dec2 = obs.loc[mid, "declination"]

            # For this index start looping through left
            for i in range(mid):

                # Pull the ra and dec for the first ob
                ra1 = obs.loc[i, "ra"]
                dec1 = obs.loc[i, "declination"]

                # Check angle to ensure it is within criteria
                flag = angularCheckTriplets(ra1, dec1, ra2, dec2)

                # Check if angle bounds are to be used
                if firstPass:
                    # If left side check is less than lower lower bound, stop iterating towards midpoint
                    if flag == 1: break
                    # If left side check is greater than upper bound, iterate towards midpoint
                    if flag == 2: continue

                # For this index start looping through right
                for j in range(mid+1, n):
                    
                    # Pull the ra and dec for the last ob
                    ra3 = obs.loc[j, "ra"]
                    dec3 = obs.loc[j, "declination"]

                    # Check angle to ensure it is within criteria
                    flag = angularCheckTriplets(ra2, dec2, ra3, dec3)

                    # Check if angle bounds are to be used
                    if firstPass:
                        # If right side check is less than lower bound, iterate towards end observation
                        if flag == 1: continue
                        # If right side check is greater than upper bounds, stop iterating towards end observation
                        if flag == 2: break

                    # If all angle checks are good, save triplet
                    triplets.append([i, mid, j])

        # Return the list of triplets
        return triplets
    
    # Call the triplets function to generate triplets
    triplets = tripletFunc(obs, firstPass)

    # Check if triplets were found or if angle criteria is too harsh
    if len(triplets) == 0:

        # Inform user that states could not be generated with the angle separation criteria
        print(f"STATES FOR SATELLITE {satNo} COULD NOT BE GENERATED WITH CURRENT ANGLE SEPARATIONS; CRITERIA REMOVED, EXPECT BAD STATES")

        # Update pass flag
        firstPass = False

        # Recall triplet generator
        triplets = tripletFunc(obs, firstPass)

    print(f"Number of triplets: {len(triplets)}")

    # Return the triplets
    return triplets




def angularCheckTriplets(ra1, dec1, ra2, dec2, lower_threshold = 1, upper_threshold = 30):

    '''
    The following determines if a triplet set of observations fullfills the angular 
    threshold check for optimal Gauss.

    INPUTS
    ra :  3x1 np array containing the right ascensions (deg) for the three observations
    dec :  3x1 np array containing the declinations (deg) for the three observations
    lower_threshold :  min angle between observations (deg), default 1 deg
    upper_threshold :  max angle between observations (deg), default 30 deg

    OUTPUTS
    0 :  angle between observations is within the bounds
    1 :  angle between observations is below the lower threshold
    2 :  angle between observations is above the upper threshold
    '''

    # Determine the unit vectors for each obs set
    u1 = radec2unit(ra1, dec1)
    u2 = radec2unit(ra2, dec2)

    # Determine the angular separation with the unit vectors
    ang = np.rad2deg(np.arccos(np.dot(u1.ravel(), u2.ravel())))

    # Determine if within threshold and return flag number
    if ang < lower_threshold:
        return 1
    elif ang > upper_threshold:
        return 2
    else:
        return 0




def radec2unit(ra, dec):
    '''
    The following function determines the unit vector associated with a right ascension 
    and declination pair.
    
    INPUTS
    ra :  scalar representing the right ascension (deg) for the observation
    dec :  scalar representing the declination (deg) for the obervation

    OUTPUTS
    unit vector associated with the observation
    '''

    # Convert to rads
    ra = np.deg2rad(ra)
    dec = np.deg2rad(dec)

    # Find unit vector
    x = np.cos(dec) * np.cos(ra)
    y = np.cos(dec) * np.sin(ra)
    z = np.sin(dec)

    # Return the topocentric unit vector
    return np.array([[x], [y], [z]])




def gibbs(r1, r2, r3, ut):
    '''
    The following function uses Gibbs or Herrick-Gibbs methods to determine the ECI 
    velocity vector. To do this, three position vectors corresponding to the three 
    observations are used.

    INPUTS
    r1 :  3x1 np array representing the ECI position vector of the first observation
    r2 :  3x1 np array representing the ECI position vector of the second observation
    r3 :  3x1 np array representing the ECI position vector of the third observation
    ut :  3x1 np array corresponding to the absolute time (sec) of the three 
            observations

    OUTPUTS
    r :  3x1 np array representing the ECI position vector of the second observation
    v :  3x1 np array representing the ECI velocity vector of the second observation
    '''

    # Define helpful Earth paramters
    mu = 398600.4418 # earth's gravitational parameter

    # Define helpful cross products and norms
    c23 = np.cross(r2.flatten(), r3.flatten()).reshape((3, 1))
    r1n = np.linalg.norm(r1)
    r2n = np.linalg.norm(r2)
    r3n = np.linalg.norm(r3)

    # Determine if the position vectors are coplanar
    eps = (np.dot(r1.ravel(), c23.ravel())) / (np.linalg.norm(r1) * np.linalg.norm(c23))

    # Find the angles between the position vectors
    theta_12 = np.rad2deg( np.arccos( (np.dot(r1.ravel(), r2.ravel())) / (r1n*r2n) ) )
    theta_23 = np.rad2deg( np.arccos( (np.dot(r2.ravel(), r3.ravel())) / (r2n*r3n) ) )
    
    # Determine if Gibbs requirement for coplanaraity and angle differences are met
    v2 = np.empty((3, 1))
    if (abs(eps) < 0.0349) and (theta_12 > 1) and (theta_23 > 1):

        # Determine further helpful cross products
        c12 = np.cross(r1.flatten(), r2.flatten()).reshape((3, 1))
        c31 = np.cross(r3.flatten(), r1.flatten()).reshape((3, 1))

        # Define the auxiliary vectors
        D = c23 + c31 + c12
        N = r1n*c23 + r2n*c31 + r3n*c12
        S = (r2n - r3n)*r1 + (r3n - r1n)*r2 + (r1n - r2n)*r3

        # Determine the velocity at middle observation
        v2 = np.sqrt(mu/(np.linalg.norm(N)*np.linalg.norm(D)))*(1/r2n*np.cross(D.flatten(), r2.flatten()).reshape((3, 1)) + S)
    
    # If conditions not met, use Herrick-Gibbs
    else:

        # Determine the time changes between positions
        t31 = ut[2, 0] - ut[0, 0]
        t32 = ut[2, 0] - ut[1, 0]
        t21 = ut[1, 0] - ut[0, 0]

        # Determine the velocity at the middle observation
        v2 = (
            -t32 * (1/(t21*t31) + mu/(12*r1n**3))*r1 + 
            (t32 - t21)*(1/(t21*t32) + mu/(12*r2n**3))*r2 + 
            t21*(1/(t32*t31) + mu/(12*r3n**3))*r3
        )

    # Return the state at the middle observation
    return r2, v2




def gauss(obs):
    '''
    The following function uses Gauss' IOD method to determine the state vector of an 
    orbiter given three angular observations. To do this, a dataframe of observations 
    with associated data (sat number, epoch, right asscension, declination, site coords,
    etc) is parsed and used. The function assumes that all observations within the 
    passed dataframe are for the same object.
    
    INPUTS
    obs :  dataframe containing the observations for a specific satellite, relevant 
    column titles include:
    --> "satNo" :  int of the NORAD ID
    --> "obTime" :  string of the observation epoch
    --> "ra" :  right ascension (deg)
    --> "declination" :  declination (deg)
    --> "senlon" :  sensor longitude (deg)
    --> "senlat" :  sensor latitude (deg)
    --> "senalt" :  sensor altitude (km)

    OUTPUTS
    states :  dataframe containing the NORAD ID, bae64 code of the state ID (initial 
    and final epoch used), state, and all associated observations for that satellite; 
    column title include:
    --> "stateID" :  string of encoded sat number and epochs used to find the state
    --> "itCount" :  the number of Gauss refinement iterations
    --> "state" :  6x1 np array containing the determined state vector [km, km/s]
    --> "ra" :  of associated right ascensions (deg) for that state
    --> "declination" : list of associated declinations (deg) for that state
    --> "obTime" :  list of str epochs for each associated observation
    '''

    # Sort data into chronological order
    obs_sorted = obs.sort_values(by="obTime").reset_index(drop=True)

    # Pull relevant columns (epoch, RA, Dec)
    obs_pruned = obs_sorted[["satNo", "obTime", "ra", "declination", "senlon", "senlat", "senalt"]].copy()

    # Convert times to JD and then to UT
    t = Time(obs_pruned["obTime"].tolist())
    ut = np.array(t.jd) * 86400
    obs_pruned["ut"] = ut

    # Generate the triplet indices for the given set
    triplets = generateTriplets(obs_pruned)

    # Initialize final dataframe
    states = []

    # Loop through the list of triplets
    for trip in triplets:

        # Pull current data for current triplet
        obs_curr = obs_pruned.iloc[trip].reset_index(drop=True)

        # Pull relevant data
        satNo = obs_curr["satNo"].tolist()
        epoch = obs_curr["obTime"].tolist()
        ut = obs_curr["ut"].to_numpy().reshape((3, 1))
        ra = obs_curr["ra"].to_numpy().reshape((3, 1))
        dec = obs_curr["declination"].to_numpy().reshape((3, 1))
        lon = obs_curr["senlon"].to_numpy().reshape((3, 1))
        lat = obs_curr["senlat"].to_numpy().reshape((3, 1))
        alt = obs_curr["senalt"].to_numpy().reshape((3, 1))

        # Determine change in absolute times
        T1 = ut[0, 0] - ut[1, 0]
        T3 = ut[2, 0] - ut[1, 0]

        # Determine helpful parameters for Gauss' method
        a1 = T3 / (T3 - T1)
        a3 = -T1 / (T3 - T1)
        a1u = T3 * ((T3 - T1)**2 - T3**2) / (6*(T3 - T1))
        a3u = -T1 * ((T3 - T1)**2 - T1**2) / (6*(T3 - T1))

        # Establish helpful Earth paramters
        f = 0.003353 # Earth's flattening factor
        R = 6378.137 # Earth's radius
        mu = 398600.4418 # earth's gravitational parameter

        # Determine the line of site matrix and site vectors
        L = np.empty((3, 3))
        r_site = np.empty((3, 3))
        itCount = 0
        for i in range(3):
            
            # Determine column
            Li = radec2unit(ra[i, 0], dec[i, 0])
            
            # Append column to line of site matrix 
            L[:, i] = Li.ravel()

            # Compute the ellipsoidal earth coefficients
            latc = np.cos(np.deg2rad(lat[i, 0]))
            lats = np.sin(np.deg2rad(lat[i, 0]))
            coeff1 = (R / np.sqrt(1 - (2*f - f**2)*lats**2) + alt[i, 0])*latc
            coeff2 = (R*(1 - f)**2)/(np.sqrt(1 - (2*f - f**2)*lats**2)) + alt[i, 0]

            # Determinet the local sidereal time
            t_temp = Time(obs_curr.loc[i, "obTime"])
            lst = t_temp.sidereal_time("mean", lon[i, 0]).deg

            # Determine the site vector
            lstc = np.cos(np.deg2rad(lst))
            lsts = np.sin(np.deg2rad(lst))
            r_sitei = np.array([[coeff1 * lstc], 
                                [coeff1 * lsts],
                                [coeff2 * lats]])
            
            # Append column to site vector matrix
            r_site[:, i] = r_sitei.ravel()

        # Determine the inverse of the LOS matrix
        invL = np.linalg.inv(L)

        # Determine intermediate mtrix m
        M = invL @ r_site

        # Define polynomial parameters
        d1 = M[1, 0] * a1 - M[1, 1] + M[1, 2] * a3
        d2 = M[1, 0] * a1u + M[1, 2] * a3u
        C = np.dot(L[:, 1].ravel(), r_site[:, 1].ravel())

        # Define polynomial
        p = [1, 0, -(d1**2 + 2*C*d1 + np.linalg.norm(r_site[:, 1])**2), 0, 0,
             -2*mu*(C*d2 + d1*d2), 0, 0, -mu**2*d2**2]
        
        # Determine the roots, and save the minimum real positive one
        rts = np.roots(p)
        rts_realpos = [r.real for r in rts if np.isreal(r) and r.real > 0]
        
        # Skip iteration if no positive real roots
        if not rts_realpos:
            continue

        # Initialize residual variables and saved state vars
        res_best = np.inf
        r_best = np.empty((3, 1))
        v_best = np.empty((3, 1))
        
        # Loop through each positive root
        for rt in rts_realpos:

            # Calc helpful gauss parameters
            u = mu / (rt**3)
            c = np.array([[a1 + a1u*u], [-1], [a3 + a3u*u]])

            # Determine the initial slant ranges
            rhoc = M @ -c
            rho0 = rhoc / c

            # Iterate to determine the most optimal slant range (stop after 100)
            k = 0
            r = np.empty((3, 1))
            v = np.empty((3, 1))
            r1 = np.empty((3, 1))
            r3 = np.empty((3, 1))
            while k < 100:

                # Update loop count
                k += 1

                # Pull the position vectors
                r1 = (rho0[0, 0] * L[:, 0] + r_site[:, 0]).reshape((3, 1))
                r2 = (rho0[1, 0] * L[:, 1] + r_site[:, 1]).reshape((3, 1))
                r3 = (rho0[2, 0] * L[:, 2] + r_site[:, 2]).reshape((3, 1))

                # Call gibbs to determine the state at the middle epoch
                r, v = gibbs(r1, r2, r3, ut)

                # Determine the semimajor axis and eccentricity of the orbit
                rhat = r / np.linalg.norm(r)
                h = np.cross(r.flatten(), v.flatten()).reshape((3, 1))
                e = np.linalg.norm((1 / mu) * np.cross(v.flatten(), h.flatten()).reshape((3, 1)) - rhat)
                energy = (1/2) * np.dot(v.ravel(), v.ravel()) - mu / np.linalg.norm(r)
                a = -mu / (2*energy)

                # Define the parameter p
                p = a * (1 - e**2)

                # Define the Lagrange coefficients for the angular difference between the position vectors
                r1n = np.linalg.norm(r1)
                r2n = np.linalg.norm(r2)
                r3n = np.linalg.norm(r3)
                ang1 = np.arccos(np.dot(r1.ravel(), r2.ravel()) / (r1n * r2n))
                ang3 = np.arccos(np.dot(r3.ravel(), r2.ravel()) / (r3n * r2n))
                f1 = 1 - (r1n / p) * (1 - np.cos(ang1))
                f3 = 1 - (r3n / p) * (1 - np.cos(ang3))
                g1 = r1n * r2n * np.sin(-ang1) / np.sqrt(mu * p)
                g3 = r3n * r2n * np.sin(ang3) / np.sqrt(mu * p)

                # Define new c values based on coeff
                c[0, 0] = g3 / (f1 * g3 - f3 * g1)
                c[1, 0] = -1
                c[2, 0] = -g1 / (f1 * g3 - f3 * g1)

                # Calc new slant ranges
                rhoc = M @ -c
                rho_test = rhoc / c

                # Set the iteration
                itCount = k

                # Check if new slant ranges are equal to old slant ranges
                if np.allclose(rho0, rho_test, rtol=0, atol=1e-5):
                    break
                
                # Assign new slant ranges for another iteration if needed
                rho0 = rho_test

            # Determine the LOS vectors based on the converged solution
            L_conv = (np.hstack((r1, r, r3)) - r_site)
            L_conv = L_conv / np.linalg.norm(L_conv, axis = 0, keepdims = True)
            
            # Determine the LOS residuals
            res = np.sum(np.linalg.norm(L_conv - L, axis = 0))

            # Save the state if current residuals are less than the previous residuals
            if res < res_best:
                res_best = res
                r_best = r
                v_best = v

        # Determine the associated state ID
        ID = str(satNo[0]) + str(epoch[0]) + str(epoch[2])
        ID_encode = base64.b64encode(ID.encode('utf-8'))
        ID_string = ID_encode.decode('utf-8')

        # Generate the final state
        X = np.vstack((r_best, v_best))

        # Append the state and ID for current iteration
        states.append({'stateID' : ID_string,
                       'itCount' : itCount,
                       'state' : X.flatten().tolist(),
                        'ra' : ra.flatten().tolist(),
                        'dec' : dec.flatten().tolist(),
                        'obTime' : epoch})
        
    # Return the states dataframe
    return pd.DataFrame(states)




def semimajorAxis(X):
    '''
    The following function determines the semimajor axis given an ECI state vector in
    list format [x, y, z, vx, vy, vz].

    INPUTS
    X :  List containing the spacecraft state [r, v] (km, km/s)

    OUPUTS
    a :  semimajor axis (km) of the orbit
    '''

    # Determine helpful earth parameters
    mu = 398600.4418

    # Pull the magnitude of the state parts
    r = np.linalg.norm(X[:3])
    v = np.linalg.norm(X[3:])

    # Determine the energy of the orbit
    energy = v**2 / 2 - mu /r

    # Find the semimajor axis of the orbit
    if energy == 0:
        # Return inf if parabolic
        return np.inf
    # Return the semimajor axis if hyperbolic or elliptical
    return -mu / (2 * energy)




def cullStates(states):
    '''
    The following function takes in the states dataframe outputted by the Gauss 
    function and culls the states outside of the trend using the standard deviation
    in the semimajor axis.

    INPUTS
    states :  dataframe containing the unpruned states determined from Gauss' method,
    relevant column titles for the state dataframe include:
    --> "stateID" :  string of encoded sat number and epochs used to find the state
    --> "itCount" :  the number of Gauss refinement iterations
    --> "state" :  6x1 np array containing the determined state vector [km, km/s]
    --> "ra" :  of associated right ascensions (deg) for that state
    --> "declination" : list of associated declinations (deg) for that state
    --> "obTime" :  list of str epochs for each associated observation

    OUTPUTS
    states_culled :  dataframe containing the pruned states based on semimajor axis 
    values within 0.25*std from the mean; relevant column titles for the states_culled
    dataframe include:
    --> "stateID" :  string of encoded sat number and epochs used to find the state
    --> "itCount" :  the number of Gauss refinement iterations
    --> "state" :  6x1 np array containing the determined state vector [km, km/s]
    --> "ra" :  of associated right ascensions (deg) for that state
    --> "declination" : list of associated declinations (deg) for that state
    --> "obTime" :  list of str epochs for each associated observation
    '''

    # Detemine the semimajor axis
    states["a"] = states["state"].apply(semimajorAxis)

    # Find the mean and standard deviation
    a_mean = states["a"].mean()
    a_std = states["a"].std()

    # Cull states outside one standard deviation from the mean
    states_culled = states[(states["a"] >= a_mean - 0.25*a_std) & (states["a"] <= a_mean + 0.25*a_std)].copy().reset_index(drop=True)

    # Drop the a column
    states_culled = states_culled.drop("a", axis = 1)

    # Return the culled states
    return states_culled




def processData(args):
    '''
    The following function takes in a specific tuple designated by gaussSorter. This
    allows for the utilization of parallel processing via this helper function.

    INPUTS
    args :  tuple of the form (satNo, period, observation dataframe)
    --> satNo :  int of the NORAD ID
    --> period :  float of the satellites orbit period
    --> observation dataframe :  dataframe containg the angular observations and epochs 

    OUTPUTS
    result :  tuple of the form (satNo, observation dataframe, culled state dataframe),
    relevant column titles for the state dataframe include:
    --> "stateID" :  string of encoded sat number and epochs used to find the state
    --> "itCount" :  the number of Gauss refinement iterations
    --> "state" :  6x1 np array containing the determined state vector [km, km/s]
    --> "ra" :  of associated right ascensions (deg) for that state
    --> "declination" : list of associated declinations (deg) for that state
    --> "obTime" :  list of str epochs for each associated observation
    '''
    
    # Pull the relevant data
    satNo, period, obs = args

    # Call Gauss' method for the current observation dataframe
    states = gauss(obs)

    # If no states found, return empty
    if states.empty:
        return (satNo, obs, pd.DataFrame())

    # Cull the states based on semi major axis
    states_culled = cullStates(states)

    # Return the tuple
    return (satNo, obs, states_culled)




def gaussSorter(data, n_processors = multiprocessing.cpu_count()):
    '''
    The following function takes in a list of tuples with each tuple corresponding to 
    a satellite and its corresponding observations which are held in a dataframe. The 
    function parses through this list, and calls Gauss to determine a set of states 
    from that observation data.
    
    INPUTS
    data :  list of tuples of form (satNo, period, observation dataframe)
    --> satNo :  int of the NORAD ID
    --> period :  float of the satellites orbit period
    --> observation dataframe :  dataframe containing the angular observations and epochs 
    for that satellite, relevant column titles include:
        --> "satNo" :  int of the NORAD ID
        --> "obTime" :  string of the observation epoch
        --> "ra" :  right ascension (deg)
        --> "declination" :  declination (deg)
        --> "senlon" :  sensor longitude (deg)
        --> "senlat" :  sensor latitude (deg)
        --> "senalt" :  sensor altitude (km)

    OUTPUTS
    IODresults :  list of tuples of the form (satNo, observation dataframe, state dataframe),
    relevant column titles for the state dataframe include:
    --> "stateID" :  string of encoded sat number and epochs used to find the state
    --> "itCount" :  the number of Gauss refinement iterations
    --> "state" :  6x1 np array containing the determined state vector [km, km/s]
    --> "ra" :  of associated right ascensions (deg) for that state
    --> "declination" : list of associated declinations (deg) for that state
    --> "obTime" :  list of str epochs for each associated observation
    '''

    # Limit cores based on length of data
    n_processors = min(n_processors, len(data))

    # Enable multiprocessing to determine the states for each bin concurrently
    with ProcessPoolExecutor(max_workers = n_processors) as executor:

        # Return the list of tuples containing the determined states
        return list(executor.map(processData, data))
