# -*- coding: utf-8 -*-
'''
windowCheck.py is the master window evaluation file that pulls UDL data in batches,
logically bisects and scores sub-batches of data to meet a certain threshold, and
slides along a sub-batch once they are sufficiently small to pull a window sized bin
of data with a sufficient score. General code flow:
--> Loop thorugh list of data set codes
--> Pull initial batch of data specified by the windowsize and windowsize multiplier
--> Sequentially bisect and score the batch until the desired threshold is met
--> If desired threshold is not met, pull new batch of data
--> Continue until list of thresholds are expended
--> Save best bin and score
--> Return list of tuples containing the best bin for each data set code with
        corresponding metadata

Created: 21 July 2025
        
@author: Miles Puchner

Updated: 31 July 2025
'''


import math
import numpy as np
import pandas as pd
import libraries.apiIntegration as UDL
import itertools as it
import datetime as dt
from libraries.basicScoringFunction import basicScoring
import libraries.config as con



def batchPull(code, start_epoch, end_epoch, UDL_token):
    '''
    The following function pulls batches of data from the UDL to be used in the
    sub driver (windowCheck()).

    INPUTS
    code :  DataSet Code object containing the dataset code for that iteration
    start_epoch :  datetime object containing the starting epoch for the batch pull
    end_epoch :  datetime object containing the ending epoch for the batch pull
    UDL_token :  the users UDL token for data pulling

    OUTPUTS
    data_compiled :  dataframe containing the batch of data from the UDL
    '''

    # Convert from udl timedate to python timedate
    start_time=UDL.UDLToDatetime(start_epoch)
    end_time=UDL.UDLToDatetime(end_epoch)

    #establish batch size
    batchsize=end_time-start_time

    #print sensortypes being queried
    sensor_types = [key for key, value_list in code.sensor_superiors.items() if code.SensorType in value_list or code.SensorType == key]
    print(sensor_types)

    #read regimes being queried    
    if code.Regime in ['LEO','GEO','MEO']:
        regimes = code.Regime
    else:
        component_regimes = it.islice(code.regime_superiors.items,4)
        regimes = [key for key, value_list in component_regimes if code.Regime in value_list]
    print(regimes)

    #read time winow
    time_window = int(code.TimeWindow)
    print(time_window)
    
    #construct parameters for query url from info in dataset code object class
    set_data = pd.DataFrame()
    param_dict={}
    data_list =list()
    if isinstance(sensor_types,str):
        sensor_types=[sensor_types]
    for sensor_type in sensor_types:
        service = code.sensor_type_queries[sensor_type]
        if isinstance(regimes,str):
            regimes=[regimes]
        
        for regime in regimes:
            param_dict={'range':code.regime_ranges[regime],
                        'uct':'false',
                        'dataMode':'REAL'}

            steps=dt.timedelta(minutes=0)
            while steps<batchsize:
                #run query command
                final_dict = param_dict.copy()
                final_dict['obTime']=UDL.datetimeToUDL(start_time+steps)+'..'+UDL.datetimeToUDL(start_time+dt.timedelta(minutes=10)+steps)
                steps +=dt.timedelta(minutes=10)
                data = UDL.UDLQuery(UDL_token,service,final_dict)
                if not data.empty:
                    data_list.append(data)
    #compile call results
    data_compiled = pd.concat(data_list,ignore_index=True)

    return(data_compiled)





def normalizeTime(data):
    '''
    The following helper function normalizes the epochs in a batch such that:
    --> 0 corresponds to most recent time
    --> final time corresponds to most distant time in the past
    This allows for easier sorting logic during bisecting and sliding.

    INPUTS
    data :  dataframe of obs data for the given batch

    OUTPUTS
    normalized_time :  amended dataframe of obs to include a normalized time column
    '''

    # Determine newest epoch
    tf = data["epoch"].max()

    # Apply new column containing normalized epochs 
    normalized_time = data["epoch"].apply(lambda t: (tf - t).total_seconds() / 86400.0)
    return normalized_time





def expFunc(window_size, batch_size, iteration, decay_rate):
    '''
    The following helper function defines an exponential decay function that slowly
    decreases the size of successive batches should a previous target threshold not
    be met. The function will never be smaller than the windowsize specified by the
    user.

    INPUTS
    window_size :  user specified window size from the dataset code (days)
    batch_size :  initial batch size specified by the user in the config file (days)
    iteration :  current iteration of batches
    decay_rate :  the decay rate of the exponential function specified by the user
            in the config file

    OUTPUTS
    new batch size (days)
    '''

    # Ensure batch size is greater than window size
    if batch_size <= window_size:

        # If smaller then return window size
        return window_size
    
    # If greater then decrease batch size
    return window_size + (batch_size - window_size) * math.exp(-decay_rate * iteration)





