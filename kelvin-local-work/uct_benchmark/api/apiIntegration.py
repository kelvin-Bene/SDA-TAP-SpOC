# -*- coding: utf-8 -*-
"""
Created on Fri Jun  6 08:51:11 2025

@author: Gabriel Lundin
"""

import asyncio
import base64
import datetime
import json
import os
import re
import time
import warnings

import aiohttp
import numpy as np

import pandas as pd
import requests
from loguru import logger

# initialize orekit and JVM
# - This must be done only once per program execution -
# - If orekit is already initialized, these lines will have no effect -
# - Using orekit_jpype as it is better maintained -
# - Expecting OREKIT_DATA_PATH environment variable to be set -
import orekit_jpype as orekit
vm_started = orekit.initVM()
from orekit_jpype.pyhelpers import setup_orekit_curdir
orekit_data_path = os.getenv("OREKIT_DATA_PATH", "./orekit-data-main")
# setup_orekit_curdir(orekit_data_path)
setup_orekit_curdir(from_pip_library=True)

from org.orekit.propagation.analytical.tle import TLE, TLEPropagator
from uct_benchmark.data.dataManipulation import binTracks
from uct_benchmark.config import INTERIM_DATA_DIR


# Because HTTPS is annoying
def _supressWarn():
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")


def UDLTokenGen(username, password):
    """
    Generates a UDL token with your login information if you don't already have one.
    WARNING: This function is not encrypted. If your login is sensitive, PLEASE MANUALLY GENERATE YOUR TOKEN.

    Args:
        username (string): Your UDL username.
        password (string): Your UDL password.

    Returns:
        string: Your UDL Base64 token for login.

    Raises:
        TypeError: If either input is not a string.
    """

    if not all(isinstance(var, str) for var in [username, password]):
        raise TypeError(
            f"Username and password must be strings, got types {type(username).__name__} and {type(password).__name__} instead."
        )
    return base64.b64encode((username + ":" + password).encode("utf-8")).decode("ascii")


def spacetrackTokenGen(username, password):
    """
    Generates a Space-Track token with your login information.
    This is specific to this API integration and cannot be generated on Space-Track's website.

    Args:
        username (string): Your Space-Track username.
        password (string): Your Space-Track password.

    Returns:
        dict: Your Space-Track token for login.

    Raises:
        TypeError: If either input is not a string.
    """

    if not all(isinstance(var, str) for var in [username, password]):
        raise TypeError(
            f"Username and password must be strings, got types {type(username).__name__} and {type(password).__name__} instead."
        )
    return {"identity": username, "password": password}


def UDLQuery(token, service, params, count=False, history=False):
    """
    Performs a UDL search using the given parameters.

    Args:
        token (string): Your UDL Base64 login token. If you don't have one, use UDLTokenGen or the Utilities page of the UDL Help site.
        service (string): The service requested from UDL.
        params (dict): A dictionary of search parameters in the form {'parameter': 'value'}. The following symbols are accepted before value (for equal, leave prefix blank):
            '~value': not equal
            '*value*': like
            '>value': greater than or equal to
            '<value': less than or equal to
            'value1..value2': between
            'value1,value2': in
        Specific parameters valid for all queries are:
            sort: 'value,ASC/DESC'
            maxResults: 'amount'
            fistResult: 'amount' (offsets search)
            columns: 'value1,value2' (constrains result columns)
        For time-based values, the following format is required: 'YYYY-MM-DDTHH:MM:SS.sZ'. Note that the quantity of 's' depends on your service and parameter.
        count (bool): If True, returns a count query instead of a data one. Defaults to False.
        history (bool): If True, uses the History Rest API instead of the standard Rest API. Defaults to False.

    Returns:
        Pandas DataFrame: The results of your query (count = False)
        int: The count for your query (count = True)

    Raises:
        TypeError: If input types are incorrect.
        HTTPError: If query fails.
    """

    # Error handling
    _supressWarn()

    if not (
        isinstance(token, str)
        and isinstance(service, str)
        and isinstance(params, dict)
        and isinstance(count, bool)
        and isinstance(history, bool)
    ):
        raise TypeError(
            f"Expected (string, string, dict, bool, bool), got ({type(token).__name__}, {type(service).__name__}, {type(params).__name__}, {type(count).__name__}, {type(history).__name__}) instead."
        )

    # Set up params for call
    basicAuth = "Basic " + token

    url = "https://unifieddatalibrary.com/udl/" + service.lower()
    if history:
        url = url + "/history"
    if count:
        url = url + "/count"

    # Call
    logger.info(f"Performing UDL query on service '{service}' with parameters={params}...")
    resp = requests.get(url, headers={"Authorization": basicAuth}, params=params, verify=False)

    # If call worked, return data
    if resp.status_code != 200:
        if resp.status_code == 400:
            raise requests.exceptions.HTTPError(resp, "Query failed due to bad parameters.")
        elif resp.status_code == 401:
            raise requests.exceptions.HTTPError(resp, "Query failed due to invalid login.")
        elif resp.status_code == 500:
            raise requests.exceptions.HTTPError(
                resp,
                "Query failed due to internal error; if UDL isn't down, likely a time-out for excessive data request.",
            )
        else:
            raise requests.exceptions.HTTPError(resp, "Query failed for unknown reason.")

    if not count:
        return pd.DataFrame(resp.json())
    else:
        return resp.json()


