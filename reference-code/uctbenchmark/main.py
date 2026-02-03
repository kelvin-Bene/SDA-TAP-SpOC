import os, sys, subprocess, time
from dotenv import load_dotenv

#Loading environment variables
load_dotenv() 

from uctbenchmark.src.libraries.dummyUCTP import dummy as UCTP


home_dir = os.getenv("HOME_DIR")
src_dir = os.getenv("SRC_DIR")
raw_dir = os.getenv("RAW_DIR")
ext_dir = os.getenv("EXT_DIR")
int_dir = os.getenv("INT_DIR")
proc_dir = os.getenv("PROC_DIR")

def runUCTP():
    #Changing working directory
    os.chdir(src_dir)

    print("Running dummy UCTP")
    UCTP(ref_obs, "")


if __name__ == "__main__":

    from uctbenchmark.src.Create_Dataset import create_dataset
    from uctbenchmark.src.Evaluation import evaluate_results

    udl_token = os.getenv("UDL_TOKEN")
    sat_data_f = os.getenv("SAT_DATA_F")
    obs = os.getenv("OBS")
    ref_obs = os.getenv("REF_OBS")
    ref_svs = os.getenv("REF_SVS")
    ref_tles = os.getenv("REF_TLES")
    
    uctp_data = os.getenv("UCTP_DATA")
    output_dataset = os.getenv("OUTPUT_DATA")
    eval_results = os.getenv("EVAL_RESULTS")
    eval_pdf = os.getenv("EVAL_PDF")
    
    
    # Generating dataset
    print("Phase 1: Running sample dataset GUI...")
    time.sleep(2)

    #Checking if dataset exists 
    if os.path.isfile(output_dataset):
        load_existing_dataset = input('Dataset detected, continue with Phase 2? (y/n): ')
        if str(load_existing_dataset).casefold().startswith('n'):
            #Generating new dataset
            create_dataset(udl_token, sat_data_f, obs, ref_svs, ref_tles, output_dataset, raw_dir)
    
    #Running dummy UCTP 
    print("Phase 2: Feeding dataset to UCTP...")
    time.sleep(2)
    runUCTP()

    #Running Evaluation
    print("Phase 3: Evaluating Results...")
    time.sleep(2)

    evaluate_results(uctp_data, output_dataset, eval_results, eval_pdf)

    print("Evaluation Complete")
    print("PDF of results is located within your 'reports' directory")
    