def thresholdConvert(thresholds_strs):
    '''
    The following helper function converts the user specifed list of thresholds into
    numerical values for ease of boolean comparison. The relationship between the 
    strings and their numnerical values are as follows:
    --> 'T1' :  4  (may require downsampling)
    --> 'T2' :  3  (requires downsampling)
    --> 'T3' :  2  (requires observation sim)
    --> 'T4' :  1  (requires object sim)
    --> 'T5' :  0  (impossible)

    INPUTS
    thresholds_strs :  list of strings contianing the thresholds for each iteration; the
            length of the list will be the amount of iterations ran for a given dataset
    
    OUTPUTS
    threhsolds_ints :  list of integer threshold scores corresponding to the threshold
            strings
    '''

    # Create a dictionary of assigned threshold integers
    tier_to_value = {
        "T1": 4,
        "T2": 3,
        "T3": 2,
        "T4": 1,
        "T5": 0
    }

    # Convert to a list format
    return [tier_to_value[t] for t in thresholds_strs]





def thresholdCheck(batch_temp, thresh_des, code):
    '''
    The following helper function scores a batch/sub-batch of data and compares it to
    a desired threshold value.

    INPUTS
    batch_temp :  batch/sub-batch dataframe
    thresh_des :  desired threshold calue for comparison
    code :  DataSet Code object containing the dataset code for that iteration

    OUTPUTS
    boolean :  whether or not the score is greater than the desired threshold value
    '''
    print('Threshold Check bin:')
    print(batch_temp['epochNormalized'])
    # Call the scoring function to find the threshold for the data
    thresh_curr, _, _ = basicScoring(code, batch_temp, satData = pd.read_csv("data/satelliteData_Full.csv"))

    # Return boolean based on threshold
    if thresh_curr >= thresh_des:
        return True
    else:
        return False





def slide(sub_batch, window_size, code):
    '''
    The following funtion determines the window of data (equal to the user specified 
    fitspan) using a sliding window method. The function takes in the minimal size
    sub-batch from bisect() and saves the highest scoreing window. The window will 
    either slide observation by observation (slide_resolution = 0), or by a
    user specified slide resolution in days that is lsited in teh config.py file.

    INPUTS
    sub_batch :  dataframe containing the minimal size sub-batch found during bisection
    window_size :  the size of the user desired window in days
    code :  DataSet Code object containing the dataset code for that iteration

    OUPUTS
    bin_best :  dataframe containing the data associated with the highest scoring bin 
            within the minimal size sub-batch
    score_best :  the score assocaited with the the best bin
    orbElems_best :  the orbital elements associated with the best bin
    metadata_best :  the metadata associated with the best bin
    '''

    #-------------------------------#
    print("Slide Entered!")
    #-------------------------------#

    # Define the slide resolution from the config file
    slide_res = con.slide_resolution
    
    # Ensure slide resolution is at most half the window size for no loss of data
    if slide_res > window_size/2:
        slide_res = window_size/2

    # Initialize best bin variables for loop
    score_best = -1
    bin_best = None
    orbElems_best = None
    metadata_best = None

    # Get time range of the current bin
    t_min = sub_batch["epochNormalized"].min()
    t_max = sub_batch["epochNormalized"].max()
    tc = t_min

    # Initialize index as the min time index (final item in sub-batch)
    i = len(sub_batch) - 1

    # Loop through window size bins within the sub-batch
    while i >= 0 and tc + window_size <= t_max:

        # Set the initial time for bin selection as the current time
        t0 = tc

        # Set the final time for bin selection as the current time plus the window size
        tf = tc + window_size

        # Pull the bin from the data
        bin = sub_batch[(sub_batch["epochNormalized"] >= t0) & (sub_batch["epochNormalized"] <= tf)]
        
        #-------------------------------#
        print(f"Windowed Bin: {bin["epochNormalized"]}")
        #-------------------------------#

        # Score the bin
        score_temp, orbElems_temp, metadata_temp = basicScoring(code, bin, satData = pd.read_csv("data/satelliteData_full.csv"))
        
        # Save the bin if the score is better than the previous iterations
        if score_temp > score_best:
            score_best = score_temp
            bin_best = bin
            metadata_best = metadata_temp
                
            # Break loop if score is T1
            if score_temp == 4:
                break
                    
        #-------------------------------#
        print(f"Windowed Bin Score: {score_temp}")
        #-------------------------------#

        # Update the current time by one point if slide resolution is zero (observation to observation)
        if slide_res == 0:

            # Update the index to pull item with next smallest normalized time
            i -= 1

            # Update the current time to be the next smallest time
            tc = sub_batch["epochNormalized"].iloc[i]

        # Update the current time based on slide resolution if it is non zero
        else:

            # Update the times for next window check
            tc += slide_res

    # Force final initial time to be one window size before the final epoch (no data loss)
    t0_forced = t_max - window_size

    # Pull the bin
    bin = sub_batch[(sub_batch["epochNormalized"] >= t0_forced) & (sub_batch["epochNormalized"] <= t_max)]
    
    #-------------------------------#
    print(f"Windowed Bin: {bin["epochNormalized"]}")
    #-------------------------------#

    # Score the final bin
    score_temp, orbElems_temp, metadata_temp = basicScoring(code, bin, satData = pd.read_csv("data/satelliteData_full.csv"))
    
    #-------------------------------#
    print(f"Windowed Bin Score: {score_temp}")
    #-------------------------------#

    # Save the bin if better than the previous iteration
    if score_temp > score_best:
        score_best = score_temp
        bin_best = bin
        orbElems_best = orbElems_temp
        metadata_best = metadata_temp

    # Return the best bin of size window size
    return bin_best, score_best, orbElems_best, metadata_best





