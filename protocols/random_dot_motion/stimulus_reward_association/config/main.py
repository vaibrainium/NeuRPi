"""
Refactored RT Maintenance configuration using base template.

This eliminates ~150 lines of repetitive configuration code.
"""

import numpy as np
from scipy import stats

from protocols.random_dot_motion.core.config.base_config import BaseRDMConfig, get_expon_flat_hazard_function

# Get base configurations
TASK = BaseRDMConfig.get_base_task_config()
STIMULUS = BaseRDMConfig.get_base_stimulus_display_config()
DATAFILES = BaseRDMConfig.get_data_files()

# RT Maintenance specific customizations
TASK.update(
    {
        "epochs": {
            "tag": "List of all epochs and their respective parameters in secs",
            "fixation": {
                "tag": "Fixation epoch",
                "duration": get_expon_flat_hazard_function(start=2, end=3),
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
                "knowledge_of_results": {
                    "mode": ["LED"],
                    "duration": 0.5,
                },
            },
            "intertrial": {
                "tag": "Intertrial epoch",
                "duration": {
                    "correct": lambda response_time, coh: get_expon_flat_hazard_function(start=2, end=3)(),
                    "incorrect": lambda response_time, coh: get_expon_flat_hazard_function(start=6, end=10)(),
                    "noresponse": lambda response_time, coh: get_expon_flat_hazard_function(start=6, end=10)(),
                    "invalid": lambda response_time, coh: 5,
                },
            },
        },
        "stimulus": {
            "signed_coherences": {
                "tag": "List of all signed coherences",
                "type": "np.array",
                "value": np.array([-100, -72, 72, 100]),
            },
            "repeats_per_block": {
                "tag": "Number of repeats of each coherences per block",
                "type": "np.array",
                "value": np.array([3, 3, 3, 3]),
            },
            "schedule_structure": {
                "tag": "How to structure block, interleaved or blocked",
                "value": "interleaved",
            },
        },
        "training_params": {
            "tag": "All other training related parameters",
            "passive_trial_probability": 1,  # between 0 & 1: 1 means all trials are passive, 0 means all trials are active
            "passive_coherence_threshold": 35,
            "passive_viewing_duration_func": get_expon_flat_hazard_function(start=0.2, end=0.3),
        },
        "graduation": {
            "tag": "Graduation criteria for coherence level advancement",
            "accuracy_threshold": 80,
            "window_size": 50,
            "coherence_levels": [100, 72, 36, 18, 9],
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
