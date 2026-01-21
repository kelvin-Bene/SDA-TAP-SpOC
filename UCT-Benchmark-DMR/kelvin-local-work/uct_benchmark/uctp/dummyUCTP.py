from datetime import datetime
import json
import random

import numpy as np
import pandas as pd
import urllib3

urllib3.disable_warnings()


def dummy(truth_data_filename, blind_data_filename):
    # parse dataset and truthobs csv
    truth_obs = pd.read_csv(truth_data_filename)
    # blindObs = pd.read_csv(blind_data_filename) # don't need this unless we improve the dummy
    # print(inputData.head())
    # print(blindObs.head())

    satList = truth_obs.satNo.unique()
    obsSatDF = truth_obs[truth_obs["satNo"].isin(satList)]

    # index_key = {value: idx for idx, value in enumerate(satList)}  # Unused variable

    fake_obs_corrs = pd.DataFrame({"id": obsSatDF["id"].values})

    # Generate random probabilities
    random_vals = np.random.random(
        len(fake_obs_corrs)
    )  # generates list of random of len fake_obs_corrs

    # conditions
    conditions = [
        (random_vals >= 0) & (random_vals < 0.6),  # 0.0 to 0.6
        (random_vals >= 0.6) & (random_vals < 0.7),  # 0.6 to 0.7
        (random_vals >= 0.7) & (random_vals <= 1.0),  # 0.7 to 1.0
    ]

    # Define corresponding choices
    choices = [
        obsSatDF["satNo"].values,  # True Positive
        np.zeros(len(fake_obs_corrs)).astype(int),  # False Negative
        np.random.choice(satList),  # False Positive (another sat)
    ]

    fake_obs_corrs["pred"] = np.select(conditions, choices)

    fake_obs_corrs["real"] = obsSatDF["satNo"].values

    prunedCorrs = fake_obs_corrs[fake_obs_corrs["pred"] != 0]  # Remove False Negatives

    grouped_obs = prunedCorrs.groupby("pred")["id"].apply(list)

    # write to dummy_output.json
    with open("./data/uctp_output.json", "w") as json_out:
        to_json = []
        for i in range(len(grouped_obs)):
            # Constants
            earth_radius_km = 6371
            altitude_km = 1000
            mu = 3.986004418e14  # Earth's gravitational parameter, m^3/s^2
            radius_km = earth_radius_km + altitude_km
            radius_m = radius_km * 1e3

            # Generate random unit vector for position
            pos_dir = np.random.randn(3)
            pos_dir /= np.linalg.norm(pos_dir)
            position = pos_dir * radius_m  # Position in meters

            # Velocity: perpendicular to position, magnitude for circular orbit
            speed = np.sqrt(mu / radius_m)

            # Generate random perpendicular unit vector
            vel_dir = np.random.randn(3)
            vel_dir -= vel_dir.dot(pos_dir) * pos_dir  # Make orthogonal to position
            vel_dir /= np.linalg.norm(vel_dir)
            velocity = vel_dir * speed

            # Simulate a realistic covariance: small position/velocity noise
            cov = [
                random.uniform(-1000, 1000),  # position covariance (m)
                random.uniform(-1000, 1000),
                random.uniform(-1000, 1000),
                random.uniform(-10, 10),  # velocity covariance (m/s)
                random.uniform(-10, 10),
                random.uniform(-10, 10),
            ] + [random.uniform(-1, 1) for _ in range(15)]
            to_json.append(
                {
                    "idStateVector": i,
                    "sourcedData": grouped_obs.iloc[i],
                    "sourcedDataTypes:": ["EO"] * len(grouped_obs.iloc[i]),
                    "classificationMarking": "?? U//PR-LSAS-SV",
                    "epoch": datetime.now().isoformat(),
                    "uct": True,
                    "xpos": position[0] / 1000,
                    "ypos": position[1] / 1000,
                    "zpos": position[2] / 1000,
                    "xvel": velocity[0] / 1000,
                    "yvel": velocity[1] / 1000,
                    "zvel": velocity[2] / 1000,
                    "referenceFrame": "J2000",
                    "covReferenceFrame": "J2000",
                    "cov": [float(x) for x in cov],
                    "lunarSolar": True,
                    "solarRadPress": True,
                    "solidEarthTides": True,
                    "inTrackThrust": False,
                    "rms": random.uniform(0, 10),
                    "source": "FAKE",
                    "dataMode": "TRASH",
                    "algorithm": "NA",
                }
            )
        json.dump(to_json, json_out, indent=4)
