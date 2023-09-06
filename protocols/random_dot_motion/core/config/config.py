from pathlib import Path

import numpy as np
from scipy.stats import pearson3

REQUIRED_HARDWARE = ["Arduino", "Display"]

REQUIRED_MODULES = ["Task", "Stimulus", "Behavior"]

TASK = {
    "epochs": {
        "tag": "List of all epochs and their respective parameters in secs",
        "fixation": {
            "tag": "Fixation epoch",
            "duration": 1.000,
        },
        "stimulus": {
            "tag": "Stimulus epoch",
            "max_viewing": 60,
            "min_viewing": 0.3,
            # TODO: move passive_viewing to free reward and rt dynamic training as this is not generic to all stages
            "passive_viewing": lambda coh_level: pearson3.rvs(
                skew=0.6, loc=4.5, scale=1.5, size=1
            )[0],
        },
        "reinforcement": {
            "tag": "Reinforcement epoch",
            "duration": 0,
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
            "type": "list",
            "value": np.array([-100, -72, -36, -18, -9, 0, 9, 18, 36, 72, 100]),
        },
        "active_coherences": {
            "tag": "Signed coherences to be used withough graduation",
            "type": "int",
            "value": np.array([-100, -72, 72, 100]),
        },
        "repeats_per_block": {
            "tag": "Number of repeats of each coherences per block",
            "type": "int",
            "value": 3,
        },
    },
    "bias_correction": {
        "repeat_threshold": {
            "active": 100,
            "passive": 35,
        },
        "rolling_window": 10,
    },
}

STIMULUS = {
    "load_media": {
        "tag": "Load media for visual and audio stimuli if any (relative to root directory)",
        "value": {
            "images": None,
            "videos": None,
            "audios": {
                "fixation_tone": "protocols/random_dot_motion/stimulus/audio/fixation_tone.wav",
                "correct_tone": "protocols/random_dot_motion/stimulus/audio/correct_tone.wav",
                "incorrect_tone": "protocols/random_dot_motion/stimulus/audio/incorrect_tone.wav",
                "stimulus_tone": "protocols/random_dot_motion/stimulus/audio/stimulus_tone.wav",
            },
        },
    },
    "required_functions": {
        "tag": "List of all functions required for this phase. Please note that any color passed as a list will have to be converted to tuple for better performance.",
        "value": {
            "initiate_fixation": {
                "background_color": (0, 0, 0),
                "audio": "fixation_tone",
            },
            "initiate_stimulus": {
                "stimulus_size": (1280, 720),
                "background_color": (0, 0, 0),
                "dots": {
                    "dot_radius": 17,
                    "dot_color": (255, 255, 255),
                    "dot_fill": 15,
                    "dot_vel": 350,  # 50 degrees/sec
                    "dot_lifetime": 30,
                },
                "audio": "stimulus_tone",
            },
            "update_stimulus": None,
            "initiate_reinforcement": {
                "background_color": (255, 255, 255),
                "audio": {
                    "correct": "correct_tone",
                    "incorrect": "incorrect_tone",
                    "invalid": "incorrect_tone",
                },
            },
            "update_reinforcement": None,
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
                "update_func": None,  # "update_reinforcement",
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