def TLEToSV(line1, line2):
    """
    Uses Orekit to obtain a state vector for a given TLE.

    Args:
        line1 (string): TLE line 1.
        line2 (string): TLE line 2.

    Returns:
        Numpy Array: (6,) Numpy array containing the corresponding state vector in km and km/s.

    Raises:
        TypeError: If inputs are not strings.
    """

    # Error handling
    if not all(isinstance(var, str) for var in [line1, line2]):
        raise TypeError(
            f"TLE lines must be strings, got types {type(line1).__name__} and {type(line2).__name__} instead."
        )

    # Set up Orekit TLE
    tle = TLE(line1, line2)
    propagator = TLEPropagator.selectExtrapolator(tle)
    date = tle.getDate()

    # Obtain and parse state vector
    pv_coords = propagator.getPVCoordinates(date)
    position = np.array(pv_coords.getPosition().toArray()) / 1000.0  # m to km
    velocity = np.array(pv_coords.getVelocity().toArray()) / 1000.0  # m/s to km/s
    return np.hstack((position, velocity))


def parseTLE(line1, line2):
    """
    Parses a TLE given in standard UDL form.

    Args:
        line1, line2 (string): lines 1 and 2 of a TLE

    Returns:
        dict: A dict containing the TLE information in the following format:
            'NORAD_ID': int
            'classification': string
            'COSPAR_ID': string
            'epoch': datetime
            'BC': float
            'n_ddot': float
            'B_star': float
            'ephemeris_type': int
            'elset_num': int
            'inclination': float
            'RAAN': float
            'eccentricity': float
            'perigee': float
            'mean_anomaly': float
            'mean_motion': float
            'rev_num': int
            'line1': string
            'line2': string

    Raises:
        TypeError: If inputs are not strings.
    """

    # Error handling
    if not all(isinstance(var, str) for var in [line1, line2]):
        raise TypeError(
            f"TLE lines must be strings, got types {type(line1).__name__} and {type(line2).__name__} instead."
        )

    TLE = line1 + " " + line2
    lines = TLE.split()

    # Fix potential lack of end values (thanks Orekit)
    if len(lines) > 17:
        lines = lines[:16] + ["".join(lines[16:]).replace(" ", "0")]

    # TLE parsing
    elset = {
        "NORAD_ID": int(lines[1][0:-1]),
        "classification": lines[1][-1],
        "COSPAR_ID": lines[2],
        "BC": float(re.sub(r"^([+-]?)(\d{5})([+-]\d)$", r"\g<1>0.\g<2>e\g<3>", lines[4])),
        "n_ddot": float(re.sub(r"^([+-]?)(\d{5})([+-]\d)$", r"\g<1>0.\g<2>e\g<3>", lines[5]))
        if lines[5] != "00000-0"
        else 0.0,
        "B_star": float(re.sub(r"^([+-]?)(\d{5})([+-]\d)$", r"\g<1>0.\g<2>e\g<3>", lines[6]))
        if lines[6] != "00000-0"
        else 0.0,
        "ephemeris_type": int(lines[7]),
        "elset_num": int(lines[8][0:-1]),
        "inclination": float(lines[11]),
        "RAAN": float(lines[12]),
        "eccentricity": float(lines[13]) / (10**7),
        "perigee": float(lines[14]),
        "mean_anomaly": float(lines[15]),
        "mean_motion": float(lines[16][0:11]),
        "rev_num": int(lines[16][11:-1]),
        "line1": line1,
        "line2": line2,
    }

    # Format epoch year correctly
    year = int(lines[3][0:2])
    if year > 56:
        year += 1900
    else:
        year += 2000

    elset["epoch"] = datetime.datetime(year, 1, 1) + datetime.timedelta(
        days=float(lines[3][2:]) - 1
    )

    return elset


