import datetime as dt
import itertools as it

import pandas as pd

import uct_benchmark.api.apiIntegration as UDL


def batchPull(code, start_epoch, end_epoch, UDL_token):
    """
    code must be DatasetCode object class

    start/end epochs UDL date time format

    script pulls large amounts of data from udl rest api
    """

    start_time = UDL.UDL_to_datetime(start_epoch)
    end_time = UDL.UDL_to_datetime(end_epoch)
    batchsize = end_time - start_time

    # return the sensor types that need pulled to provide obs for this code
    sensor_types = [
        key for key, value_list in code.sensor_superiors.items() if code.SensorType in value_list
    ]
    print(sensor_types)

    # pull regime from code
    if code.Regime in ["LEO", "GEO", "MEO"]:
        regimes = code.Regime
    else:
        component_regimes = it.islice(code.regime_superiors.items, 4)
        regimes = [key for key, value_list in component_regimes if code.Regime in value_list]
    print(regimes)

    # pull time window from code
    time_window = int(code.TimeWindow)
    print(time_window)

    # assemble parameter dict to feed to query function in 10 minute steps
    param_dict = {}
    data_list = list()
    if isinstance(sensor_types, str):
        sensor_types = [sensor_types]
    for sensor_type in sensor_types:
        service = code.sensor_type_queries[sensor_type]
        if isinstance(regimes, str):
            regimes = [regimes]

        for regime in regimes:
            param_dict = {"range": code.regime_ranges[regime], "uct": "false", "dataMode": "REAL"}

            steps = dt.timedelta(minutes=0)
            while steps < batchsize:
                final_dict = param_dict.copy()
                final_dict["obTime"] = (
                    UDL.datetime_to_UDL(start_time + steps)
                    + ".."
                    + UDL.datetime_to_UDL(start_time + dt.timedelta(minutes=10) + steps)
                )
                steps += dt.timedelta(minutes=10)
                data = UDL.UDL_query(UDL_token, service, final_dict)
                if not data.empty:
                    data_list.append(data)
    data_compiled = pd.concat(data_list, ignore_index=True)

    return data_compiled
