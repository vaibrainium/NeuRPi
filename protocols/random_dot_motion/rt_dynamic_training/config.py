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

# SUBJECT["rolling_perf"]: {
#     "window": 50,
#     "current_coherence_level": 2,
#     "trials_in_current_level": 0,
#     "total_attempts": 0,
#     "total_reward": 0,
#     "reward_volume": 3,
#     "index": list(
#         np.zeros(len(TASK["stimulus"]["signed_coherences"]["value"])).astype(int)
#     ),
#     "accuracy": list(
#         np.zeros(len(TASK["stimulus"]["signed_coherences"]["value"])).astype(int)
#     ),
#     "outcome_history": {},
# }

# for coh in TASK["stimulus"]["signed_coherences"]["value"]:
#     SUBJECT["rolling_perf"]["outcome_history"][coh] = np.zeros(
#         SUBJECT["rolling_perf"]["window"]
#     )

TASK["epochs"]["stimulus"]["passive_viewing"] = lambda coh_level: pearson3.rvs(
    skew=0.6, loc=(coh_level - 1) * 10, scale=1.5, size=1
)[0]

TASK["epochs"]["reinforcement"] = (
    {
        "tag": "Reinforcement epoch. Returns delay in stimulus display and delay screen duration (usually white).",
        "durations": {
            "correct": lambda response_time: {
                "duration": 0.300,
                "delay": 0.000,
            },
            "incorrect": lambda response_time: {
                "duration": 1.000,
                "delay": 25 * (np.exp(-4 * response_time)),
            },
            "invalid": lambda response_time: {
                "duration": 1.000,
                "delay": 25 * (np.exp(-4 * response_time)),
            },
        },
    },
)

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
        },
    },
    "accuracy": {
        "rolling_widows": {
            "tag": "Number of trials per coherence to consider for accuracy calculation",
            "value": 50,
        },
        "thresholds": {
            "tag": "List of all accuracy conditions for each coherence level to move forward (or backward)",
            "value": {
                1: np.array([0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7]),
                2: np.array([0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7]),
                3: np.array([0.7, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7, 0.7]),
                4: np.array([0.7, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7, 0.7]),
                5: np.array([0.7, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7, 0.7]),
                6: np.array([0.7, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7, 0.7]),
            },
        },
    },
    "trials_threshold": {
        "tag": "Number of trials required to move forward (or backward) for each coherence level",
        "value": {
            1: 0,
            2: 0,
            3: 0,
            4: 200,
            5: 200,
            6: 200,
        },
    },
}


def grad_check(current_level, accuracy, level_change_trial_counter):
    graduation_direction = GRADUATION["direction"]["value"]
    accuracy_thesholds = GRADUATION["accuracy"]["thresholds"]["value"]
    trials_threshold = GRADUATION["trials_threshold"]["value"]

    next_coherence_level = current_level
    new_trial_counter = level_change_trial_counter + 1

    # forward graduation
    while next_coherence_level < 5:
        if all(accuracy >= accuracy_thesholds[next_coherence_level]) and (
            new_trial_counter >= trials_threshold[next_coherence_level]
        ):
            next_coherence_level = next_coherence_level + 1
            new_trial_counter = 0
        else:
            break

    # backward graduation
    if graduation_direction == 0:
        while next_coherence_level > 1:
            if any(accuracy < accuracy_thesholds[next_coherence_level - 1]):
                next_coherence_level = next_coherence_level - 1
                new_trial_counter = 0
            else:
                break

    print(f"Coherence level changed from {current_level} to {next_coherence_level}")
    print(f"Trial counter: {level_change_trial_counter} to {new_trial_counter}")
    return next_coherence_level


if __name__ == "__main__":
    GRADUATION["direction"]["value"] = 0
    accuracy = np.array([0.7, 0.2, 0.7, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7, 0.7])
    current_level = 5
    level_change_trial_counter = 1
    current_level = grad_check(current_level, accuracy, level_change_trial_counter)
    level_change_trial_counter = 201
    current_level = grad_check(current_level, accuracy, level_change_trial_counter)