def spacetrackQuery(token, params, request="satcat", controller="basicspacedata"):
    """
    Performs a Space-Track search using the given parameters.

    Args:
        token (dict): Your Space-Track login token. If you don't have one, use spacetrackTokenGen.
        params (dict): A dictionary of search parameters in the form {'parameter': 'value'}. The following symbols are accepted before value (for equal, leave prefix blank):
            '<>value': not equal
            '~~value': like
            '^value': like (after value only)
            '>value': greater than or equal to
            '<value': less than or equal to
            'value1--value2': between
            'value1,value2': or
        Specific parameters valid for all queries are:
            orderby: 'VALUE asc/desc' (VALUE must be all caps)
            metadata: 'true'
            emptyresult: 'show'
        For time-based values, the following format is required: 'YYYY-MM-DD'.
        request (string): The request class desired from Space-Track. Defaults to "satcat".
        controller (string): The controller requested from Space-Track. Defaults to "basicspacedata"

    Returns:
        Pandas DataFrame: The results of your query.

    Raises:
        TypeError: If input types are incorrect.
        HTTPError: If login or query fails.
    """

    # Error handling
    _supressWarn()

    if not (
        isinstance(token, dict)
        and isinstance(controller, str)
        and isinstance(params, dict)
        and isinstance(request, str)
    ):
        raise TypeError(
            f"Expected (dict, dict, string, string), got ({type(token).__name__}, {type(params).__name__}, {type(request).__name__}, {type(controller).__name__}) instead."
        )

    # Set up query params
    uriBase = "https://www.space-track.org"
    requestLogin = "/ajaxauth/login"
    requestCmdAction = "/" + controller + "/query"
    requestFind = "/class/" + request
    requestFind.join(f"/{k.upper()}/{v}" for k, v in params.items())

    # Spacetrack requires lowercase
    if any(k.lower() == "format" for k in params):
        params = {k: v for k, v in params.items() if k.lower() != "format"}

    # Perform query
    with requests.Session() as session:
        resp = session.post(uriBase + requestLogin, data=token)
        if resp.status_code != 200:
            raise requests.exceptions.HTTPError(resp, "Login failed; double-check login info.")

        resp = session.get(uriBase + requestCmdAction + requestFind)
        if resp.status_code != 200:
            if resp.status_code == 500:
                raise requests.exceptions.HTTPError(
                    resp, "Query failed due to throttle limit (500); please slow down!"
                )
            if resp.status_code == 401:
                raise requests.exceptions.HTTPError(
                    resp, "Query failed due to bad credentials (401)."
                )
            else:
                raise requests.exceptions.HTTPError(
                    resp,
                    "Query failed for unknown reason ("
                    + str(resp.status_code)
                    + "); double-check search parameters.",
                )

        session.close()
    return pd.DataFrame(resp.json())


def discoswebQuery(token, params, data="objects", version=2):
    """
    Performs an ESA Discosweb search using the given parameters.

    Args:
        token (string): Your ESA Discosweb access token. If you don't have one, generate one at https://discosweb.esoc.esa.int/tokens.
        params (dict): A string of search parameters in the form "searchTerm1&searchTerm2". Please read https://discosweb.esoc.esa.int/apidocs/v2 for formatting.
        data (string): The requested data type from Discosweb. Defaults to "objects".
        version (int): The requested Discosweb API version. Defaults to version 2.

    Returns:
        Pandas DataFrame: The results of your query.

    Raises:
        TypeError: If input types are incorrect.
        HTTPError: If login or query fails.
    """

    # Error handling
    if not (
        isinstance(token, str)
        and isinstance(data, str)
        and isinstance(params, str)
        and isinstance(version, int)
    ):
        raise TypeError(
            f"Expected (string, string, string, int), got ({type(token).__name__}, {type(params).__name__}, {type(data).__name__}, {type(version).__name__}) instead."
        )

    # Set up query
    URL = "https://discosweb.esoc.esa.int"

    auth = {"Authorization": f"Bearer {token}", "DiscosWeb-Api-Version": str(version)}

    # Perform query
    resp = requests.get(
        f"{URL}/api/{data}",
        headers=auth,
        params={"filter": params},
    )

    if resp.status_code != 200:
        if resp.status_code == 429:
            raise requests.exceptions.HTTPError(
                resp, "Query failed due to API rate limit (429). Slow down!"
            )
        else:
            raise requests.exceptions.HTTPError(
                resp,
                "Query failed for unknown reason ("
                + str(resp.status_code)
                + "); double-check login info and query parameters.",
            )
    return pd.DataFrame(resp.json()["data"])


def celestrakSatcat():
    """
    Grabs the entire CelesTrak satcat. Probably very slow.

    Returns:
        Pandas DataFrame: The sat cat.
    """

    URL = "https://celestrak.org/pub/satcat.csv"

    return pd.read_csv(URL)


def celestrakQuery(params, table="gp"):
    """
    Performs a CelesTrak search using the given parameters.

    Args:
        params (dict): A dictionary of search parameters in the form {'parameter': 'value'}. Inequalities are not accepted for this type of query.
        table (string): The requested CelesTrak database, either gp variants or satcat. Defaults to "gp".

    Returns:
        Pandas DataFrame: The results of your query.

    Raises:
        TypeError: If input types are incorrect.
        HTTPError: If query fails.
    """

    # Error handling
    if not (isinstance(params, dict) and isinstance(table, str)):
        raise TypeError(
            f"Expected (dict, string), got ({type(params).__name__}, {type(table).__name__}) instead."
        )

    # Set up query
    if table.lower() == "satcat":
        URL = "https://celestrak.org/satcat/records.php"
    else:
        URL = "https://celestrak.org/NORAD/elements/" + table.lower() + ".php"

    params = {k.upper(): v for k, v in params.items() if k.upper() != "FORMAT"}

    params["FORMAT"] = "JSON"

    # Perform query
    resp = requests.get(
        URL,
        params=params,
    )

    if resp.status_code != 200:
        raise requests.exceptions.HTTPError(
            resp,
            "Query failed for unknown reason ("
            + str(resp.status_code)
            + "); double-check query parameters.",
        )
    return pd.DataFrame(resp.json())