def bisect(batch, window_size, thresh_des, code):
    '''
    The following function uses overlapping bisection to determine a minimal size 
    sub-batch that can be passed to the slide function. To do this, a batch of data
    is continually bisected with each sub-batch scored. If the score of the sub-batch
    meets the threshold desired, recursive bisection is started.

    INPUTS
    batch :  the dataframe containing the batch of data to be bisected
    window_size :  the size of the user desired window in days
    thresh_des :  the desired threshold for that batch iteration
    code :  DataSet Code object containing the dataset code for that iteration

    OUPUTS
    bin_best :  dataframe containing the data associated with the highest scoring bin 
            within the minimal size sub-batch
    score_best :  the score assocaited with the the best bin
    orbElems_best :  the orbital elements associated with the best bin
    metadata_best :  the metadata associated with the best bin
    '''

    # Initialize variables for best bin and statts
    score_best = -1
    bin_best = None
    orbElems_best = None
    metadata_best = None

    # Define the recursion function for bisecting
    def recurse(sub_batch):

        # Set non local variables to keep track of best bin stats
        nonlocal score_best, bin_best, orbElems_best, metadata_best

        # Get time range of the current bin
        t0 = sub_batch["epochNormalized"].min()
        tf = sub_batch["epochNormalized"].max()
        duration = tf - t0

        # Check threshold of batch/sub-batch as a whole
        check = thresholdCheck(sub_batch, thresh_des, code)

        # If batch contains valid data and is larger than twice the window size
        if check and (duration >= 2.01 * window_size):

            #-------------------------------#
            print("Sub-batch is valid and large enough to be bisected.")
            #-------------------------------#
            
            # Determine the midpoint epoch of the batch
            tm = (t0 + tf) / 2

            # Pull data to the left with half window size overlap
            batch_left = sub_batch[sub_batch["epochNormalized"] >= (tm - 0.5 * window_size)]

            # Pull data to the right with half window size overlap
            batch_right = sub_batch[sub_batch["epochNormalized"] < (tm + 0.5 * window_size)]

            #-------------------------------#
            print(f"Left Sub-batch: {batch_left["epochNormalized"]}")
            #-------------------------------#

            # Call the recursive bisect function for left sub-batch
            recurse(batch_left)

            #-------------------------------#
            print(f"Right Sub-batch: {batch_right["epochNormalized"]}")
            #-------------------------------#

            # Call the recursive bisect function for right sub-batch
            recurse(batch_right)

        # Bin is valid but is minimum size and must be swept
        elif check:

            #-------------------------------#
            print("Sub-batch is valid but not large enough to be bisected.")
            #-------------------------------#
            
            # Call the slide function
            bin_temp, score_temp, orbElems_temp, metadata_temp = slide(sub_batch, window_size, code)

            # Save the score and bin if better than the previous iterations bin
            if score_temp > score_best:
                score_best = score_temp
                bin_best = bin_temp
                orbElems_best = orbElems_temp
                metadata_best = metadata_temp
    
    # Call the intitial recursive bisect
    recurse(batch)

    # Return the best bin and stats
    return bin_best, score_best, orbElems_best, metadata_best





