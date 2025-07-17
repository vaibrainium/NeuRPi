"""
Refactored RT Test configuration using base template.

This eliminates ~140 lines of repetitive configuration code.
"""

import numpy as np
from scipy import stats

from protocols.random_dot_motion.core.config.base_config import BaseRDMConfig

# Get base configurations
TASK = BaseRDMConfig.get_base_task_config()
STIMULUS = BaseRDMConfig.get_base_stimulus_display_config()
DATAFILES = BaseRDMConfig.get_data_files()

# RT Test specific customizations
TASK.update(
    {
        "epochs": {
            "tag": "List of all epochs and their respective parameters in secs",
            "fixation": {
                "tag": "Fixation epoch",
                "duration": lambda: stats.expon.rvs(loc=0.5, scale=1 / 5),
            },
            "stimulus": {
                "tag": "Stimulus epoch",
                "max_viewing": 15,
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
                    "correct": lambda response_time, coh: stats.expon.rvs(loc=0.75, scale=1 / 5),
                    "incorrect": lambda response_time, coh: 3 + 4 * (np.exp(-3 * response_time)),
                    "noresponse": lambda response_time, coh: 3,
                    "invalid": lambda response_time, coh: 2,
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
                "type": "np.array",
                "value": np.array([-100, -36, -18, -9, 0, 9, 18, 36, 100]),
            },
            "repeats_per_block": {
                "tag": "Number of repeats of each coherences per block",
                "type": "np.array",
                "value": np.array([3, 3, 3, 3, 3, 3, 3, 3, 3]),
            },
        },
        "bias_correction": {
            "bias_window": 20,
            "passive": {
                "coherence_threshold": 101,  # Disabled for testing
            },
            "active": {
                "abs_bias_threshold": 1.01,  # Disabled for testing
                "correction_strength": 0,  # No correction for testing
            },
        },
        "training_type": {
            "tag": "Training type: 0: passive-only, 1: active-passive, 2: active-only",
            "value": 2,
        },
    },
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