def datetimeToUDL(time, micro=6):
    """
    Converts a datetime object to UDL formatting.

    Args:
        time (datetime.datetime): Time you wish to convert.
        micro (int): Amount of fraction-second precision needed. Max and defaults to 6.

    Returns:
        String: UDL-formatted timestamp.

    Raises:
        TypeError: If input types are incorrect.
    """

    if not isinstance(micro, int):
        raise TypeError(f"Expected micro to  be an int, got {type(micro).__name__}) instead.")

    micro = max(micro, 6)

    return time.strftime("%Y-%m-%dT%H:%M:%S.") + str(time.microsecond)[0:micro] + "Z"


def UDLToDatetime(time):
    """
    Converts a UDL formatted timestamp to a datetime object.

    Args:
        time (string): Timestamp you wish to convert.

    Returns:
        datetime.datetime: Datetime object.

    Raises:
        TypeError: If input types are incorrect.
    """

    return datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S.%fZ")


async def _asyncUDLQuery(token, service, params, count=False, history=False):
    """
    Async version of UDLQuery using aiohttp.
    """

    # Error handling
    if not (
        isinstance(token, str)
        and isinstance(service, str)
        and isinstance(params, dict)
        and isinstance(count, bool)
        and isinstance(history, bool)
    ):
        raise TypeError(
            f"Expected (string, string, dict, bool, bool), got "
            f"({type(token).__name__}, {type(service).__name__}, "
            f"{type(params).__name__}, {type(count).__name__}, {type(history).__name__})"
        )

    # Form query params
    base_url = "https://unifieddatalibrary.com/udl/"
    url = base_url + service.lower()
    if history:
        url += "/history"
    if count:
        url += "/count"

    headers = {"Authorization": "Basic " + token}

    # Perform async query
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params, ssl=False) as response:
            if response.status != 200:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message="Query failed. Common status codes: 400 - bad params, 401 - invalid login, 500 - internal error (UDL down or time-out).",
                )
            data = await response.json()
            return data if count else pd.DataFrame(data)


async def _batchUDLQuery(token, service, params_list, dt=1.0, count=False, history=False):
    """
    Internal wrapper for _asyncUDLQuery() that performs the asyncio calls.
    """
    results = []

    # This is used to enforce rate limit
    async def limited_query(index, params):
        await asyncio.sleep(index * dt)
        return await _asyncUDLQuery(token, service, params, count, history)

    tasks = [limited_query(i, p) for i, p in enumerate(params_list)]
    results = await asyncio.gather(*tasks)

    return sum(results) if count else pd.concat(results, ignore_index=True)


def asyncUDLBatchQuery(token, service, params_list, dt=0.1, count=False, history=False):
    """
    Performs an async batch of UDL searchs using the given parameters.

    Args:
        token (string): Your UDL Base64 login token. If you don't have one, use UDLTokenGen or the Utilities page of the UDL Help site.
        service (string): The service requested from UDL.
        params_list (list): A list of params sent into UDLQuery. Read that documentation for more information.
        dt (float): Rate limit for UDL calls in seconds. Defaults to 1 second.
        count (bool): If True, returns a count query instead of a data one. Defaults to False.
        history (bool): If True, uses the History Rest API instead of the standard Rest API. Defaults to False.

    Returns:
        Pandas DataFrame: The results of your queries concated (count = False)
        int: The sum of all query counts (count = True)

    Raises:
        TypeError: If input types are incorrect.
        ClientResponseError: If a query fails.
    """
    # Try-Except to handle certain Python clients which already run an async loop
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_batchUDLQuery(token, service, params_list, dt, count, history))
    else:
        import nest_asyncio

        nest_asyncio.apply()
        return asyncio.get_event_loop().run_until_complete(
            _batchUDLQuery(token, service, params_list, dt, count, history)
        )


