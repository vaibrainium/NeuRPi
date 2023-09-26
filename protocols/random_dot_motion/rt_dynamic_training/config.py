from pathlib import Path

import numpy as np
from scipy import stats

REQUIRED_HARDWARE = ["Arduino", "Display"]

REQUIRED_MODULES = ["Task", "Stimulus", "Behavior"]

TASK = {
    "epochs": {
        "tag": "List of all epochs and their respective parameters in secs",
        "fixation": {"tag": "Fixation epoch", "duration": lambda: stats.gamma.rvs(a=1.5, loc=2, scale=0.3) * 0.75},
        "stimulus": {
            "tag": "Stimulus epoch",
            "max_viewing": 60,
            "min_viewing": 0.3,
            # "passive_viewing": lambda coh_level: pearson3.rvs(skew=0.6, loc=4.5, scale=1.5, size=1)[0], # old free reward
            # "passive_viewing": lambda coh_level: pearson3.rvs(skew=1.5, loc=2, scale=1, size=1)[0], # new free reward
            "passive_viewing": lambda coh_level: stats.pearson3.rvs(skew=0.6, loc=(coh_level - 1) * 10, scale=1.5, size=1)[0],  # new rt dynamic
        },
        "reinforcement": {
            "tag": "Reinforcement epoch. Returns delay in stimulus display and delay screen duration (usually white).",
            "duration": {
                "correct": lambda response_time: 0.300,
                "incorrect": lambda response_time: 0.300, #1.000,
                "noresponse": lambda response_time: 0.300, #1.000,
            },
        },
        "delay": {
            "tag": "Delay epoch. Returns delay in stimulus display and delay screen duration (usually white).",
            "duration": {
                "correct": lambda response_time: 0.000,
                "incorrect": lambda response_time: 8 * (np.exp(-2 * response_time)),
                "noresponse": lambda response_time: 8 * (np.exp(-2 * response_time)),
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
    "rolling_performance": {
        "rolling_window": 50,
        "current_coherence_level": 2,
        "reward_volume": 3,
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
                "audio": None,  # "stimulus_tone",
            },
            "update_stimulus": None,
            "initiate_reinforcement": {
                "background_color": (255, 255, 255),
                "audio": {
                    "correct": "correct_tone",
                    "incorrect": None,  # "incorrect_tone",
                    "noresponse": None,  # "incorrect_tone",
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
                "update_func": None,
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

TASK["epochs"]["stimulus"]["passive_viewing"] = lambda coh_level: pearson3.rvs(skew=0.6, loc=(coh_level - 1) * 10, scale=1.5, size=1)[0]

GRADUATION = {
    "direction": {
        "tag": "Direction of graduation. 0: 'forward' or 1:'forward and backward'",
        "value": 1,
    },
    "coherence_levels": {
        "tag": "List of all coherence levels and their properties used in this phase",
        "value": {
            1: np.array([-100, 100]),
            2: np.array([-100, -72, 72, 100]),
            3: np.array([-100, -72, -36, 36, 72, 100]),
            4: np.array([-100, -72, -36, -18, 18, 36, 72, 100]),
            5: np.array([-100, -72, -36, -18, -9, 9, 18, 36, 72, 100]),
        },
    },
    "accuracy": {
        "rolling_widows": {
            "tag": "Number of trials per coherence to consider for accuracy calculation",
            "value": 50,
        },
        "thresholds": {
            "tag": "List of all accuracy conditions for each coherence level to move forward (or backward)",
            "value": {
                1: np.array([0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7]),
                2: np.array([0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7]),
                3: np.array([0.7, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7, 0.7]),
                4: np.array([0.7, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7, 0.7]),
                5: np.array([0.7, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7, 0.7]),
                6: np.array([0.7, 0.7, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7, 0.7]),
            },
        },
    },
    "trials_threshold": {
        "tag": "Number of trials required to move forward (or backward) for each coherence level",
        "value": {
            1: 0,
            2: 0,
            3: 0,
            4: 200,
            5: 200,
            6: 200,
        },
    },
    "reward_change": {
        "tag": "Reward change for each coherence level increase (or decrease)",
        "value": {
            "increase": 0.3,
            "decrease": 0.3,
        },
    },
}


def grad_check(current_level, accuracy, level_change_trial_counter):
    graduation_direction = GRADUATION["direction"]["value"]
    accuracy_thesholds = GRADUATION["accuracy"]["thresholds"]["value"]
    trials_threshold = GRADUATION["trials_threshold"]["value"]

    next_coherence_level = current_level
    new_trial_counter = level_change_trial_counter + 1

    # forward graduation
    while next_coherence_level < 5:
        if all(accuracy >= accuracy_thesholds[next_coherence_level]) and (new_trial_counter >= trials_threshold[next_coherence_level]):
            next_coherence_level = next_coherence_level + 1
            new_trial_counter = 0
        else:
            break

    # backward graduation
    if graduation_direction == 0:
        while next_coherence_level > 1:
            if any(accuracy < accuracy_thesholds[next_coherence_level - 1]):
                next_coherence_level = next_coherence_level - 1
                new_trial_counter = 0
            else:
                break

    print(f"Coherence level changed from {current_level} to {next_coherence_level}")
    print(f"Trial counter: {level_change_trial_counter} to {new_trial_counter}")
    return next_coherence_level


if __name__ == "__main__":
    GRADUATION["direction"]["value"] = 0
    accuracy = np.array([0.7, 0.2, 0.7, 0.0, 0.0, 0.0, 0.0, 0.7, 0.7, 0.7])
    current_level = 5
    level_change_trial_counter = 1
    current_level = grad_check(current_level, accuracy, level_change_trial_counter)
    level_change_trial_counter = 201
    current_level = grad_check(current_level, accuracy, level_change_trial_counter)
