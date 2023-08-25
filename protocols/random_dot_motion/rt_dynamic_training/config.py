from pathlib import Path

import numpy as np
from scipy.stats import pearson3

from protocols.random_dot_motion.core.config import config

REQUIRED_HARDWARE = config.REQUIRED_HARDWARE

REQUIRED_MODULES = config.REQUIRED_MODULES

TASK = config.TASK

STIMULUS = config.STIMULUS

DATAFILES = config.DATAFILES

SUBJECT = config.SUBJECT

TASK["epochs"]["stimulus"]["passive_viewing"] = lambda coh_level: pearson3.rvs(
    skew=0.6, loc=(coh_level - 1) * 10, scale=1.5, size=1
)[0]

GRADUATION = {
    "direction": {
        "tag": "Direction of graduation. 0: 'forward' or 1:'forward and backward'",
        "value": 1,
    },
    "coherence_levels": {
        "tag": "List of all coherence levels and their properties used in this phase",
        "value": {
            1: np.array([-100, 100]),
            2: np.array([-100, -72, 72, 100]),
            3: np.array([-100, -72, -36, 36, 72, 100]),
            4: np.array([-100, -72, -36, -18, 18, 36, 72, 100]),
            5: np.array([-100, -72, -36, -18, -9, 9, 18, 36, 72, 100]),
            6: np.array([-100, -72, -36, -18, -9, 0, 9, 18, 36, 72, 100]),
        },
    },
    "accuracy": {
        "rolling_widows": {
            "tag": "Number of trials per coherence to consider for accuracy calculation",
            "value": 50,
        },
        "threadholds": {
            "tag": "List of all accuracy conditions for each coherence level to move forward (or backward)",
            "value": {
                1: np.array([0.7, 0.0, 0.0, 0.0, 0.0, 0.7]),
                2: np.array([0.7, 0.7, 0.0, 0.0, 0.7, 0.7]),
                3: np.array([0.7, 0.7, 0.7, 0.7, 0.7, 0.7]),
                4: np.array([0.7, 0.7, 0.7, 0.7, 0.7, 0.7]),
                5: np.array([0.7, 0.7, 0.7, 0.7, 0.7, 0.7]),
                6: np.array([0.7, 0.7, 0.7, 0.7, 0.7, 0.7]),
            },
        },
    },
    "trial_thresholds": {
        "tag": "Number of trials required to move forward (or backward) for each coherence level",
        "value": {
            1: 200,
            2: 200,
            3: 200,
            4: 200,
            5: 200,
            6: 200,
        },
    },
}