def generateDataset(
    UDL_token, ESA_token, satIDs, timeframe, timeunit, dt=0.1, max_datapoints=0, end_time="now"
):
    """
    Generates a benchmark  dataset given satellites and various parameters.

    Args:
        UDL_token (string): Your UDL Base64 login token. If you don't have one, use UDLTokenGen or the Utilities page of the UDL Help site.
        ESA_token (string): Your ESA Discosweb access token. If you don't have one, generate one at https://discosweb.esoc.esa.int/tokens.
        satIDs (numpy Array): List of satellites you wish to pull obs from.
        timeframe (int): Timespan of sweep.
        timeunit (string): Unit of timeframe.
        dt (float): Rate limit for UDL calls in sec. Please check EULA or contact Bluestack before making this very small. Defaults to 0.1.
        max_datapoints (int): If > 0, limit of obs data return per satellite, returning newest obs. Defaults to 0 (disabled), max 10000.
        end_time (datetime.datetime): Sets the end time of the data timespan. Defaults to 'now' which sets end to current time.

    Returns:
        Pandas DataFrame: A dataset of "uct" observations.
        Pandas DataFrame: The truth observations, matched using "id" field.
        Pandas DataFrame: The truth state vectors of requested satellites.
        Pandas DataFrame: The truth TLEs of requested satellites.
        Array (int): All satellites that were actually obtained.
        Dict: Various runtime data.

    Raises:
        TypeError: If input types are incorrect.
        HTTPError/ClientResponseError: If a query fails.
    """

    # Start timing the entire operation
    start_time = time.perf_counter()

    # Determine the time window for observation data based on the user-specified end_time
    if end_time != "now":
        # Construct a UDL time range string from (end_time - timeframe) to end_time
        sweep_time = (
            datetimeToUDL(end_time - pd.Timedelta(**{timeunit: timeframe}))
            + ".."
            + datetimeToUDL(end_time)
        )
    else:
        # Use relative time if 'now' is specified
        sweep_time = ">now-" + str(timeframe) + " " + timeunit

    # Prepare a list of parameter dictionaries for each satellite to query observation data
    params_list = [
        {
            "satNo": str(ID),
            "obTime": sweep_time,
            "uct": "false",  # Only real (non-UCT) data
            "dataMode": "REAL",
            "maxResults": max_datapoints,
        }
        for ID in satIDs
    ]

    # Remove 'maxResults' if the user disabled the limit (<= 0)
    if max_datapoints <= 0:
        params_list = [{k: v for k, v in d.items() if k != "maxResults"} for d in params_list]

    # Perform asynchronous UDL query for observational truth data
    obs_truth_data = asyncUDLBatchQuery(UDL_token, "eoobservation", params_list, dt)

    # Convert observation times to datetime objects
    obs_truth_data["obTime"] = [UDLToDatetime(t) for t in obs_truth_data["obTime"]]

    # Cull satIDs list to only include those for which data was actually returned
    requested_sats = len(satIDs)
    satIDs = obs_truth_data["satNo"].unique()
    obs_sats = len(satIDs)

    # Compute elapsed time for the observation query step
    obs_elapsed_time = time.perf_counter() - start_time

    # Grabs state vector data
    # Required to do batch call (no access to statevector/current)
    params_list = [
        {
            "satNo": str(ID),
            "epoch": sweep_time,
            "uct": "false",
            "dataMode": "REAL",
            "sort": "epoch,DESC",
        }
        for ID in satIDs
    ]

    state_truth_data = asyncUDLBatchQuery(UDL_token, "statevector", params_list, dt)

    # Remove duplicate state vectors and prioritize ones with covariance
    if state_truth_data["satNo"].nunique() < len(state_truth_data):
        df = state_truth_data.copy()
        # Create helper column to track presence of covariance
        cov_sources = ["eqCov", "cov"]
        df["has_cov"] = np.any(
            [
                df[col].notna() if col in df.columns else pd.Series(False, index=df.index)
                for col in cov_sources
            ],
            axis=0,
        )

        # Keep only rows with covariance
        df_with_cov = df[df["has_cov"]]

        # If no covariance for a satellite, it will disappear here
        if not df_with_cov.empty:
            # Sort by epoch descending so most recent first
            df_with_cov_sorted = df_with_cov.sort_values(by="epoch", ascending=False)

            # Select the most recent row WITH covariance for each satellite
            state_truth_data = (
                df_with_cov_sorted.groupby("satNo", group_keys=False)
                .head(1)
                .reset_index(drop=True)
            )
        else:
            # If absolutely no covariance anywhere, result is empty
            state_truth_data = df_with_cov.copy()

        # Drop the helper column if it still exists
        state_truth_data = state_truth_data.reset_index(drop=True)
        state_truth_data.drop(columns="has_cov", inplace=True, errors="ignore")

    # Convert epoch times to datetime
    state_truth_data["epoch"] = [UDLToDatetime(t) for t in state_truth_data["epoch"]]

    # Format drag coeff and solar rad coeff correctly
    cols_to_fill = ["dragCoeff", "solarRadPressCoeff"]
    for col in cols_to_fill:
        if col not in state_truth_data.columns:
            state_truth_data[col] = 0
        else:
            state_truth_data[col] = state_truth_data[col].fillna(0)

    # If a satellite has no orbit data, drop it from list and obs
    satIDs = state_truth_data["satNo"].unique()
    orbit_sats = len(satIDs)
    obs_truth_data = obs_truth_data[obs_truth_data["satNo"].isin(satIDs)]

    # Obtain mass and cross-sectional area from Discosweb
    params = "in(satno,(" + ",".join(map(str, satIDs)) + "))"
    resp = discoswebQuery(ESA_token, params)

    # Only interested in mass and area
    keys = ["satno", "mass", "xSectAvg"]
    supp_data = pd.DataFrame([{k: d.get(k) for k in keys} for d in resp["attributes"]])
    # Rename columns for consistency with state_truth_data
    supp_data = supp_data.rename(columns={"satno": "satNo", "xSectAvg": "crossSection"})
    # Fill any missing values with 0
    supp_data = supp_data.fillna(0)
    # Merge into main dataset, ensuring no info is lost
    state_truth_data = pd.merge(state_truth_data, supp_data, on="satNo", how="left")
    state_truth_data = state_truth_data.fillna({"mass": 0, "crossSection": 0})

    # Compute elapsed time for state vector query step
    sv_elapsed_time = time.perf_counter() - obs_elapsed_time - start_time

    # Grab TLE data. Assumes that you can get it if a state vector exists
    # Use "current" call if allowed, else grab individuals
    if end_time == "now":
        elset_truth_data = UDLQuery(
            UDL_token,
            "elset/current",
            {
                "satNo": ",".join(map(str, satIDs)),
            },
        )
    else:
        params_list = [
            {
                "satNo": str(ID),
                "epoch": sweep_time,
                "uct": "false",
                "dataMode": "REAL",
                "sort": "epoch,DESC",
                "maxResults": 1,
            }
            for ID in satIDs
        ]
        elset_truth_data = asyncUDLBatchQuery(UDL_token, "elset", params_list, dt)

    # If a satellite has no TLE data, drop it from list, state vectors, and obs
    satIDs = elset_truth_data["satNo"].unique()
    elset_sats = len(satIDs)
    obs_truth_data = obs_truth_data[obs_truth_data["satNo"].isin(satIDs)]
    state_truth_data = state_truth_data[state_truth_data["satNo"].isin(satIDs)]

    # Parse TLEs into usable orbital elements
    elset_truth_data["elset"] = elset_truth_data.apply(
        lambda row: parseTLE(row["line1"], row["line2"]), axis=1
    )

    # Compute elapsed time for TLE query step
    elset_elapsed_time = time.perf_counter() - sv_elapsed_time - obs_elapsed_time - start_time

    # Generate final dataset from observation data
    dataset = obs_truth_data.copy()
    dataset["uct"] = True  # Mark these as UCT/"unknown" points

    # Remove metadata columns that might identify data (silently ignore if any are missing)
    dataset = dataset.drop(
        columns=[
            "satNo",
            "idOnOrbit",
            "origObjectId",
            "rawFileURI",
            "createdAt",
            "trackId",
            "has_cov",
        ],
        errors="ignore",
    )

    # Create artificial track bins
    binned, _ = binTracks(obs_truth_data, state_truth_data)
    id_to_track = {}

    for track_idx, (_, _, df) in enumerate(binned):
        # Get all ids from this dataframe
        ids_in_track = df["id"].values
        # Map each id to the current track index
        id_to_track.update({id_: track_idx for id_ in ids_in_track})

    dataset["trackId"] = dataset["id"].map(id_to_track)
    dataset["origObjectId"] = dataset["id"].map(id_to_track)

    # Shuffle the dataset for good measure
    dataset = dataset.sample(frac=1).reset_index(drop=True)

    # Compute total elapsed time
    total_elapsed_time = time.perf_counter() - start_time

    # Collect and return all performance outputs
    performance_data = {
        "Observation Collection Time": obs_elapsed_time,
        "State Vector Collection Time": sv_elapsed_time,
        "TLE Collection Time": elset_elapsed_time,
        "Total Runtime": total_elapsed_time,
        "Desired Satellite Count": requested_sats,
        "Satellites with Observations": obs_sats,
        "Observed Satellites with SV Information": orbit_sats,
        "Observed Satellites with SV and TLE Information": elset_sats,
    }

    return dataset, obs_truth_data, state_truth_data, elset_truth_data, satIDs, performance_data


