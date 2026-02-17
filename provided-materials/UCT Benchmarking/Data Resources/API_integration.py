# -*- coding: utf-8 -*-
"""
Created on Fri Jun  6 08:51:11 2025

@author: Gabriel Lundin
"""

import requests, base64, warnings, pandas as pd, re, datetime, asyncio, aiohttp, time, numpy as np

# Because HTTPS is annoying
def _supress_warn():
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def UDL_token_gen(username,password):
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
        raise TypeError(f"Username and password must be strings, got types {type(username).__name__} and {type(password).__name__} instead.")
    return base64.b64encode((username+":"+password).encode('utf-8')).decode("ascii")

def spacetrack_token_gen(username,password):
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
        raise TypeError(f"Username and password must be strings, got types {type(username).__name__} and {type(password).__name__} instead.")
    return {'identity': username, 'password': password}


def UDL_query(token, service, params, count=False, history=False):
    """
    Performs a UDL search using the given parameters.

    Args:
        token (string): Your UDL Base64 login token. If you don't have one, use UDL_token_gen or the Utilities page of the UDL Help site.
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
    
    _supress_warn()
    
    if not (isinstance(token,str) and isinstance(service,str) and isinstance(params,dict) and isinstance(count,bool) and isinstance(history,bool)):
        raise TypeError(f"Expected (string, string, dict, bool, bool), got ({type(token).__name__}, {type(service).__name__}, {type(params).__name__}, {type(count).__name__}, {type(history).__name__}) instead.")
    
    basicAuth = "Basic " + token

    url = "https://unifieddatalibrary.com/udl/" + service.lower()
    if history:
        url = url + "/history"
    if count:
        url = url + "/count"
    
    resp = requests.get(url, 
                          headers={'Authorization':basicAuth}, 
                          params=params,
                          verify=False)
    
    if resp.status_code != 200:
        raise requests.exceptions.HTTPError(resp, "Query failed; double-check login info, service, and parameters.")
    
    if not count:
        return pd.DataFrame(resp.json())
    else:
        return resp.json()
    
def parse_TLE(line1, line2):
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
            'ephemeris_type': int,
            'elset_num': int
            'inclination': float
            'RAAN': float
            'eccentricity': float
            'perigee': float
            'mean_anomaly': float
            'mean_motion': float
            'rev_num': int

    Raises:
        TypeError: If inputs are not strings.
    """
    
    if not all(isinstance(var, str) for var in [line1, line2]):
        raise TypeError(f"TLE lines must be strings, got types {type(line1).__name__} and {type(line2).__name__} instead.")
    
    TLE = line1 + " " + line2
    lines = TLE.split()

    elset = {
        'NORAD_ID': int(lines[1][0:-1]),
        'classification': lines[1][-1],
        'COSPAR_ID': lines[2],
        'BC': float(re.sub(r'([+-]\d+)([+-]\d+)', r'\1e\2', lines[5])),
        'n_ddot': float(re.sub(r'([+-]\d+)([+-]\d+)', r'\1e\2', lines[5])),
        'B_star': float(re.sub(r'([+-]\d+)([+-]\d+)', r'\1e\2', lines[6])),
        'ephemeris_type': int(lines[7]),
        'elset_num': int(lines[8][0:-1]),
        'inclination': float(lines[11]),
        'RAAN': float(lines[12]),
        'eccentricity': float(lines[13])/(10**7),
        'perigee': float(lines[14]),
        'mean_anomaly': float(lines[15]),
        'mean_motion': float(lines[16][0:11]),
        'rev_num': int(lines[16][11:-1])
        }

    year = int(lines[3][0:2])
    if year > 56:
        year += 1900
    else:
        year += 2000

    elset['epoch'] = datetime.datetime(year, 1, 1) + datetime.timedelta(days=float(lines[3][2:]) - 1)
    
    return elset

