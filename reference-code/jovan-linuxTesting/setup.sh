#!/bin/bash
 
#Checking for .\data and subdirectories
if [ -d "data"]; then
    if [ -d "./data/raw"]; then
        echo "raw directory detected"
    else
        mkdir data/raw
    fi
    if [ -d "./data/interim"]; then
        echo "interim directory detected"
    else
        mkdir data/interim    
    fi
    if [ -d "./data/processed"]; then
        echo "processed directory detected"
    else
        mkdir data/processed
    fi
    if [ -d "./data/external"]; then
        echo "external directory detected"
    else
        mkdir data/external
    fi

else
    mkdir -p data/raw;
    mkdir data/interim;
    mkdir data/processed;
    mkdir data/external;
fi


#Setting up .venv file
data_path=$(pwd)"/data"
env_file=".env"

#Gathering User UDL Token
echo "Please provide UDL token to continue..."
read udl_token

#Setting environment variables
echo "UDL_TOKEN="$udl_token > "$env_file"
echo "JAVA_HOME=jdk4py.JAVA_HOME" >> "$env_file"
echo "REPORTS="$(pwd)"/reports" >> "$env_file"
echo "FIGS="$(pwd)"/reports/figures" >> "$env_file"
echo "EVAL_PDF="$(pwd)"/reports/evaluation_report.pdf" >> "$env_file"
echo "EXT_DIR="$data_path"/external" >> "$env_file"
echo "RAW_DIR="$data_path"/raw" >> "$env_file"
echo "INTERIM_DIR="$data_path"/interim" >> "$env_file"
echo "PROC_DIR="$data_path"/external/processed" >> "$env_file"
echo "SRC_DIR="$(pwd)"/uctbenchmark/src" >> "$env_file"
echo "OBS="$data_path"/external/observations_.csv" >> "$env_file"
echo "REF_OBS="$data_path"/external/ref_obs.csv" >> "$env_file"
echo "REF_ORBITS="$data_path"/external/ref_orbits.csv" >> "$env_file"
echo "REF_SVS="$data_path"/external/referenceSVs_.csv" >> "$env_file"
echo "REF_TLES="$data_path"/external/referenceTLEs_.csv" >> "$env_file"
echo "SAT_DATA="$data_path"/external/satelliteData.csv" >> "$env_file"
echo "SAT_DATA_F="$data_path"/external/satelliteData_Full.csv" >> "$env_file"
echo "DUMMY_DATA="$data_path"/external/dummy_database.csv" >> "$env_file"
echo "SAMPLE_WINDOW="$data_path"/external/sampleWindow.csv" >> "$env_file"
echo "SENSOR_COUNTS="$data_path"/external/sensorCounts.csv" >> "$env_file"
echo "OUTPUT_DATA="$data_path"/interim/output_dataset.json" >> "$env_file"
echo "UCTP_DATA="$data_path"/interim/uctp_output.json" >> "$env_file"
echo "EVAL_RESULTS="$data_path"/interim/raw_results.json" >> "$env_file"
echo "SIM_OBS="$data_path"/interim/simulated_observations.csv" >> "$env_file"



#Checking uv version
python_ver=$(python --version 2>/dev/null | awk '{print $2}')
uv_ver=$(uv --version 2>/dev/null | awk '{print $2}')

#Verifying uv is present
if [ -n "$uv_ver" ]; then 
    echo 'uv has detected; proceeding with activating .venv' 
#Installing uv 
else 
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

#Initializing uv and venv; updating orekit library
uv init
uv venv --clear
uv pip install --upgrade git+https://gitlab.orekit.org/orekit/orekit-data.git



