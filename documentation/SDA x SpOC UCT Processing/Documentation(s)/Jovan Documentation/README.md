# UCTBenchmark Demo 2

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

A packaged representation of the SDA TAP Lab UCTBenchmark MVP still in-process..

## Project Organization

```
├── LICENSE            <- Open-source license if one is chosen
├── Makefile           <- Makefile with convenience commands like `make data` or `make train`
├── README.md          <- The top-level README for developers using this project.
├── data
│   ├── external       <- Data from third party sources.
│   ├── interim        <- Intermediate data that has been transformed.
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── docs               <- A default mkdocs project; see www.mkdocs.org for details
│
├── models             <- Trained and serialized models, model predictions, or model summaries
│
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
│
├── pyproject.toml     <- Project configuration file with package metadata for 
│                         uctbenchmark and configuration for tools like black
│
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
│
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
├── setup.cfg          <- Configuration file for flake8
│
└── uctbenchmark   <- Source code for use in this project.
    │
    ├── __init__.py             <- Makes uctbenchmark a Python module
    │
    ├── config.py               <- Store useful variables and configuration
    │
    ├── dataset.py              <- Scripts to download or generate data
    │
    ├── features.py             <- Code to create features for modeling
    │
    ├── modeling                
    │   ├── __init__.py 
    │   ├── predict.py          <- Code to run model inference with trained models          
    │   └── train.py            <- Code to train models
    │
    └── plots.py                <- Code to create visualizations
```

--------
## Project Prerequisites

The following are required:
- Python >=3.12
- Java >=11*
- Python module `uv`
- Git >=2.51 

*Currently code is setup to run with JDK4PY, logic for system-level dependency has not been implemented. Starting in 2026, Java 21 will be required

## Setup Guide

* Instructions assume git is present and configured with your name and email 

To setup code for local development from the Git Repo:

    1. Open your terminal and navigate to your project folder
    2. Run `git clone -b {branch} {HTTPS:URL}` to clone your branch from the repo
        - Replace **{branch}** and **{HTTPS:URL}** with the branch name and URL pointing to your remote Repository.
    3. Download `data dependencies.zip` from the Google Drive
        - This contains reference data needed for the application to run. It contains `interim` and `external` data directories. 
        - If you unzip contents prior to running setup, you'll need to create your project's data directory in the location showed in our project's organization diagram. The `raw` and `processed` directories will still be generated during setup script execution.
    4. Establish .env file with variables (eg UDL Base64 Token, Local system file paths)
    

### Windows Setup

Run `setup.bat` to finish setup of the application*

    - During setup you'll be prompted for your UDL token
    - Creates data folder structure and configures environment variables
    - If .env file exists, you can overwrite or exit the setup process

*Setup will ignore existing data folders, so that you are safe to load your data dependencies before or after running the script.

### Linux Setup

ACTION NEEDED: Bash script for Linux/Unix systems is still pending development



## Operation & Expected Behavior

The project has been structured so that 3 main scripts `Create_Dataset.py`, `Evaluation.py`, and `MainMVP.py` are executed in 3 phases via the `main.py`. 

    - To run the script, navigate to the project folder in your terminal and enter `uv run py .\main.py`
        - uv will load the project's dependencies during execution of the script. To have a persistent venv, you'll need to `.venv\Scripts\activate`
    - As `main.py` runs it will execute 3 'Phases'
    
        Phase 1 runs `Create_Dataset.py`, if it does not see an `output_json` file already. If there is an existing file, it will prompt you on  whether to continue with Phase 1 or to skip to Phase 2.
                * ACTION NEEDED: Logic will need implemented so that our app can generate and load more than one dataset. 
            - The CustomTKinter GUI will launch with the default parameters set to the known working configuration. You can customize the parameters and scroll down to run
                * ACTION NEEDED: Logic needs implemented for error handling during UDL request, empty UDL responses, partial UDL requests (if existing data under `raw` directory) and validating all parameter configurations query successfully
            - After saving the parameter set, a folder is created under `.\data\raw` as `{Parameters}_{App Version}_{Timestamp}`
                - You will see the app generate JSON files containing UDL's responses to our query, divided into 24-hour increments.
            - The app will evaluate the responses in a "binning" process and announce when transformations (ie downsampling & simulation) should've been applied for batches evaluated below tier I.
                * ACTION NEEDED: Downsampling and data simulation are not implemented
            - Finally the app pulls the reference SV & TLEs and generate `ref_obs.csv`, `referenceSVs_.csv` and `referenceTLEs_.csv` alongside the `output_dataset.json` file
    
    Phase 2 runs `mainMVP.py` which is intended to immulate UCTP output.

        - This phase can likely be removed in place of more standardized testing & development methods, as it's intention is to generate input for our evaluation reports for Phase 3. A static evaluation test set would serve this function and functionally separate our pipelines for generating datasets and evaluating UCTP performance

    Phase 3 runs `Evaluation.py` which imports our generated dataset and begins evaluating the dummy UCTP output against the ground truth
        ACTION NEEDED: App currently uses reference CSVs for inputs during evaluation. I'm unsure if this information is static or is interlinked with the `output_dataset.json` file. These may need stored in a similar fashion to the batch pulls, where they are saved under a `{Parameters}_{App Version}_{Timestamp}` subdirectory 

        - After reading data, app will take the reference SVs and output_dataset in order to associate orbits
        - Binary, Orbital State and Residual metrics are evaluated
        and saved under `.\reports\report.pdf`

After Completing all 3 Phases, `main.py` is currently set to exit the session. In future versions, we may want to have the application able to run in an iterable way, so that the session persists after execution and until the user exits.

