"""
Refactored Reward Spout Stimulus Association configuration (conservative with compound conditioning) using base template.

This eliminates ~150 lines of repetitive configuration code.
"""

import numpy as np
from scipy import stats

from protocols.random_dot_motion.core.config.base_config import BaseRDMConfig

# Get base configurations
TASK = BaseRDMConfig.get_base_task_config()
STIMULUS = BaseRDMConfig.get_base_stimulus_display_config()

# Conservative switching with compound conditioning specific customizations
TASK.update(
    {
        "epochs": {
            "tag": "List of all epochs and their respective parameters in secs",
            "fixation": {
                "tag": "Fixation epoch",
                "duration": lambda: 0,  # No fixation for association task
            },
            "stimulus": {
                "tag": "Stimulus epoch",
                "max_viewing": 10,
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
                "knowledge_of_results": {
                    "duration": 0.5,
                },
            },
            "intertrial": {
                "tag": "Intertrial epoch",
                "duration": {
                    "correct": lambda response_time, coh: stats.expon.rvs(loc=5, scale=1 / 5),
                    "incorrect": lambda response_time, coh: 6 + 4 * (np.exp(-3 * response_time)),
                    "noresponse": lambda response_time, coh: 6,
                    "invalid": lambda response_time, coh: 5,
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
                "value": np.array([-100, 100]),
            },
            "repeats_per_block": {
                "tag": "Number of repeats of each coherences per block",
                "type": "np.array",
                "value": np.array([3, 3]),
            },
            "schedule_structure": {
                "tag": "How to structure block, interleaved or blocked",
                "value": "interleaved",
            },
        },
        "bias_correction": {
            "bias_window": 20,
            "passive": {
                "coherence_threshold": 40,
            },
            "active": {
                "abs_bias_threshold": 1.1,
                "correction_strength": 1,
            },
        },
        "reward": {
            "volume": 2,
            "must_consume": True,
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