def pullStates(UDL_token, satIDs, timeframe, timeunit, dt=0.1, end_time="now"):
    """
    Generates a dataframe of state vectors from UDL data given desired window and satellites.

    Args:
        UDL_token (string): Your UDL Base64 login token. If you don't have one, use UDLTokenGen or the Utilities page of the UDL Help site.
        satIDs (numpy Array): List of satellites you wish to obtain vectors for.
        timeframe (int): Timespan of sweep.
        timeunit (string): Unit of timeframe.
        dt (float): Rate limit for UDL calls in sec. Please check EULA or contact Bluestack before making this very small. Defaults to 0.1.
        end_time (datetime.datetime): Sets the end time of the data timespan. Defaults to 'now' which sets end to current time.

    Returns:
        Pandas DataFrame: State vectors of requested satellites, with covariance.
        Pandas DataFrame: TLEs of requested satellites.
        Array (int): All satellites that were actually obtained.
        Float: Runtime.

    Raises:
        TypeError: If input types are incorrect.
        HTTPError/ClientResponseError: If a query fails.
    """

    # Start timing the entire operation
    start_time = time.perf_counter()

    # Determine the time window for observation data based on the user-specified end_time
    if end_time != "now":
        # Construct a UDL time range string from (end_time - timeframe) to end_time
        sweep_time = (
            datetimeToUDL(end_time - pd.Timedelta(**{timeunit: timeframe}))
            + ".."
            + datetimeToUDL(end_time)
        )
    else:
        # Use relative time if 'now' is specified
        sweep_time = ">now-" + str(timeframe) + " " + timeunit

    # Grabs state vector data
    # Required to do batch call (no access to statevector/current)
    params_list = [
        {
            "satNo": str(ID),
            "epoch": sweep_time,
            "uct": "false",
            "dataMode": "REAL",
            "sort": "epoch,DESC",
        }
        for ID in satIDs
    ]

    sv_data = asyncUDLBatchQuery(UDL_token, "statevector", params_list, dt)

    # Remove duplicate state vectors and prioritize ones with covariance
    if sv_data["satNo"].nunique() < len(sv_data):
        df = sv_data.copy()
        # Create helper column to track presence of covariance
        cov_sources = ["eqCov", "cov"]
        df["has_cov"] = np.any(
            [
                df[col].notna() if col in df.columns else pd.Series(False, index=df.index)
                for col in cov_sources
            ],
            axis=0,
        )

        # Keep only rows with covariance
        df_with_cov = df[df["has_cov"]]

        # If no covariance for a satellite, it will disappear here
        if not df_with_cov.empty:
            # Sort by epoch descending so most recent first
            df_with_cov_sorted = df_with_cov.sort_values(by="epoch", ascending=False)

            # Select the most recent row WITH covariance for each satellite
            sv_data = (
                df_with_cov_sorted.groupby("satNo", group_keys=False)
                .head(1)
                .reset_index(drop=True)
            )
        else:
            # If absolutely no covariance anywhere, result is empty
            sv_data = df_with_cov.copy()

        # Drop the helper column if it still exists
        sv_data = sv_data.reset_index(drop=True)
        sv_data.drop(columns="has_cov", inplace=True, errors="ignore")

    # Convert epoch times to datetime
    sv_data["epoch"] = [UDLToDatetime(t) for t in sv_data["epoch"]]

    # Format drag coeff and solar rad coeff correctly
    cols_to_fill = ["dragCoeff", "solarRadPressCoeff"]
    for col in cols_to_fill:
        if col not in sv_data.columns:
            sv_data[col] = 0
        else:
            sv_data[col] = sv_data[col].fillna(0)

    # Grab TLE data. Assumes that you can get it if a state vector exists
    # Use "current" call if allowed, else grab individuals
    if end_time == "now":
        elset_data = UDLQuery(
            UDL_token,
            "elset/current",
            {
                "satNo": ",".join(map(str, satIDs)),
            },
        )
    else:
        params_list = [
            {
                "satNo": str(ID),
                "epoch": sweep_time,
                "uct": "false",
                "dataMode": "REAL",
                "sort": "epoch,DESC",
                "maxResults": 1,
            }
            for ID in satIDs
        ]
        elset_data = asyncUDLBatchQuery(UDL_token, "elset", params_list, dt)

    # If a satellite has no TLE data, drop it from list, state vectors, and obs
    satIDs = elset_data["satNo"].unique()
    sv_data = sv_data[sv_data["satNo"].isin(satIDs)]

    # Parse TLEs into usable orbital elements
    elset_data["elset"] = elset_data.apply(
        lambda row: parseTLE(row["line1"], row["line2"]), axis=1
    )

    return sv_data, elset_data, sv_data["satNo"].unique(), time.perf_counter() - start_time


