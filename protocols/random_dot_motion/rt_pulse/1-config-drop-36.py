
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
            "min_viewing": 0,
        },
        "reinforcement": {
            "tag": "Reinforcement epoch. Returns delay in stimulus display and delay screen duration (usually white).",
            "duration": {
                "correct": lambda response_time: 0,
                "incorrect": lambda response_time: 0,
                "noresponse": lambda response_time: 0,
            },
        },
        "delay": {
            "tag": "Delay epoch. Returns delay in stimulus display and delay screen duration (usually white).",
            "duration": {
                "correct": lambda response_time, coh: 0,
                "incorrect": lambda response_time, coh: 0,
                "noresponse": lambda response_time, coh: 0,
            },
        },
        "intertrial": {
            "tag": "Intertrial epoch",
            "duration": {
                "correct": lambda response_time, coh: stats.expon.rvs(loc=0.25, scale=0.075),
                "incorrect": lambda response_time, coh: 3 + 4 * (np.exp(-3 * response_time)),
                "noresponse": lambda response_time, coh: 7,
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
        "pulse_probabilities": {
            "tag": "Probability of pulse at each coherence [left_100_early, left_100_middle, left_100_late, right_100_early, right_100_middle, right_100_late, control_early, control_middle, control_late]",
            "type": "dict",
            "value": {
                # drop 36
                -100: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                -36: [0.0, 0.0, 0.0, 0.0, 0.3, 0.3, 0.000, 0.000, 0.40],
                -18: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                -9: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                0: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                9: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                18: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.125, 0.125, 0.15],
                36: [0.0, 0.0, 0.0, 0.0, 0.3, 0.3, 0.000, 0.000, 0.40],
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
    "rolling_performance": {
        "rolling_window": 50,
        "reward_volume": 1.5,
        "current_coherence_level": 6,
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
                "8KHz": "protocols/random_dot_motion/core/stimulus/audio/8KHz_2sec.wav",
                "16KHz": "protocols/random_dot_motion/core/stimulus/audio/16KHz_2sec.wav",
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
                    "dot_vel": 200, #for 25 degrees/sec
                    "dot_lifetime": 60,
                },
                "audio": {
                        "8KHz": None, #"8KHz",
                        "16KHz": None, #"16KHz",
                }
            },
            "update_stimulus": None,
            "initiate_reinforcement": {
                "background_color": (0, 0, 0),
                "audio": {
                    "correct": None, # "correct_tone",
                    "incorrect": None, # "incorrect_tone",
                    "noresponse": None,  # "incorrect_tone",
                },
            },
            "update_reinforcement": None,
            "initiate_delay": {
                "background_color": (0, 0, 0),
            },
            "update_delay": None,
            "initiate_must_respond": None,
            "update_must_respond": None,
            "initiate_intertrial": {"background_color": (0, 0, 0)},
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
                "update_func": None, #"update_delay,
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
SUBJECT = {}

DATAFILES = {
    "lick": "_lick.csv",
    "trial": "_trial.csv",
}