def spacetrack_query(token, params, request="satcat", controller='basicspacedata'):
    """
    Performs a Space-Track search using the given parameters.

    Args:
        token (dict): Your Space-Track login token. If you don't have one, use spacetrack_token_gen.
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
    
    _supress_warn()
    
    if not (isinstance(token,dict) and isinstance(controller,str) and isinstance(params,dict) and isinstance(request,str)):
        raise TypeError(f"Expected (dict, dict, string, string), got ({type(token).__name__}, {type(params).__name__}, {type(request).__name__}, {type(controller).__name__}) instead.")
    
    uriBase = "https://www.space-track.org"
    requestLogin = "/ajaxauth/login"
    requestCmdAction = "/" + controller + "/query" 
    requestFind = "/class/" + request
    requestFind.join(f"/{k.upper()}/{v}" for k, v in params.items())
    
    if any(k.lower() == "format" for k in params):
        params = {k: v for k,v in params.items() if k.lower() != "format"}

    with requests.Session() as session:
        resp = session.post(uriBase + requestLogin, data = token)
        if resp.status_code != 200:
            raise requests.exceptions.HTTPError(resp, "Login failed; double-check login info.")
        
        resp = session.get(uriBase + requestCmdAction + requestFind)
        if resp.status_code != 200:
            if resp.status_code == 500:
                raise requests.exceptions.HTTPError(resp, "Query failed due to throttle limit (500); please slow down!")
            if resp.status_code == 401:
                raise requests.exceptions.HTTPError(resp, "Query failed due to bad credentials (401).")
            else:
                raise requests.exceptions.HTTPError(resp, "Query failed for unknown reason (" + str(resp.status_code) + "); double-check search parameters.")
        
        session.close()
    return pd.DataFrame(resp.json())

def discosweb_query(token, params, data='objects', version=2):
    """
    Performs an ESA Discosweb search using the given parameters.

    Args:
        token (string): Your ESA Discosweb access token. If you don't have one, generate one at https://discosweb.esoc.esa.int/tokens.
        params (dict): A dictionary of search parameters in the form {'parameter': 'value'}. Please read https://discosweb.esoc.esa.int/apidocs/v2 for formatting.
        data (string): The requested data type from Discosweb. Defaults to "objects".
        version (int): The requested Discosweb API version. Defaults to version 2.

    Returns:
        Pandas DataFrame: The results of your query.

    Raises:
        TypeError: If input types are incorrect.
        HTTPError: If login or query fails.
    """
    
    if not (isinstance(token,str) and isinstance(data,str) and isinstance(params,dict) and isinstance(version,int)):
        raise TypeError(f"Expected (string, dict, string, int), got ({type(token).__name__}, {type(params).__name__}, {type(data).__name__}, {type(version).__name__}) instead.")
    
    URL = 'https://discosweb.esoc.esa.int'
    
    auth = {'Authorization': f'Bearer {token}', 'DiscosWeb-Api-Version':  str(version)}
    
    if any(k.lower() == "format" for k in params):
        params = {k: v for k,v in params.items() if k.lower() != "format"}
    
    resp = requests.get(
        f'{URL}/api/{data}',
        headers=auth,
        params=params,
        )
    
    if resp.status_code != 200:
        if resp.status_code == 429:
            raise requests.exceptions.HTTPError(resp, "Query failed due to API rate limit (429). Slow down!")
        else:
            raise requests.exceptions.HTTPError(resp, "Query failed for unknown reason ("+resp.status_code+"); double-check login info and query parameters.")
    return pd.DataFrame(resp.json()["data"])

def celestrak_satcat():
    """
    Grabs the entire CelesTrak satcat. Probably very slow.

    Returns:
        Pandas DataFrame: The sat cat.
    """
    
    URL = 'https://celestrak.org/pub/satcat.csv'
    
    return pd.read_csv(URL)

def celestrak_query(params, table='gp'):
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
    
    if not (isinstance(params,dict) and isinstance(table,str)):
        raise TypeError(f"Expected (dict, string), got ({type(params).__name__}, {type(table).__name__}) instead.")
    
    if table.lower() == "satcat":
        URL = 'https://celestrak.org/satcat/records.php'
    else:
        URL = "https://celestrak.org/NORAD/elements/"+table.lower()+".php"
    
    params = {k.upper(): v for k,v in params.items() if k.upper() != "FORMAT"}
    
    params["FORMAT"] = "JSON"
    
    resp = requests.get(
        URL,
        params=params,
        )
    
    if resp.status_code != 200:
        raise requests.exceptions.HTTPError(resp, "Query failed for unknown reason ("+resp.status_code+"); double-check query parameters.")
    return pd.DataFrame(resp.json())



def datetime_to_UDL(time,micro=6):
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
    
    if not isinstance(micro,int):
        raise TypeError(f"Expected micro to  be an int, got {type(micro).__name__}) instead.")
    
    micro = max(micro,6)
        
    return time.strftime("%Y-%m-%dT%H:%M:%S.") + str(time.microsecond)[0:micro] + "Z"
    
def UDL_to_datetime(time):
    """
    Converts a UDL formatted timestamp to a datetime object.

    Args:
        time (string): Timestamp you wish to convert.

    Returns:
        datetime.datetime: Datetime object.

    Raises:
        TypeError: If input types are incorrect.
    """
        
    return datetime.datetime.strptime(time,"%Y-%m-%dT%H:%M:%S.%fZ")
    
'''
def run_parallel_UDL_queries(token, service, params_list, dt):
    """
    Performs an async batch of UDL searchs using the given parameters. 
    Does not support History API calls or count calls.

    Args:
        token (string): Your UDL Base64 login token. If you don't have one, use UDL_token_gen or the Utilities page of the UDL Help site.
        service (string): The service requested from UDL.
        params_list (list): A list of params sent into UDL_query. Read that documentation for more information.
        dt (float): Rate limit for UDL calls in seconds.

    Returns:
        Pandas DataFrame: The results of your queries concated

    Raises:
        TypeError: If input types are incorrect.
        HTTPError: If a query fails.
    """

    coro = _async_batch_query(token, service, params_list, dt)
    
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop and loop.is_running():
        if inspect.iscoroutinefunction(run_parallel_UDL_queries):
            return coro
        else:
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)

async def _async_batch_query(token, service, params_list, dt) -> pd.DataFrame:
    rate_lock = asyncio.Lock()
    tasks = [_call_with_rate_limit(token, service, p, dt, rate_lock) for p in params_list]
    results = await asyncio.gather(*tasks)
    return pd.concat(results, ignore_index=True)

async def _call_with_rate_limit(token, service, params, dt, rate_lock):
    async with rate_lock:
        start = time.time()
        df = await asyncio.to_thread(UDL_query, token, service, params)
        elapsed = time.time() - start
        await asyncio.sleep(max(0, dt - elapsed))  # Ensure dt between call *starts*
        return df
'''

async def _async_UDL_query(token, service, params, count=False, history=False):
    """
    Async version of UDL_query using aiohttp.
    """
    if not (isinstance(token, str) and isinstance(service, str) and
            isinstance(params, dict) and isinstance(count, bool) and isinstance(history, bool)):
        raise TypeError(f"Expected (string, string, dict, bool, bool), got "
                        f"({type(token).__name__}, {type(service).__name__}, "
                        f"{type(params).__name__}, {type(count).__name__}, {type(history).__name__})")

    base_url = "https://unifieddatalibrary.com/udl/"
    url = base_url + service.lower()
    if history:
        url += "/history"
    if count:
        url += "/count"

    headers = {"Authorization": "Basic " + token}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params, ssl=False) as response:
            if response.status != 200:
                raise aiohttp.ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message="Query failed; double-check login info, service, and parameters."
                )
            data = await response.json()
            return data if count else pd.DataFrame(data)

async def _batch_UDL_query(token, service, params_list, dt=1.0, count=False, history=False):
    """
    Internal wrapper for multiple _async_UDL_query() calls
    """
    results = []

    async def limited_query(index, params):
        await asyncio.sleep(index * dt)
        return await _async_UDL_query(token, service, params, count, history)

    tasks = [limited_query(i, p) for i, p in enumerate(params_list)]
    results = await asyncio.gather(*tasks)

    return sum(results) if count else pd.concat(results, ignore_index=True)

def async_UDL_batch_query(token, service, params_list, dt=0.1, count=False, history=False):
    """
    Performs an async batch of UDL searchs using the given parameters. 

    Args:
        token (string): Your UDL Base64 login token. If you don't have one, use UDL_token_gen or the Utilities page of the UDL Help site.
        service (string): The service requested from UDL.
        params_list (list): A list of params sent into UDL_query. Read that documentation for more information.
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
    try:
        return asyncio.run(_batch_UDL_query(token,service,params_list,dt,count,history))
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.get_event_loop().run_until_complete(
                _batch_UDL_query(token,service,params_list,dt,count,history)
            )
        else:
            raise

