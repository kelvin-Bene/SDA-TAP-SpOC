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
import uctbenchmark.src.libraries.apiIntegration as apiI
from uctbenchmark.src.libraries.unitConversion import unitConversion
import uctbenchmark.src.libraries.dataManipulation as dataM
import uctbenchmark.src.libraries.windowTools as windowTools
from uctbenchmark.src.libraries.timerClass import Timer
import uctbenchmark.src.libraries.windowCheck as windowCheck

from uctbenchmark.src.libraries.dataManipulation import binTracks

from uctbenchmark.src.libraries.TLEGeneration import TLEGeneration

# === Define Functions ===

# === Main Execution Block ===

def create_dataset(udl_token, sat_data_f, obs, ref_svs, ref_tles, output_dataset, raw_dir):
    
    t = Timer()
    t.mark('Start')

    satelliteData = pd.read_csv(sat_data_f)

    # Create Dataset codes based on user input, opens a dialog box for user input
    datasetCodeDataframe = windowTools.createDatasetCodeGUI()
    datasetCodes = windowTools.codeGenerator(datasetCodeDataframe)
    t.mark('Dataset Codes Created')

    # Window selection based on user input
    # DO NOT SAVE UDL PASSWORD OR TOKEN TO THE GITHUB/GITLAB PLEASE
    # Save UDL Base64 token to environment variable UDL_TOKEN

    #UDL_token = apiI.UDLTokenGen(Username,Password)
    bins = windowCheck.windowMain(datasetCodes,udl_token, raw_dir)

    for bin in bins:
        datasetCode, tierThreshold, observations, orbElms, metaData = bin
        # Pull list of satellites from each bin
        satIDs = observations['satNo'].unique() # untested

        # Remove satellites with obs < min threshold
        if tierThreshold == 'T4':
            # Need to simulate objects to reach desired object type dnesity
            print('T4 NOT implemented. Moving On')
            pass # logic not yet implemented in basicScoringFunction
        if tierThreshold == 'T3':
            # Need to simulate observations to reach desired data quality
            print('T3 NOT implemented. Moving On')
            pass
        #if tierThreshold == 'T2':
        # Everything will be passed to downsample, if no downsample required, function will pass
        # Need to downsample to reach desired data quality
        print('T2 NOT implemented. Moving On')
        pass


        # Get reference state vectors and TLEs
        endTime = pd.to_datetime(observations['obTime'].max()) # get the latest observation time
        referenceSVs, referenceTLEs, satList, _ = apiI.pullStates(udl_token,satIDs,int(datasetCode.TimeWindow),'days',end_time=endTime)
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
        observations.to_csv(obs, index=False)
        referenceSVs.to_csv(ref_svs, index=False)
        referenceTLEs.to_csv(ref_tles, index=False)

        # For each 'bin' (datasetCode), save a dataset to database
        # Save Created Dataset to a JSON file and save in database
        output_json = apiI.saveDataset(observations, TLEdataset, referenceSVs , referenceTLEs, output_dataset)


if __name__ == "__main__":
    create_Dataset()
    




        
        
        
        

    








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