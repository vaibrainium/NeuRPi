"""
Base configuration template for Random Dot Motion experiments.

Provides common configuration structure to reduce repetition.
"""

from __future__ import annotations

import numpy as np
from scipy import stats


class BaseRDMConfig:
    """
    Base configuration class for RDM experiments.

    Contains common configuration patterns shared across experiments.
    """

    @staticmethod
    def get_base_task_config():
        """Get base task configuration common to all RDM experiments."""
        return {
            "epochs": {
                "tag": "List of all epochs and their respective parameters in secs",
                "fixation": {
                    "tag": "Fixation epoch",
                    "duration": lambda: 0,
                },
                "stimulus": {
                    "tag": "Stimulus epoch",
                    "max_viewing": 3,
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
                        "mode": ["LED", "SCREEN"],
                    },
                },
                "intertrial": {
                    "tag": "Intertrial epoch",
                    "duration": {
                        "correct": lambda response_time, coh: stats.expon.rvs(
                            loc=0.75,
                            scale=1 / 5,
                        ),
                        "incorrect": lambda response_time, coh: 3 + 4 * (np.exp(-3 * response_time)),
                        "noresponse": lambda response_time, coh: 3,
                        "invalid": lambda response_time, coh: 2,
                    },
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
        }

    @staticmethod
    def get_base_stimulus_config():
        """Get base stimulus configuration common to all RDM experiments."""
        return {
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
        }

    @staticmethod
    def get_base_stimulus_display_config():
        """Get base stimulus display configuration."""
        return {
            "load_media": {
                "tag": "Load media for visual and audio stimuli",
                "value": {
                    "images": None,
                    "videos": None,
                    "audios": {
                        "fixation_tone": "protocols/random_dot_motion/core/stimulus/audio/fixation_tone_ramp.wav",
                        "correct_tone": "protocols/random_dot_motion/core/stimulus/audio/correct_tone.wav",
                        "incorrect_tone": "protocols/random_dot_motion/core/stimulus/audio/incorrect_tone.wav",
                        "stimulus_tone": "protocols/random_dot_motion/core/stimulus/audio/fixation_tone_ramp.wav",
                        "8KHz": "protocols/random_dot_motion/core/stimulus/audio/8KHz_2sec.wav",
                        "16KHz": "protocols/random_dot_motion/core/stimulus/audio/16KHz_2sec.wav",
                    },
                },
            },
            "required_functions": {
                "tag": "Required functions for stimulus display",
                "value": {
                    "initiate_fixation": {
                        "background_color": (0, 0, 0),
                        "audio": None,
                    },
                    "initiate_stimulus": {
                        "background_color": (0, 0, 0),
                        "stimulus_size": (1280, 720),
                        "dots": {
                            "dot_radius": 10,
                            "dot_color": (255, 255, 255),
                            "dot_fill": 15,
                            "dot_vel": 300,
                            "dot_lifetime": 60,
                        },
                        "audio": {
                            "onset_tone": None,
                        },
                    },
                    "initiate_reinforcement": {
                        "background_color": (0, 0, 0),
                        "audio": {
                            "correct": None,
                            "incorrect": None,
                            "noresponse": None,
                            "invalid": None,
                        },
                    },
                    "initiate_intertrial": {
                        "background_color": (0, 0, 0),
                    },
                },
            },
            "task_epochs": {
                "tag": """List of all epochs and their respective functions
                    Format:
                        epoch_name:
                            init_func: function to initiate epoch. This will be executed once at the beginning of epoch.
                            update_func: function to update epoch. This will be executed continuously until epoch is over.""",
                "value": {
                    "fixation_epoch": {
                        "clear_queue": True,
                        "init_func": "initiate_fixation",
                        "update_func": None,
                    },
                    "stimulus_epoch": {
                        "clear_queue": True,
                        "init_func": "initiate_stimulus",
                        "update_func": "update_stimulus",
                    },
                    "reinforcement_epoch": {
                        "clear_queue": True,
                        "init_func": "initiate_reinforcement",
                        "update_func": None,
                    },
                    "delay_epoch": {
                        "clear_queue": True,
                        "init_func": "initiate_delay",
                        "update_func": None,  # "update_delay", #None,
                    },
                    "must_respond_epoch": {
                        "clear_queue": False,
                        "init_func": "initiate_must_respond",
                        "update_func": None,
                    },
                    "intertrial_epoch": {
                        "clear_queue": True,
                        "init_func": "initiate_intertrial",
                        "update_func": None,
                    },
                },
            },
        }