def generate_dataset(token, satIDs,timeframe,timeunit,dt=0.1,max_datapoints=0,endTime='now',elsetMode=False):
    """
    Generates a benchmark  dataset given satellites and various parameters.
    TODO: ENABLE DATA MANIPULATION
    
    Args:
        token (string): Your UDL Base64 login token. If you don't have one, use UDL_token_gen or the Utilities page of the UDL Help site.
        satIDs (numpy Array): List of satellites you wish to pull obs from.
        timeframe (int): Timespan of sweep.
        timeunit (string): Unit of timeframe.
        dt (float): Rate limit for UDL calls in sec. Please check EULA or contact Bluestack before making this very small. Defaults to 0.1.
        max_datapoints (int): If > 0, limit of obs data return per satellite, returning newest obs. Defaults to 0 (disabled), max 10000.
        endTime (datetime.datetime): Sets the end time of the data timespan. Defaults to 'now' which sets end to current time.
        elsetMode (bool): If True, returns elsets on orbitTruthData. Else, returns state vectors. Defaults to False.
        
    Returns:
        Pandas DataFrame: A dataset of "uct" observations.
        Pandas DataFrame: The truth observations, matched using "id" field. 
        Pandas DataFrame: The truth orbits of requested satellites.
        Array (int): All satellites that were actually obtained.
        Dict: Various runtime data.
        
    Raises:
        TypeError: If input types are incorrect.
        ClientResponseError: If a query fails.
    """

    start_time = time.perf_counter()
    
    if endTime != 'now':
        sweep_time = datetime_to_UDL(endTime-pd.Timedelta(**{timeunit: timeframe})) + '..' + datetime_to_UDL(endTime)
    else:
        sweep_time = '>now-' + str(timeframe) + ' ' + timeunit

    params_list = [{
        "satNo": str(ID),
        "obTime": sweep_time,
        "uct": "false",
        "dataMode": "REAL",
        "maxResults": max_datapoints
        } for ID in satIDs]
    if max_datapoints <= 0:
        params_list = [{k: v for k, v in d.items() if k != "maxResults"} for d in params_list]

    obsTruthData = async_UDL_batch_query(token, "eoobservation", params_list, dt)

    obsTruthData["obTime"] = [UDL_to_datetime(t) for t in obsTruthData["obTime"]]

    # Cull sat IDs to ones we got data for
    satIDs = obsTruthData["satNo"].unique()

    obs_elapsed_time = time.perf_counter() - start_time

    if elsetMode:
        orbitTruthData = UDL_query(token, "elset/current", {
            "satNo": ",".join(map(str, satIDs)),
            })
        orbitTruthData["elset"] = orbitTruthData.apply(lambda row: parse_TLE(row['line1'], row['line2']), axis=1)
    else:
        if dt > 0.05*timeframe:
            # Pull state vector data
            orbitTruthData = UDL_query(token, "statevector", {
                "satNo": ",".join(map(str, satIDs)),
                "epoch": '>now-' + str(timeframe) + ' ' + timeunit,
                "uct": "false",
                "dataMode": "REAL",
                "sort": "epoch,DESC",
                })
        
            # Cull to most recent sate vector
            orbitTruthData = orbitTruthData.drop_duplicates(subset='satNo', keep='first')
        
            # Check and backfill missing satellites as needed
            missingIDs = np.setdiff1d(satIDs, orbitTruthData["satNo"].unique())
            expanded_time = timeframe*2
            while len(missingIDs) != 0:
                if endTime !='now':
                    ex_sweep_time = datetime_to_UDL(endTime-pd.Timedelta(**{timeunit: expanded_time})) + '..' + datetime_to_UDL(endTime)
                else:
                    ex_sweep_time = '>now-' + str(expanded_time) + ' ' + timeunit
                vector = UDL_query(token, "statevector", {
                    "satNo": ",".join(map(str, missingIDs)),
                    "epoch": ex_sweep_time,
                    "uct": "false",
                    "dataMode": "REAL",
                    "sort": "epoch,DESC",
                    })
                vector = vector.drop_duplicates(subset='satNo', keep='first')
                
                orbitTruthData = pd.concat([orbitTruthData,vector])
                missingIDs = np.setdiff1d(satIDs, orbitTruthData["satNo"].unique())

                expanded_time += timeframe
        else:
            params_list = [{
                "satNo": str(ID),
                "epoch": '<now',
                "uct": "false",
                "dataMode": "REAL",
                "maxResults": 1,
                "sort": "epoch,DESC",
                } for ID in satIDs]
        
            orbitTruthData = async_UDL_batch_query(token, "statevector", params_list, dt)
            
        orbitTruthData["epoch"] = [UDL_to_datetime(t) for t in orbitTruthData["epoch"]]
        orbit_elapsed_time = time.perf_counter() - obs_elapsed_time - start_time
            
    # Generate dataset using truth data
    dataset = obsTruthData.copy()
    dataset["uct"] = True
    dataset = dataset.drop(columns=['satNo', 'idOnOrbit',"origObjectId", "rawFileURI", "createdAt", "trackId"])
    dataset = dataset.sample(frac=1).reset_index(drop=True) # For good measure

    # Return datasets
    total_elapsed_time = time.perf_counter() - start_time

    time_elapsed = {"obs": obs_elapsed_time,"orbit": orbit_elapsed_time,"total": total_elapsed_time}
    
    return dataset, obsTruthData, orbitTruthData, satIDs, time_elapsed




































