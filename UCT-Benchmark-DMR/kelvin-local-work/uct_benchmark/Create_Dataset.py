#                                             #
# UCTP Benchmarker Skeleton: Dataset Creation #
#                                             #

"""Lightweight refactor of the dataset creation driver.

This module separates GUI launching from dataset creation logic so the
GUI can be invoked independently and the dataset creation functions can
be called from tests or a CLI.
"""

import os
import sys
from dotenv import load_dotenv
import duckdb

import pandas as pd
from loguru import logger

from uct_benchmark.config import (
    DATA_DIR,
    EXTERNAL_DATA_DIR,
    INTERIM_DATA_DIR,
    PROJ_ROOT,
)
from uct_benchmark.api import apiIntegration as apiI
from uct_benchmark.data import windowCheck as windowCheck
from uct_benchmark.data import windowTools as windowTools
from uct_benchmark.utils.timerClass import Timer


# load environment variables from .env file if it exists
load_dotenv()


def launch_gui():
    """Launch a GUI to create dataset codes.

    Returns the dataframe produced by the GUI code-generator.
    """
    os.chdir(PROJ_ROOT)
    return windowTools.createDatasetCodeGUI()


def create_datasets_from_codes(
    datasetCodeDataframe, udl_token=None, satellite_data_path=None
):
    """Create datasets from a dataframe of dataset codes.

    Parameters
    - datasetCodeDataframe: dataframe returned by the code-generator GUI
    - udl_token: str or None - token for UDL API calls. If None, uses
      environment variable `UDL_TOKEN`.
    - satellite_data_path: optional Path to satelliteData_Full.csv; if
      not provided a default inside the project is used.

    Returns a list of results returned from apiI.saveDataset.
    """
    os.chdir(PROJ_ROOT)

    t = Timer()
    t.mark("Start")

    # locate satellite data
    if satellite_data_path is None:
        satellite_data_path = EXTERNAL_DATA_DIR / "satellite_data_full.parquet"

    satelliteData = pd.read_parquet(satellite_data_path)

    # If udl_token is not provided, fall back to environment
    if udl_token is None:
        udl_token = os.getenv("UDL_TOKEN")

    # Convert codes to the canonical datasetCodes structure
    datasetCodes = windowTools.codeGenerator(datasetCodeDataframe)
    t.mark("Dataset Codes Created")

    logger.info(f"Starting window selection for {datasetCodes[0]}...")
    bins = windowCheck.windowMain(datasetCodes, udl_token)
    logger.info("Window selection complete.")
    logger.info(f"Generated {len(bins)} dataset bins from "
                f"{len(datasetCodes)} dataset codes.")
    logger.info(f"Processing {datasetCodes[0]}...")

    outputs = []
    for bin_entry in bins:
        # tolerant unpacking in case some legacy tuples omit metadata
        if len(bin_entry) == 5:
            datasetCode = bin_entry[0]
            tierThreshold = bin_entry[1]
            observations = bin_entry[2]
            # fifth element intentionally ignored for now
        elif len(bin_entry) == 4:
            datasetCode = bin_entry[0]
            tierThreshold = bin_entry[1]
            observations = bin_entry[2]
        else:
            logger.warning(f"Unexpected bin structure, skipping: {bin_entry}")
            continue

        satIDs = observations["satNo"].unique()

        # placeholder logic for T4/T3/T2 (keeps existing behavior)
        if tierThreshold == "T4":
            logger.info("T4 processing not implemented; continuing")
        if tierThreshold == "T3":
            logger.info("T3 processing not implemented; continuing")

        endTime = pd.to_datetime(observations["obTime"].max())
        logger.info(f"Pulling reference states up to {endTime} for "
                    f"{len(satIDs)} satellites")
        referenceSVs, referenceTLEs, satList, _ = apiI.pullStates(
            udl_token,
            satIDs,
            int(datasetCode.TimeWindow),
            "days",
            end_time=endTime,
        )

        # Merge mass and crossSection data into referenceSVs
        massCrossSection = satelliteData[["satNo", "mass", "xSectAvg"]].copy()
        massCrossSection.rename(
            columns={"xSectAvg": "crossSection"}, inplace=True
        )
        referenceSVs = pd.merge(
            referenceSVs, massCrossSection, on="satNo", how="left"
        )
        referenceSVs = referenceSVs.fillna({"mass": 0, "crossSection": 0})

        # Build a TLE dataset placeholder (keeps current behaviour)
        TLEdataset = observations[["id", "satNo", "ra", "declination"]].copy()

        # Save debug CSVs (same as previous behaviour)
        observations.to_parquet(
            INTERIM_DATA_DIR / "observations_.parquet", index=False)
        referenceSVs.to_parquet(
            INTERIM_DATA_DIR / "referenceSVs_.parquet", index=False)
        referenceTLEs.to_parquet(
            INTERIM_DATA_DIR / "referenceTLEs_.parquet", index=False)

        output_json = apiI.saveDataset(
            observations,
            TLEdataset,
            referenceSVs,
            referenceTLEs,
            "./data/output_dataset.json",
        )
        outputs.append(output_json)

    logger.info(f"endtime={endTime.strftime('%Y-%m-%dT%H:%M:%S')}")
    logger.info(
        f"Completed processing for Dataset code {datasetCodes[0]}")

    t.mark("Complete")
    t.report()
    return outputs


def main():
    """Launch the dataset code generation GUI."""
    print("Launching dataset code generation GUI...")
    print("This will open a window where you can configure dataset",
          "parameters.")
    print()

    try:
        dataframe = launch_gui()
        session_db_path = DATA_DIR / "session_data.duckdb"
        conn = duckdb.connect(session_db_path)

        if dataframe is not None and not dataframe.empty:
            # create or replace the dataset_codes table
            conn.execute("""CREATE OR REPLACE TABLE dataset_codes AS
                             SELECT * FROM dataframe""")

            print(f"GUI completed successfully. Generated {len(dataframe)}",
                  "dataset configurations.")
            print("To create datasets from these codes, use:")
            print("  from uct_benchmark.Create_Dataset import",
                  "create_datasets_from_codes")
            print("  outputs = create_datasets_from_codes(dataframe)")

            outputs = create_datasets_from_codes(dataframe)
        else:
            print("GUI was cancelled or no configurations were generated.")
    except Exception as e:
        print(f"Error launching GUI: {e}")
        print("Make sure you have the required dependencies installed",
              "and display available.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
