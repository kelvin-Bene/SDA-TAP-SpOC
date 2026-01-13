# Scrape Current Elsets from UDL for all known satellites
# Scrape mass and cross section data from ESA for all known satellites
# Combine information by NORAD ID and save to .csv

import base64

import numpy as np
import os
import pandas as pd
from dotenv import load_dotenv
import requests

from uct_benchmark.config import EXTERNAL_DATA_DIR


# Constants
MAX_SATELLITES = 65000
BATCH_SIZE = 30
UDL_BASE_URL = "https://unifieddatalibrary.com/udl/elset/current"

# Column names to keep in final dataset
KEEP_COLUMNS = [
    'cosparId', 'satno', 'satNo', 'name', 'objectClass', 'mass', 'shape',
    'width', 'height', 'depth', 'diameter', 'span', 'xSectMax', 'xSectMin',
    'xSectAvg', 'firstEpoch', 'active', 'idElset', 'epoch', 'meanMotion',
    'eccentricity', 'inclination', 'raan', 'argOfPerigee', 'meanAnomaly',
    'bStar', 'meanMotionDot', 'semiMajorAxis', 'period', 'apogee', 'perigee',
    'line1', 'line2'
]

# Orbital regime thresholds (km)
LEO_THRESHOLD = 6731 + 1500
GEO_THRESHOLD = 35000
HEO_ECCENTRICITY_THRESHOLD = 0.7
HAMR_THRESHOLD = 1.0


# load environment variables from .env file
load_dotenv()


def discoswebQuery(token, params, data='objects', version=2):
    """
    Performs an ESA Discosweb search using the given parameters.

    Args:
        token (str): Your ESA Discosweb access token. If you don't have one,
            generate one at https://discosweb.esoc.esa.int/tokens.
        params (str): A string of search parameters in the form
            "searchTerm1&searchTerm2". Please read
            https://discosweb.esoc.esa.int/apidocs/v2 for formatting.
        data (str): The requested data type from Discosweb.
            Defaults to "objects".
        version (int): The requested Discosweb API version.
            Defaults to version 2.

    Returns:
        pd.DataFrame: The results of your query.

    Raises:
        TypeError: If input types are incorrect.
        requests.exceptions.HTTPError: If login or query fails.
    """

    # Error handling
    if not (isinstance(token, str) and isinstance(data, str) and
            isinstance(params, str) and isinstance(version, int)):
        raise TypeError(
            f"Expected (str, str, str, int), got "
            f"({type(token).__name__}, {type(params).__name__}, "
            f"{type(data).__name__}, {type(version).__name__}) instead."
        )

    # Set up query
    base_url = 'https://discosweb.esoc.esa.int'

    auth = {
        'Authorization': f'Bearer {token}',
        'DiscosWeb-Api-Version': str(version)
    }

    # Perform query
    resp = requests.get(
        f'{base_url}/api/{data}',
        headers=auth,
        params={'filter': params},
    )

    if resp.status_code != 200:
        if resp.status_code == 429:
            raise requests.exceptions.HTTPError(
                resp, "Query failed due to API rate limit (429). Slow down!"
            )
        else:
            raise requests.exceptions.HTTPError(
                resp, f"Query failed for unknown reason ({resp.status_code}); "
                "double-check login info and query parameters."
            )
    return pd.DataFrame(resp.json()["data"])


def scrape_udl_data():
    """Scrape satellite data from UDL API."""
    # Load UDL token from environment variable
    # Specify the UDL_TOKEN environment variable in your .env file
    # before running this script.
    token = os.environ.get('UDL_TOKEN')
    basic_auth = "Basic " + token

    udl_data_frames = []

    # Query satellite data in batches
    batch_ranges = [
        ("<30000", "first 30000 satellites"),
        ("30000..60000", "next 30000 satellites"),
        ("60000..65000", "final 5000 satellites")
    ]

    for range_param, description in batch_ranges:
        print(f"Querying {description}...")
        url = f"{UDL_BASE_URL}?satNo={range_param}"

        try:
            resp = requests.get(
                url,
                headers={'Authorization': basic_auth},
                verify=False
            )
            resp.raise_for_status()
            udl_data_frames.append(pd.DataFrame(resp.json()))
        except requests.RequestException as e:
            print(f"Error querying {description}: {e}")
            continue

    if not udl_data_frames:
        raise RuntimeError("Failed to retrieve any UDL data")

    return pd.concat(udl_data_frames, ignore_index=True)


