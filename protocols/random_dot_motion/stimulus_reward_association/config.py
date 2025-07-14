import numpy as np
from scipy.stats import truncexpon

REQUIRED_HARDWARE = ["Arduino", "Display"]

REQUIRED_MODULES = ["Task", "Stimulus", "Behavior"]


def get_expon_flat_hazard_function(start, end, b=5):
    """
    Returns a truncated exponential sampler with consistent decay shape
    regardless of interval width.

    Parameters
    ----------
    - start: minimum value
    - end: maximum value
    - b: shape parameter (higher means steeper decay)

    Returns
    -------
    - A callable that samples from a truncated exponential distribution.

    """
    interval = end - start
    scale = interval / b
    return lambda: np.clip(truncexpon.rvs(b=b, loc=start, scale=scale), start, end)


TASK = {
    "epochs": {
        "tag": "List of all epochs and their respective parameters in secs",
        "fixation": {"tag": "Fixation epoch", "duration": get_expon_flat_hazard_function(start=2, end=3)},
        "stimulus": {
            "tag": "Stimulus epoch",
            "max_viewing": 10,
            "min_viewing": 0,
        },
        "reinforcement": {
            "tag": "Reinforcement epoch. Returns delay in stimulus display and delay screen duration (usually white).",
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
                "correct": lambda response_time, coh: get_expon_flat_hazard_function(start=2, end=3)(),
                "incorrect": lambda response_time, coh: get_expon_flat_hazard_function(start=6, end=10)(),
                "noresponse": lambda response_time, coh: get_expon_flat_hazard_function(start=6, end=10)(),
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
        "schedule_structure": {"tag": "How to structure block, interleaved or blocked", "value": "interleaved"},
    },
    "rolling_performance": {
        "rolling_window": 50,
        "current_coherence_level": 1,
        "reward_volume": 1.5,
    },
    "bias_correction": {
        "bias_window": 20,
        "passive": {
            "coherence_threshold": 40,
        },
        "active": {
            "abs_bias_threshold": 1.1,  # absolute bias threshold for active trials range 0 to 1
            "correction_strength": 1,  # between 0 and 1. 0: no correction, 1: full correction block
        },
    },
    "training_params": {
        "tag": "All other training related parameters",
        "passive_trial_probability": 1,  # between 0 & 1: 1 means all trials are passive, 0 means all trials are active
        "passive_coherence_threshold": 35,
        "passive_viewing_duration_func": get_expon_flat_hazard_function(start=0.2, end=0.3),
    },
    "fixed_ratio": {
        "tag": "Fixed reward ratio minimum streak",
        "value": 1000,
    },
    "reward": {
        "volume": 2,
        "must_consume": True,
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
                "background_color": (22, 62, 100),
                "audio": None,
            },
            "initiate_stimulus": {
                "stimulus_size": (1280, 720),
                "background_color": (0, 0, 0),
                "dots": {
                    "dot_radius": 9,  # 2 degrees,
                    "dot_color": (255, 255, 255),
                    "dot_fill": 15,
                    "dot_vel": 450,  # for 45 degrees/sec
                    "dot_lifetime": 60,
                },
                "audio": {
                    "onset_tone": None,  # "fixation_tone",
                    "8KHz": None,  # "8KHz",
                    "16KHz": None,  # "16KHz",
                },
            },
            "update_stimulus": None,
            "initiate_reinforcement": {
                "background_color": (0, 0, 0),
                "audio": {
                    "correct": None,  # "correct_tone",
                    "incorrect": None,  # "incorrect_tone",
                    "noresponse": None,  # "incorrect_tone",
                    "invalid": None,  # "incorrect_tone",
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

SUBJECT = {}

DATAFILES = {
    "lick": "_lick.csv",
    "trial": "_trial.csv",
}