def saveDataset(ref_obs, ref_track, ref_sv, ref_elset, output_path):
    """
    Saves obtained data to a json file in the format:
        output_json: {
            'dataset_obs': Dataframe
            'dataset_elset': Dataframe
            'reference': Dataframe containing:
                groupedObs
                groupedObsIds
                groupedElsets
                groupedElsetIds
            }

    Args:
        ref_obs (Pandas DataFrame): Dataframe of "truth" observations.
        ref_track (Pandas DataFrame): Dataframe of "truth" track TLEs.
        ref_sv (Pandas DataFrame): Dataframe of satellite state vector data.
        ref_elset (Pandas DataFrame): Dataframe of satellite TLE data.
        output_path (string): Relative save path for the file.

    Returns:
        The json data saved.
    """

    # Avoid modifying in place
    ref_obs = ref_obs.copy()
    ref_track = ref_track.copy()

    # convert obTime columns to timestamps if not already
    ref_obs["obTime"] = pd.to_datetime(ref_obs["obTime"])

    # --------------------------------------------------------------------
    # Generate decorrelated obs dataset
    # --------------------------------------------------------------------
    obs_data = ref_obs.copy()
    obs_data["uct"] = True  # Mark these as UCT/"unknown" points

    # Remove metadata columns that might identify data (silently ignore if any are missing)
    obs_data = obs_data.drop(
        columns=[
            "satNo",
            "idOnOrbit",
            "origObjectId",
            "rawFileURI",
            "createdAt",
            "trackId",
            "has_cov",
        ],
        errors="ignore",
    )

    # Create artificial track bins
    binned, _ = binTracks(ref_obs, ref_sv)
    id_to_track = {}

    for track_idx, (_, _, df) in enumerate(binned):
        # Get all ids from this dataframe
        ids_in_track = df["id"].values
        # Map each id to the current track index
        id_to_track.update({id_: track_idx for id_ in ids_in_track})

    obs_data["trackId"] = obs_data["id"].map(id_to_track)
    obs_data["origObjectId"] = obs_data["id"].map(id_to_track)

    # Shuffle the dataset for good measure
    obs_data = obs_data.sample(frac=1).reset_index(drop=True)

    # Serialize decorrelated obs dataset
    obs_data["obTime"] = obs_data["obTime"].astype(str)
    obs_data_json = obs_data.to_dict(orient="records")

    # --------------------------------------------------------------------
    # Generate decorrelated track dataset
    # --------------------------------------------------------------------
    track_data = ref_track.copy()
    track_data["uct"] = True  # Mark these as UCT/"unknown" points

    # Remove metadata columns that might identify data (silently ignore if any are missing)
    track_data = obs_data.drop(
        columns=[
            "satNo",
            "idOnOrbit",
            "origObjectId",
            "rawFileURI",
            "createdAt",
            "trackId",
            "has_cov",
            "epochNormalized",
        ],
        errors="ignore",
    )

    # Shuffle the dataset for good measure
    track_data = track_data.sample(frac=1).reset_index(drop=True)

    # Serialize decorrelated track dataset
    track_data_json = track_data.to_dict(orient="records")

    # --------------------------------------------------------------------
    # Serialize ref obs
    # --------------------------------------------------------------------
    ref_obs["obTime"] = ref_obs["obTime"].astype(str)

    # --------------------------------------------------------------------
    # Set up and serialize orbital data
    # --------------------------------------------------------------------
    cols_sv = [
        "satNo",
        "xpos",
        "ypos",
        "zpos",
        "xvel",
        "yvel",
        "zvel",
        "epoch",
        "cov",
        "mass",
        "crossSection",
        "dragCoeff",
        "solarRadPressCoeff",
    ]
    cols_elset = ["satNo", "line1", "line2"]

    orbit_data = pd.merge(ref_sv[cols_sv], ref_elset[cols_elset], on="satNo")

    obs_ids = ref_obs.groupby("satNo")["id"].agg(list).to_dict()
    elset_ids = ref_track.groupby("satNo")["id"].agg(list).to_dict()
    orbit_data["groupedObsIds"] = orbit_data["satNo"].map(obs_ids)
    orbit_data["groupedElsetIds"] = orbit_data["satNo"].map(elset_ids)

    orbit_data["cov"] = [json.dumps(arr) for arr in orbit_data["cov"].values]

    # orbit_data = safe_serialize_cov_column(orbit_data)

    orbit_data["epoch"] = orbit_data["epoch"].astype(str)

    orbit_data_json = orbit_data.to_dict(orient="records")

    # --------------------------------------------------------------------
    # Create and save output
    # --------------------------------------------------------------------
    output_json = {
        "dataset_obs": obs_data_json,
        "dataset_elset": track_data_json,
        "reference": orbit_data_json,
    }

    obs_data.to_parquet(INTERIM_DATA_DIR / "output_dataset_obs.parquet", index=False)
    track_data.to_parquet(INTERIM_DATA_DIR / "output_dataset_elset.parquet", index=False)
    orbit_data.to_parquet(INTERIM_DATA_DIR / "output_dataset_reference.parquet", index=False)

    output_dataset_path = \
        INTERIM_DATA_DIR / "output_dataset.json"
    with open(str(output_dataset_path), "w") as f:
        json.dump(
            output_json,
            f,
            indent=2,
            default=lambda o: o.isoformat() if isinstance(o, pd.Timestamp) else str(o),
        )

    return output_json