def scrape_esa_data():
    """Scrape satellite data from ESA Discosweb API."""
    # Load ESA token from environment variable
    # Specify the ESA_TOKEN environment variable in your .env file
    esa_token = os.environ.get('ESA_TOKEN')

    if not esa_token:
        print(
            "Warning: Using placeholder ESA token. Replace with actual token."
        )

    max_iterations = int(np.ceil(MAX_SATELLITES / BATCH_SIZE))
    esa_data_frames = []

    for i in range(max_iterations):
        sat_ids = list(range(i * BATCH_SIZE, (i + 1) * BATCH_SIZE))
        params = (
            "in(satno,(" +
            ",".join(map(str, sat_ids)) +
            "))"
        )

        try:
            resp = discoswebQuery(esa_token, params)
            temp = pd.json_normalize(resp['attributes'])
            esa_data_frames.append(temp)
        except (requests.RequestException, KeyError, ValueError) as e:
            print(
                f"Error querying ESA data for satellites "
                f"{sat_ids[0]}-{sat_ids[-1]}: {e}"
            )
            continue

    if not esa_data_frames:
        print("Warning: No ESA data retrieved")
        return pd.DataFrame()

    return pd.concat(esa_data_frames, ignore_index=True)


def classify_orbital_regimes(df):
    """Add orbital regime classifications to the dataframe."""
    # Identify Orbital Regime (LEO, MEO, GEO, HEO)
    df['GEO'] = (
        df['semiMajorAxis'].notna() &
        (df['semiMajorAxis'] > GEO_THRESHOLD)
    )
    df['LEO'] = (
        df['semiMajorAxis'].notna() &
        (df['semiMajorAxis'] < LEO_THRESHOLD)
    )
    df['MEO'] = (
        df['semiMajorAxis'].notna() &
        ~(df['GEO'] | df['LEO'])
    )
    df['HEO'] = (
        df['eccentricity'].notna() &
        (df['eccentricity'] > HEO_ECCENTRICITY_THRESHOLD)
    )
    return df


def calculate_amr_and_hamr(df):
    """Calculate Area-to-Mass Ratio and HAMR classification."""
    df['AMR'] = df['xSectAvg'] / df['mass']
    df['HAMR'] = df['AMR'] > HAMR_THRESHOLD
    return df


def main():
    """Main function to scrape and process satellite data."""
    print("Starting satellite data scraping...")

    # Scrape UDL data
    print("Scraping UDL data...")
    udl_data = scrape_udl_data()
    print(f"Retrieved {len(udl_data)} records from UDL")

    # Scrape ESA data
    print("Scraping ESA data...")
    esa_data = scrape_esa_data()
    print(f"Retrieved {len(esa_data)} records from ESA")

    # Merge dataframes by satellite number
    print("Merging datasets...")
    merged_data = pd.merge(
        esa_data, udl_data,
        left_on='satno', right_on='satNo',
        how='outer'
    )

    # Filter to relevant columns
    available_columns = [
        col for col in KEEP_COLUMNS if col in merged_data.columns
    ]
    merged_data = merged_data[available_columns]

    # Add orbital regime classifications
    merged_data = classify_orbital_regimes(merged_data)

    # Calculate AMR and HAMR
    merged_data = calculate_amr_and_hamr(merged_data)

    # Save dataframe to csv
    #   - original version: output_file = 'satelliteData_Full.csv'
    output_file = EXTERNAL_DATA_DIR / 'satellite_data_full.parquet'
    merged_data.to_parquet(output_file, index=False)
    print(f"Saved {len(merged_data)} records to {output_file}")

    return merged_data


if __name__ == "__main__":
    main()
