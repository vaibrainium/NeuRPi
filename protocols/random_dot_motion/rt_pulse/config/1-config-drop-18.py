"""
Refactored RT Pulse configuration (drop-18 variant) using base template.

This eliminates ~150 lines of repetitive configuration code.
"""

import numpy as np
from scipy import stats

from protocols.random_dot_motion.core.config.base_config import BaseRDMConfig

# Get base configurations
TASK = BaseRDMConfig.get_base_task_config()
STIMULUS = BaseRDMConfig.get_base_stimulus_display_config()
DATAFILES = BaseRDMConfig.get_data_files()
# RT Pulse Drop-18 specific customizations
TASK.update(
    {
        "epochs": {
            "tag": "List of all epochs and their respective parameters in secs",
            "fixation": {
                "tag": "Fixation epoch",
                "duration": lambda: stats.gamma.rvs(a=1.6, loc=0.5, scale=0.04),
            },
            "stimulus": {
                "tag": "Stimulus epoch",
                "max_viewing": 25,
                "min_viewing": 0,
            },
            "reinforcement": {
                "tag": "Reinforcement epoch",
                "duration": {
                    "correct": lambda response_time: 0,
                    "incorrect": lambda response_time: 0,
                    "noresponse": lambda response_time: 0,
                    "invalid": lambda response_time: 0,
                },
            },
            "intertrial": {
                "tag": "Intertrial epoch",
                "duration": {
                    "correct": lambda response_time, coh: stats.expon.rvs(loc=0.25, scale=0.075),
                    "incorrect": lambda response_time, coh: 3 + 4 * (np.exp(-3 * response_time)),
                    "noresponse": lambda response_time, coh: 7,
                    "invalid": lambda response_time, coh: 7,
                },
            },
        },
        "stimulus": {
            "coherences": {
                "tag": "List of all coherences used in study",
                "type": "list",
                "value": np.array([100, 72, 36, 18, 9, 0]),
            },
            "signed_coherences": {
                "tag": "List of all signed coherences",
                "type": "list",
                "value": np.array([-100, -36, -18, -9, 0, 9, 18, 36, 100]),
            },
            "repeats_per_block": {
                "tag": "Number of repeats of each coherences per block",
                "type": "int",
                "value": 3,
            },
            # Drop-18 specific pulse probabilities
            "pulse_probabilities": {
                "tag": "Probability of pulse at each coherence (drop-18 variant)",
                "type": "dict",
                "value": {
                    -100: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                    -36: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                    -18: [
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.3,
                        0.3,
                        0.000,
                        0.000,
                        0.40,
                    ],  # Drop at 18
                    -9: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                    0: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                    9: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                    18: [
                        0.0,
                        0.0,
                        0.0,
                        0.0,
                        0.3,
                        0.3,
                        0.000,
                        0.000,
                        0.40,
                    ],  # Drop at 18
                    36: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                    100: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                },
            },
            "pulse_duration": {
                "tag": "Duration of pulse in #frames (1/60s)",
                "type": "int",
                "value": 4,
            },
            "pulse_onset": {
                "tag": "Onset of pulse in #frames (1/60s)",
                "type": "dict",
                "value": {
                    "early": 3,
                    "middle": 14,
                    "late": 25,
                },
            },
        },
        "bias_correction": {
            "repeat_threshold": {
                "active": 100,
                "passive": 100,
            },
            "bias_window": 10,
        },
        "training_type": {
            "tag": "Training type: 0: passive-only, 1: active-passive, 2: active-only",
            "value": 2,
        },
    }
)

# Hardware requirements
REQUIRED_HARDWARE = ["Arduino", "Display"]
REQUIRED_MODULES = ["Task", "Stimulus", "Behavior"]

# Subject configuration (empty as requested)
SUBJECT = {}

# Data files configuration
DATAFILES = {
    "lick": "_lick.csv",
    "trial": "_trial.csv",
}
