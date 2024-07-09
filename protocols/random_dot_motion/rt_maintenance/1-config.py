from pathlib import Path

import numpy as np
from scipy import stats

REQUIRED_HARDWARE = ["Arduino", "Display"]

REQUIRED_MODULES = ["Task", "Stimulus", "Behavior"]

TASK = {
    "epochs": {
        "tag": "List of all epochs and their respective parameters in secs",
        "fixation": {"tag": "Fixation epoch", "duration": lambda: stats.gamma.rvs(a=1.6, loc=0.5, scale=0.04)},
        "stimulus": {
            "tag": "Stimulus epoch",
            "max_viewing": 25,
            "min_viewing": 0, #0.3,
        },
        "reinforcement": {
            "tag": "Reinforcement epoch. Returns delay in stimulus display and delay screen duration (usually white).",
            "duration": {
                "correct": lambda response_time: 0.5,
                "incorrect": lambda response_time: 1.5,
                "noresponse": lambda response_time: 1.5,
            },
        },
        "delay": {
            "tag": "Delay epoch. Returns delay in stimulus display and delay screen duration (usually white).",
            "duration": {
                "correct": lambda response_time, coh: 0.000,
                # "incorrect": lambda response_time, coh: 0.5+(6*np.exp(-3 * response_time)), #5,
                "incorrect": lambda response_time, coh: 5+(20*np.exp(-4 * response_time)), #5,
                "noresponse": lambda response_time, coh: 10,
            },
        },
        "intertrial": {
            "tag": "Intertrial epoch",
            "duration": 0.500,
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
            "value": np.array([-100, -72, -36, -18, -9, 9, 18, 36, 72, 100]),
        },
        "repeats_per_block": {
            "tag": "Number of repeats of each coherences per block",
            "type": "np.array",
            "value": np.array([4, 4, 3, 3, 2, 2, 3, 3, 4, 4]) # 3,
        },
    },
    "rolling_performance": {
        "rolling_window": 50,
        "current_coherence_level": 2,
        "reward_volume": 1.5,
    },
    "bias_correction": {
        "repeat_threshold": {
            "active": 100,
            "passive": 35,
        },
        "bias_window": 10,
    },
    "training_type": {
        "tag": "Training type: 0: passive-only, 1: active-passive, 2: active-only",
        "value": 2,
    },
    "fixed_ratio": {
        "tag": "Fixed reward ratio minimum streak",
        "value": 1000,
    },
}

STIMULUS = {
    "load_media": {
        "tag": "Load media for visual and audio stimuli if any (relative to root directory)",
        "value": {
            "images": None,
            "videos": None,
            "audios": {
                "fixation_tone": "protocols/random_dot_motion/core/stimulus/audio/fixation_tone_ramp.wav",
                "correct_tone": "protocols/random_dot_motion/core/stimulus/audio/correct_tone.wav",
                "incorrect_tone": "protocols/random_dot_motion/core/stimulus/audio/incorrect_tone.wav",
                "stimulus_tone": "protocols/random_dot_motion/core/stimulus/audio/fixation_tone_ramp.wav",
            },
        },
    },
    "required_functions": {
        "tag": "List of all functions required for this phase. Please note that any color passed as a list will have to be converted to tuple for better performance.",
        "value": {
            "initiate_fixation": {
                "background_color": (0, 0, 0),
                "audio": None, #"fixation_tone",
            },
            "initiate_stimulus": {
                "stimulus_size": (1280, 720),
                "background_color": (0, 0, 0),
                "dots": {
                    "dot_radius": 17,
                    "dot_color": (255, 255, 255),
                    "dot_fill": 15,
                    "dot_vel": 200, #350,  # 50 degrees/sec
                    "dot_lifetime": 60,
                },
                "audio": None,  # "stimulus_tone",
            },
            "update_stimulus": None,
            "initiate_reinforcement": {
                "background_color": (255, 255, 255),
                "audio": {
                    "correct": "correct_tone",
                    "incorrect": "incorrect_tone",
                    "noresponse": "incorrect_tone",
                    "invalid": None,  # "incorrect_tone",
                },
            },
            "update_reinforcement": None,
            "initiate_delay": {
                "background_color": (255, 255, 255),
            },
            "update_delay": None,
            "initiate_must_respond": None,
            "update_must_respond": None,
            "initiate_intertrial": {"background_color": (100, 100, 100)},
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
                "clear_queue": False,
                "init_func": "initiate_reinforcement",
                "update_func": "update_reinforcement",
            },
            "delay_epoch": {
                "clear_queue": True,
                "init_func": "initiate_delay",
                "update_func": None, #"update_delay", #None,
            },
            "must_respond_epoch": {
                "clear_queue": False,
                "init_func": "initiate_must_respond",
                "update_func": "update_must_respond",
            },
            "intertrial_epoch": {
                "clear_queue": True,
                "init_func": "initiate_intertrial",
                "update_func": None,
            },
        },
    },
}

SUBJECT = {}

DATAFILES = {
    "lick": "_lick.csv",
    "trial": "_trial.csv",
}
