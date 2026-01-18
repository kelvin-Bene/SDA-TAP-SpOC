#                                             #
# UCTP Benchmarker Skeleton: Dataset Creation #
#                                             #

# to be run before sending data to the UCTP. 
# Does not need to be run every time UCTP is evaluated

# === Import Required Libraries ===
import numpy as np
import os
import json
import pandas as pd

# === Import Local Dependencies ===
import libraries.apiIntegration as apiI
from libraries.unitConversion import unitConversion
import libraries.dataManipulation as dataM
import libraries.windowTools as windowTools
from libraries.timerClass import Timer
import libraries.windowCheck as windowCheck

from libraries.dataManipulation import binTracks

from libraries.TLEGeneration import TLEGeneration

# === Define Functions ===

# === Main Execution Block ===

# Fix potential current working dir issues
os.chdir(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":

    t = Timer()
    
    t.mark('Start')

    satelliteData = pd.read_csv('./data/satelliteData_Full.csv')

    # Create Dataset codes based on user input, opens a dialog box for user input
    datasetCodeDataframe = windowTools.createDatasetCodeGUI()
    datasetCodes = windowTools.codeGenerator(datasetCodeDataframe)
    t.mark('Dataset Codes Created')

    # Window selection based on user input
    # DO NOT SAVE UDL PASSWORD OR TOKEN TO THE GITHUB/GITLAB PLEASE
    # Save UDL Base64 token to environment variable UDL_TOKEN

    #UDL_token = apiI.UDLTokenGen(Username,Password)
    UDL_token = os.getenv('UDL_TOKEN')
    #UDL_token = "QmlueWFtaW4uc3Rpdmk6UGxlYXNlRzF2ZU1lTW9yZURhdGE="
    bins = windowCheck.windowMain(datasetCodes,UDL_token)

    for bin in bins:
        datasetCode, tierThreshold, observations, orbElms, metaData = bin
        # Pull list of satellites from each bin
        satIDs = observations['satNo'].unique() # untested

        # Remove satellites with obs < min threshold
        if tierThreshold == 'T4':
            # Need to simulate objects to reach desired object type density
            print('T4 NOT implemented. Moving On')
            pass  # logic not yet implemented in basicScoringFunction

        if tierThreshold == 'T3':
            # Need to simulate observations to reach desired data quality
            print(f'Applying {tierThreshold} simulation...')

            # Import simulation modules and config
            import sys
            sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            import uct_benchmark.config as config
            from uct_benchmark.simulation.simulateObservations import simulateObs, epochsToSim

            # Load sensor data for simulation
            sensors_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sensorCounts.csv')
            if os.path.exists(sensors_path):
                sensorsDf = pd.read_csv(sensors_path)
            else:
                print(f'Warning: Sensor data not found at {sensors_path}')
                print('T3 simulation requires sensor data. Skipping simulation.')
                sensorsDf = None

            if sensorsDf is not None:
                obs_before = len(observations)
                simulated_total = 0
                satellites_simulated = 0

                for sat_id in observations['satNo'].unique():
                    sat_obs = observations[observations['satNo'] == sat_id]

                    # Check if we have orbital elements for this satellite
                    if sat_id not in orbElms:
                        print(f'  Skipping satellite {sat_id}: no orbital elements')
                        continue

                    sat_orb_elems = orbElms[sat_id]

                    # Determine epochs needing simulation
                    try:
                        epochs_to_sim, bins_info = epochsToSim(
                            sat_id, sat_obs, sat_orb_elems
                        )
                    except Exception as e:
                        print(f'  Error determining epochs for {sat_id}: {e}')
                        continue

                    if not epochs_to_sim:
                        status = bins_info.get('status', 'unknown')
                        if status != 'all_bins_covered':
                            print(f'  Satellite {sat_id}: {status}')
                        continue

                    print(f'  Simulating {len(epochs_to_sim)} epochs for satellite {sat_id}')

                    # Create state vector from orbital elements for propagation
                    # Use TLE if available, otherwise construct from orbital elements
                    try:
                        # Get a reference epoch from existing observations
                        ref_epoch = pd.to_datetime(sat_obs['obTime'].iloc[0])
                        if hasattr(ref_epoch, 'to_pydatetime'):
                            ref_epoch = ref_epoch.to_pydatetime()

                        # Build approximate state vector from orbital elements
                        # This is a simplified approach - uses orbital elements to estimate state
                        a = sat_orb_elems.get('Semi-Major Axis', 7000)  # km
                        e = sat_orb_elems.get('Eccentricity', 0.001)
                        i = np.radians(sat_orb_elems.get('Inclination', 45))
                        raan = np.radians(sat_orb_elems.get('RAAN', 0))
                        argp = np.radians(sat_orb_elems.get('Argument of Perigee', 0))
                        M = np.radians(sat_orb_elems.get('Mean Anomaly', 0))

                        # Convert orbital elements to approximate state vector (simplified)
                        # Using vis-viva equation for velocity magnitude
                        mu = 398600.4418  # km^3/s^2
                        r = a * (1 - e**2) / (1 + e * np.cos(M))  # Approximate radius
                        v = np.sqrt(mu * (2/r - 1/a))  # Velocity magnitude

                        # Simplified position and velocity (in orbital plane)
                        x = r * np.cos(M)
                        y = r * np.sin(M)
                        vx = -v * np.sin(M)
                        vy = v * np.cos(M)

                        # Rotate to ECI (simplified - doesn't account for all rotations)
                        state_vector = np.array([x, y, 0, vx, vy, 0]) * 1000  # Convert km to m

                        # Simulate observations at determined epochs
                        sim_obs = simulateObs(
                            state_vector,
                            ref_epoch,
                            epochs_to_sim,
                            sensorsDf,
                            positionNoise=config.positionNoise,
                            angularNoise=config.angularNoise,
                            satelliteParameters=[sat_id, 0, 0]
                        )

                        if len(sim_obs) > 0:
                            # Mark observations as simulated
                            sim_obs['dataMode'] = 'SIMULATED'

                            # Merge with existing observations
                            observations = pd.concat([observations, sim_obs], ignore_index=True)
                            simulated_total += len(sim_obs)
                            satellites_simulated += 1

                    except Exception as e:
                        print(f'  Simulation failed for satellite {sat_id}: {e}')
                        continue

                obs_after = len(observations)
                print(f'T3 simulation complete: {obs_before} -> {obs_after} observations')
                print(f'Added {simulated_total} simulated observations for {satellites_simulated} satellites')

        # T1/T2 Processing: Apply downsampling
        if tierThreshold in ['T1', 'T2']:
            print(f'Applying {tierThreshold} downsampling...')

            # Import config for downsampling parameters
            import sys
            sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            import uct_benchmark.config as config

            # Build downsampling parameters from config
            orbit_coverage_params = {
                'sats': None,  # Apply to all satellites
                'p_bounds': config.downsample_coverage_bounds,
                'p_coverage': config.downsample_coverage_target
            }
            track_length_params = {
                'sats': None,
                'p_bounds': config.downsample_gap_bounds,
                'p_track': config.downsample_gap_target
            }
            obs_count_params = {
                'sats': None,
                'p_bounds': config.downsample_obs_bounds,
                'obs_max': config.downsample_obs_max
            }

            # Get observation count before downsampling
            obs_before = len(observations)

            # Apply downsampling
            try:
                observations, p_reached = dataM.downsampleData(
                    observations,
                    orbElms,
                    orbit_coverage_params,
                    track_length_params,
                    obs_count_params,
                    bins=10,
                    rand=42  # Fixed seed for reproducibility
                )

                obs_after = len(observations)
                print(f'Downsampling complete: {obs_before} -> {obs_after} observations')
                print(f'Reduction: {100 * (1 - obs_after/obs_before):.1f}%')
                print(f'Percentages reached: {p_reached}')
            except Exception as e:
                print(f'Downsampling failed: {e}')
                print('Continuing with original observations...')
        else:
            print(f'{tierThreshold} does not require downsampling')


        # Get reference state vectors and TLEs
        endTime = pd.to_datetime(observations['obTime'].max()) # get the latest observation time
        referenceSVs, referenceTLEs, satList, _ = apiI.pullStates(UDL_token,satIDs,int(datasetCode.TimeWindow),'days',end_time=endTime)
        # pullStates will only return SVs and TLEs for satellites that have info on UDL. satList is list of satIDs that we returned data for in order that they appear
        # Condider removing satellites for which we have no state data

        # Merge mass and crossSection data into referenceSVs
        massCrossSection = satelliteData[['satNo', 'mass', 'xSectAvg']].copy()
        massCrossSection.rename(columns={'xSectAvg': 'crossSection'}, inplace=True)
        referenceSVs = pd.merge(referenceSVs, massCrossSection, on='satNo', how='left')
        referenceSVs = referenceSVs.fillna({
            'mass': 0,
            'crossSection': 0
            })

        # raw obs to TLEs
        # NOTE: This line has not been tested in the driver
        #TLEdataset = TLEGeneration(observations, referenceSVs)
        TLEdataset = observations[['id','satNo','ra','declination']].copy() # Dummy dataset to allow saveData to work but bypass TLEgeneration

        # Save dataframes to .csv for easy debugging
        observations.to_csv("./data/observations_.csv", index=False)
        referenceSVs.to_csv("./data/referenceSVs_.csv", index=False)
        referenceTLEs.to_csv("./data/referenceTLEs_.csv", index=False)

        # For each 'bin' (datasetCode), save a dataset to database
        # Save Created Dataset to a JSON file and save in database
        output_json = apiI.saveDataset(observations, TLEdataset, referenceSVs , referenceTLEs, './data/output_dataset.json')



        
        
        
        

    








'''


    
    # Somehow select what kind of dataset user wants
    # TODO: For now, we're just using default data/calibration satellites
    satIDs = np.array([1328, 5398, 7646, 8820, 16908, 19751, 20026, 22195, 22314, 22824, 23613, 24876, 25544, 26360, 27566, 27944, 32711, 36508, 39070, 39086, 39504, 40730, 41240, 41335, 42915, 43476, 43477, 43873, 46826, 48859])
    
    timeframe = 2
    timeunit = 'hours'
    end_timestamp = 'now'
    

    api_options = {
        # Source
        "udl": True, 
        "esa": False, 
        "spacetrack": False,
        # incomplete <!>
        # Select Observation Data Type (EO, RF, RADAR) 
        "eo": True,
        "rf": False,
        "radar": False,
        # Select Orbital Plane (LEO, GEO, MEO, HEO)
        "leo": True,
        "meo": True,
        "geo": True,
        "heo": True,
        # Select Data Quality (Unknown Sensor Type, Unknown Calibration, Unknown Calibration, Small % of Orbit Tracked, Limited Obs, Long Period b/w tracks, Normal)
            #NOTE: for limited data, query for anything with more than minimum data amount
        "unknown_sensor_type": False,
        "unknown_calibration": False,
        "small_percent": False, #TODO: make the orbital parameter based on polygon area in great circle
        # Select Time Period (1 Day, 3 Days, 1 Week, 3 Weeks, Custom)
        #TODO: make preset time ranges for easy standard testing
        #NOTE: ALL TIMES AS JULIAN DATE 
        "time_start": 2460844.41142 - 1,
        "time_end": 2460844.41142 - 0,
        # Select Events (Maneuver b/w Obs, Breakup, Long Duration Low Thrust, None)
        "maneuver_bw_obs": False,
        "ldlt_maneuver": False,
        "breakup": False,
        # Select Satellite-Specific Data (HAMR, Close Proximity, Average Sat., Calibration Sat.)
        "hamr": True,
        "close_prox": True,
        "avg_sat": True,
        "calibration_sat": True
    }

    
    # Authenticate
    # This is Gabriel's login, future pull from operator
    UDL_token = "QmlueWFtaW4uc3Rpdmk6Q2k1MXVuYXI1YXRlMTFpdGU="
    ESA_token = "ImUyZWM1M2ViLTRlM2UtNGYwYy05YjBkLTVkZGU2YTAxNzdjYyI.-lBJphYv0O3j0LTEJgU7pcycifQ" 
    


    # Perform API call and obtain obs data, reference orbits, and decorrelated dataset
    # This function already handles intersection conflicts
    dataset, obsTruthData, svTruthData, elsetTruthData, satIDs, performance_info = apiI.generateDataset(UDL_token, ESA_token, satIDs, timeframe, timeunit, endTime=end_timestamp)
    t.mark('Data Collection')
    svTruthData = unitConversion(svTruthData)
    t.mark('Unit Conversion')
    
    # Perform TLE generation
    #TLETruthData = TLEGeneration(obsTruthData, svTruthData)
    t.mark('TLE Generation')
    
    # Verify there's enough data for a full set
     # TODO
    
    # Downsample: if data had a greater number of real obs than data quality selection, remove some at random
    # TODO
    #obsTruthData, dataset, p_reached = dataM.downsampleData(obsTruthData, dataset, svTruthData, {'sats': None, 'p_bounds': (0.5,0.7), 'p_coverage': 0.25}, {'sats': None, 'p_bounds': (0.5,0.7), 'p_track': 2}, {'sats': None, 'p_bounds': (0.5,0.7), 'obs_max': 50}, bins=10, rand=None)
    #obsTruthData, dataset, p_reached = dataM.downsampleData(obsTruthData, dataset, svTruthData, {'sats': None, 'p_bounds': (0.0,0.7), 'p_coverage': 0.25}, {'sats': None, 'p_bounds': (0.0,0.7), 'p_track': 2}, {'sats': None, 'p_bounds': (0.0,0.7), 'obs_max': 50}, bins=10, rand=None)
    t.mark('Downsampling')
    
    # Save all data as csv (input into blackbox)
    # Output is in UDL format for now

    #Insert format once we make changes
    
    #tr, m = dataM.binTracks(obsTruthData, svTruthData)
    t.mark('Track Binning')
    
    #output_json = apiI.saveDataset(obsTruthData, dataset, svTruthData, elsetTruthData, './data/output_dataset.json')
    t.mark('Save JSON')
    
    
    output_json = apiI.saveDataset(obsTruthData, dataset, obsTruthData[['id','satNo','ra','declination']],obsTruthData[['id','ra','declination']], svTruthData, elsetTruthData, './data/output_dataset.json')

    with open('./data/Patrick_obs_output_dataset.json', 'w') as f:
        json.dump(output_json['dataset_obs'], f)

    
    #o, d, s, e = apiI.loadDataset('./data/output_dataset.json')
    t.mark('Load JSON')
    
    t.report()
    
    #svTruthData['cov_matrix'] = svTruthData['cov_matrix'].apply(lambda arr: json.dumps(arr.tolist()))
    #obsTruthData.to_csv("./data/ref_obs.csv", index=False)
    #svTruthData.to_csv("./data/ref_orbits.csv", index=False)
    #dataset.to_csv("./data/dataset.csv", index=False)
    
    # Send to UCTP...'''