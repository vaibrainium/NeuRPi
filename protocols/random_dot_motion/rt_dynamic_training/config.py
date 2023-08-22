from pathlib import Path

import numpy as np
from scipy.stats import pearson3

REQUIRED_HARDWARE = ["Arduino", "Display"]

REQUIRED_MODULES = ["Task", "Stimulus", "Behavior"]

GRADUATION = {
    "coherence_levels": {
        "tag": "List of all coherence levels used in this phase",
        "value": {
            1: np.array([-100, 100]),
            2: np.array([-100, -72, 72, 100]),
            3: np.array([-100, -72, -36, 36, 72, 100]),
            4: np.array([-100, -72, -36, -18, 18, 36, 72, 100]),
            5: np.array([-100, -72, -36, -18, -9, 9, 18, 36, 72, 100]),
            6: np.array([-100, -72, -36, -18, -9, 0, 9, 18, 36, 72, 100]),
        },
    },
    "accuracy_threadholds": {
        "tag": "List of all accuracy conditions for each coherence level to move forward (or backward)",
        "value": {
            1: np.array([0.7, 0.7]),
            2: np.array([0.7, 0.7, 0.7, 0.7]),
            3: np.array([0.7, 0.7, 0.7, 0.7, 0.7, 0.7]),
            4: np.array([0.7, 0.7, 0.7, 0.7, 0.7, 0.7]),
            5: np.array([0.7, 0.7, 0.7, 0.7, 0.7, 0.7]),
            6: np.array([0.7, 0.7, 0.7, 0.7, 0.7, 0.7]),
        },
    },
    "trial_thresholds": {
        "tag": "Number of trials required to move forward (or backward) for each coherence level",
        "value": {
            1: 200,
            2: 200,
            3: 200,
            4: 200,
            5: 200,
            6: 200,
        },
    },
}


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
            "passive_viewing": lambda coh_level: pearson3.rvs(
                skew=0.6, loc=(coh_level - 1) * 10, scale=1.5, size=1
            )[0],
        },
        "reinforcement": {
            "tag": "Reinforcement epoch",
            "duration": {
                "correct": 0.500,
                "incorrect": 1.500,
                "invalid": 1.500,
            },
        },
        "intertrial": {
            "tag": "Intertrial epoch",
            "duration": {
                "correct": 0.500,
                "incorrect": lambda dur: 0.5 + (25 * (np.exp(-4 * dur))),
                "invalid": lambda dur: 0.5 + (25 * (np.exp(-4 * dur))),
            },
        },
    },
    "stimulus": {
        "coherences": {
            "tag": "List of all coherences used in study",
            "type": "list",
            "value": [100, 72, 36, 18, 9, 0],
        },
        "coherence_level": {
            "tag": "Level of difficulty for current block",
            "type": "int",
            "value": 1,
        },
        "repeats_per_block": {
            "tag": "Number of repeats of each coherences per block",
            "type": "int",
            "value": 3,
        },
    },
    "bias": {
        "active_correction": {
            "tag": "Repeat threshold",
            "type": "int",
            "threshold": 100,
        },
        "passive_correction": {
            "tag": "Repeat threshold and window",
            "type": "int",
            "threshold": 35,
            "rolling_window": 10,
        },
    },
    "timings": {
        "fixation": {
            "tag": "Mean fixation time in secs",
            "type": "int",
            "value": 1.00,
        },
        "stimulus": {
            "tag": "Minimum and Maximum stimulus time in secs",
            "type": "int",
            "max_viewing": 60.000,
            "min_viewing": 0.3,
        },
        "intertrial": {
            "tag": "Inter-trial interval in secs",
            "type": "int",
            "value": 0.500,
        },
    },
    "feedback": {
        "correct": {
            "visual": {
                "tag": "Visual feedback for correct trial",
                "type": "tuple",
            },
            "audio": {
                "tag": "Audio feedback for correct trial",
                "type": "tuple",
            },
            "time": {
                "tag": "Temporal delay feedback in secs",
                "type": "int",
                "value": 0.500,
            },
            "intertrial": {
                "tag": "Reaction Time dependent exponentially decaying intertrial_duration",
                "base": 0,
                "power": 0,
            },
        },
        "incorrect": {
            "visual": {
                "tag": "Visual feedback for incorrect trial",
                "type": "tuple",
            },
            "audio": {
                "tag": "Audio feedback for incorrect trial",
                "type": "tuple",
            },
            "time": {
                "tag": "Temporal delay feedback in secs",
                "type": "int",
                "value": 1.500,
            },
            "intertrial": {
                "tag": "Reaction Time dependent exponentially decaying intertrial_duration",
                "base": 25,
                "power": -4,
            },
        },
        "invalid": {
            "visual": {
                "tag": "Visual feedback for invalid trial",
                "type": "tuple",
            },
            "audio": {
                "tag": "Audio feedback for invalid trial",
                "type": "tuple",
            },
            "time": {
                "tag": "Temporal delay feedback in secs",
                "type": "int",
                "value": 1.500,
            },
            "intertrial": {
                "tag": "Reaction Time dependent exponentially decaying intertrial_duration",
                "base": 25,
                "power": -4,
            },
        },
    },
    "training_type": {
        "value": 1,
        "tag": """
            0                  : 'Passive-Only'
            1                  : 'Active-Passive'
            2                  : 'Active-Only'
            """,
        "active_passive": {
            "tag": "Parameters for Active-Passive Training (time in secs)",
            "passive_rt_mu": 10.000,
            "passive_rt_skew": 0.6,
            "passive_rt_sigma": 1.5,
        },
        "graduation_direction": {
            "tag": "Whether graduate is unidirectional i.e., only increasing difficulty (1) or bidirectional (0)",
            "value": 0,
        },
    },
}

STIMULUS = {
    "load_media": {
        "tag": "Load media for visual and audio stimuli if any (relative to root directory)",
        "value": {
            "images": None,
            "videos": None,
            "audios": {
                "fixation_tone": Path(
                    "protocols/random_dot_motion/stimulus/audio/fixation_tone.wav"
                ),
                "correct_tone": Path(
                    "protocols/random_dot_motion/stimulus/audio/correct_tone.wav"
                ),
                "incorrect_tone": Path(
                    "protocols/random_dot_motion/stimulus/audio/incorrect_tone.wav"
                ),
                "stimulus_tone": Path(
                    "protocols/random_dot_motion/stimulus/audio/stimulus_tone.wav"
                ),
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
                    "dot_vel": 420,
                    "dot_lifetime": 30,
                },
                "audio": "stimulus_tone",
            },
            "update_stimulus": None,
            "initiate_reinforcement": {
                "audio": {
                    "correct": "correct_tone",
                    "incorrect": "incorrect_tone",
                    "invalid": "incorrect_tone",
                },
            },
            "update_reinforcement": None,
            "initiate_must_respond": None,
            "update_must_respond": None,
            "initiate_intertrial": {
                "background_color": (255, 255, 255),  # (160,160,160)
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
                "clear_queue": False,
                "init_func": "initiate_reinforcement",
                "update_func": "update_reinforcement",
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
    # "event": "_event.csv",
}