def windowCheck(window_size, batch_size, code, start_epoch, end_epoch, UDL_token):
    '''
    The following function acts as the sub driver for determining the best window of
    data for the given data set code. To do this, multiple iterations of batches are
    ran until the desired threshold is met.

    INPUTS
    window_size :  the size of the user desired window in days
    batch_size :  the size of the user desired batch in days
    code :  DataSet Code object containing the dataset code for that iteration
    start_epoch :  datetime object containing the starting epoch for the first batch
    end_epoch :  datetime object containing the ending epoch for the first batch
    UDL_token :  the users UDL token for data pulling

    OUTPUTS
    bin_best :  dataframe containing the data associated with the highest scoring bin 
            within the minimal size sub-batch
    score_best :  the score assocaited with the the best bin
    orbElems_best :  the orbital elements associated with the best bin
    metadata_best :  the metadata associated with the best bin
    '''
    
    # Pull scoring thresholds from config file
    threshold_scores = thresholdConvert(con.thresholds)

    # Initialize score, bin, and termination flag values for loop
    score_temp = 0
    score_best = -1
    bin_best = None
    bin_best = None
    orbElems_best = None
    metadata_best = None
    
    # Loop through batches until end of thresholds
    for i in range(len(threshold_scores)):

        # Determine threshold to beat
        thresh_des = threshold_scores[i]

        #-------------------------------#
        print(f"Desired threshold: {thresh_des}")
        #-------------------------------#
        
        # Convert to times to UDL format
        start_epoch_UDL = UDL.datetimeToUDL(start_epoch)
        end_epoch_UDL = UDL.datetimeToUDL(end_epoch)

        # Pull the initial data
        data = batchPull(code, start_epoch_UDL, end_epoch_UDL, UDL_token)

        # Convert to datetime object
        data["epoch"] = pd.to_datetime(data["obTime"])
        
        # Sort the observations into chronological order
        data_sorted = data.sort_values(by="epoch").reset_index(drop=True)

        # Normalize the epochs
        data_sorted["epochNormalized"] = normalizeTime(data_sorted)

        #-------------------------------#
        print(f"Current batch: {data_sorted["epochNormalized"]}")
        print(f"Batch Size: {data_sorted["epochNormalized"].max() - data_sorted["epochNormalized"].min()}")
        #-------------------------------#

        # Initial threshold check
        if thresholdCheck(data_sorted, thresh_des, code):

            #-------------------------------#
            print("Bisesct Entered!")
            #-------------------------------#
            
            # Call the bisect function
            bin_temp, score_temp, orbElems_temp, metadata_temp = bisect(data_sorted, window_size, thresh_des, code)

            # Save the best bins score
            if score_temp > score_best:
                score_best = score_temp
                bin_best = bin_temp
                orbElems_best = orbElems_temp
                metadata_best = metadata_temp

        #-------------------------------#
        else:
            print("Bisesct Skipped!")
        #-------------------------------#

        # Exit loop if threshold corresponding to that iteration was exceeded
        if score_best >= thresh_des:
            break

        # Determine the new batch size based on iteration and exp func
        batch_size_current = max(expFunc(window_size, batch_size, i+1, con.batchSizeDecayRate), 2.01 * window_size)
        
        # Determine datetime epochs for new batch, allowing for overlap
        start_epoch = start_epoch - dt.timedelta(days = batch_size_current)
        end_epoch = start_epoch + dt.timedelta(days = window_size)

    # Return the best bin for this iteration
    return bin_best, score_best, orbElems_best, metadata_best





def windowMain(codes, UDL_token):
    '''
    The following funtion is the main driver for determining the best bin of data for every 
    dataset code desired. To do this, the function loops through each dataset code and calls
    sub driver (windowCheck()) to determine the best bin of data.

    INPUTS
    codes :  list of dataset codes
    UDL_token :  the users UDL token for data pulling

    OUTPUTS
    bins :  a list of tuples with the following structure
        --> code :  DataSet Code object containing the dataset code for that iteration
        --> threshold :  the threshold met for that code
        --> bin_best :  dataframe containing the data associated with the best bin
        --> orbElems :  the orbital elements associated with the best bin
        --> metadata :  the scoring metadata associated with the best bin
    '''

    # Initialize list of tuples
    bins = []

    # Loop through each code in list
    for code in codes:

        #-------------------------------#
        print(f"Started Code: {str(code)}")
        #-------------------------------#

        # Convert the code strings to int
        # window_size = int(code.TimeWindow)
        window_size=0.2

        # Define final epoch to start
        end_epoch = dt.datetime.now()

        # Define the initial batch size
        initial_batch_size = con.batchSizeMultiplier*window_size

        # Define initial starting time based on the initial batch size
        start_epoch = end_epoch - dt.timedelta(days = initial_batch_size)
       
        # Call the windowCheck function to determine the best bin for the given code
        bin_best, score, orbElems, metadata = windowCheck(window_size, initial_batch_size, code, start_epoch, end_epoch, UDL_token)

        #-------------------------------#
        print(f"Best Bin: {bin_best["epochNormalized"]}")
        print(f"Best Bin score: {score}")
        #-------------------------------#

        # Convert score to threshold
        thresholds = ['T5', 'T4', 'T3', 'T2', 'T1']
        if score == -1: score = 0
        threshold = thresholds[score]

        # Remove the normalized epoch column
        bin_best.drop(columns=['epochNormalized'], inplace=True)

        # Append the list with current codes best bin
        bins.append((code, threshold, bin_best, orbElems, metadata))

    # Return the list of tuples
    return bins
