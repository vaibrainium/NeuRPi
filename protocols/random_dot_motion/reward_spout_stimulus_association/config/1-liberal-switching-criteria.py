"""
Refactored Reward Spout Stimulus Association configuration (liberal switching) using base template.

This eliminates ~90 lines of repetitive configuration code.
"""

from protocols.random_dot_motion.core.config.base_config import BaseRDMConfig

# Get base configurations
TASK = BaseRDMConfig.get_base_task_config()
STIMULUS = BaseRDMConfig.get_base_stimulus_display_config()

# Reward Spout Stimulus Association specific customizations
TASK.update(
    {
        "reward": {
            "volume": 2,
            "must_consume": True,  # Ensure the reward is consumed
        },
        "knowledge_of_results": {
            "tag": "Knowledge of results epoch",
            "duration": 0.5,
            "mode": ["LED"],  # Use LED for feedback
        },
        "bias_correction": {
            "window": 20,
            "threshold": 0.5,  # Liberal switching criteria
        },
        "intertrial": {
            "duration": 1,
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
