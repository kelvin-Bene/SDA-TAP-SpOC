from datetime import datetime

from loguru import logger


def timeSort(t_X, t_obs):
    t_obs_before = []
    t_obs_after = []

    # Check if state epoch falls inbetween obs epochs (obs already in chronological order)
    if t_X < t_obs[-1] and t_X > t_obs[0]:
        # Split obs list at the state epoch
        # Split the list
        t_obs_before = [t_ob for t_ob in t_obs if t_ob < t_X]
        t_obs_after = [t_ob for t_ob in t_obs if t_ob >= t_X]

    return t_obs_before, t_obs_after


if __name__ == "__main__":
    # Example datetime list (must already be sorted chronologically)
    dt_list = [
        datetime(2025, 1, 1),
        datetime(2025, 3, 1),
        datetime(2025, 5, 1),
        datetime(2025, 7, 1),
    ]

    # Cutoff datetime
    cutoff = datetime(2025, 4, 1)

    t_obs_before, t_obs_after = timeSort(cutoff, dt_list)

    logger.debug("Before: %s" % t_obs_before)
    logger.debug("After: %s" % t_obs_after)
