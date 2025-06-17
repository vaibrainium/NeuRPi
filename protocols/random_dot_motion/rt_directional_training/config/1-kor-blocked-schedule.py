"""
Refactored RT Directional Training configuration using base template.

This eliminates ~150 lines of repetitive configuration code.
"""

import numpy as np

from protocols.random_dot_motion.core.config.base_config import BaseRDMConfig

# Get base configurations
TASK = BaseRDMConfig.get_base_task_config()
STIMULUS = BaseRDMConfig.get_base_stimulus_display_config()

# RT Directional Training specific customizations
TASK.update(
    {
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
                "value": np.array([6, 6]),
            },
            "schedule_structure": {
                "tag": "How to structure block, interleaved or blocked",
                "value": "blocked",
            },
        },
        "bias_correction": {
            "bias_window": 20,
            "repeat_threshold": {
                "passive": 40,
                "active": 1.1,
            },
            "repeat_coherence": {
                "passive": 100,
                "active": 18,
            },
            "correction_strength": 1,
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