def loadDataset(input_path):
    """
    Loads dataset JSON into its original DataFrame components.

    Args:
        input_path (string): Path to JSON file.

    Returns:
        ref_obs (Pandas DataFrame): Dataframe of "truth" observations.
        obs_data (Pandas DataFrame): Dataframe of decorrelated observations.
        ref_track (Pandas DataFrame): Dataframe of "truth" track TLEs.
        track_data (Pandas DataFrame): Dataframe of decorrelated track TLEs.
        ref_sv (Pandas DataFrame): Dataframe of satellite state vector data.
        ref_elset (Pandas DataFrame): Dataframe of satellite TLE data.
    """
    with open(input_path, "r") as f:
        data = json.load(f)

    # Reconstruct obs_data
    obs_data = pd.DataFrame(data["dataset_obs"])
    obs_data["obTime"] = pd.to_datetime(obs_data["obTime"])

    # Reconstruct track_data
    track_data = pd.DataFrame(data["dataset_elset"])

    # Reconstruct ref_obs from 'reference' field
    reference = pd.DataFrame(data["reference"])

    # Reconstruct ref_obs and ref_tracks by correlating groupedObsIds and groupedElsetIds
    obs_id_to_satno = {}
    elset_id_to_satno = {}
    for entry in data["reference"]:
        sat_no = entry["satNo"]
        for obs_id in entry["groupedObsIds"]:
            obs_id_to_satno[obs_id] = sat_no
        for elset_id in entry["groupedElsetIds"]:
            elset_id_to_satno[elset_id] = sat_no

    ref_obs = obs_data[obs_data["id"].isin(obs_id_to_satno)].copy()
    ref_obs["satNo"] = ref_obs["id"].map(obs_id_to_satno)

    ref_track = track_data[track_data["id"].isin(elset_id_to_satno)].copy()
    ref_track["satNo"] = ref_track["id"].map(elset_id_to_satno)

    # Reconstruct ref_sv
    ref_sv = reference[
        [
            "satNo",
            "xpos",
            "ypos",
            "zpos",
            "xvel",
            "yvel",
            "zvel",
            "epoch",
            "cov_matrix",
            "mass",
            "crossSection",
            "dragCoeff",
            "solarRadPressCoeff",
        ]
    ].copy()
    ref_sv["epoch"] = pd.to_datetime(ref_sv["epoch"])
    ref_sv["cov_matrix"] = ref_sv["cov_matrix"].apply(lambda x: np.array(json.loads(x)))

    # Reconstruct ref_elset
    ref_elset = reference[["satNo", "line1", "line2"]].copy()

    return ref_obs, obs_data, ref_track, track_data, ref_sv, ref_elset
