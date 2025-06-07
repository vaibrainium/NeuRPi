
REQUIRED_HARDWARE = ["Arduino", "Display"]

REQUIRED_MODULES = ["Task", "Stimulus", "Behavior"]

TASK = {
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
        "window": 10,
        "threshold": 0.20,
    },
    "intertrial": {
        "duration": 1,
	}
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
                "audio": None,  # "fixation_tone",
            },
            "initiate_stimulus": {
                "stimulus_size": (1280, 720),
                "background_color": (0, 0, 0),
                "dots": {
                    "dot_radius": 17,
                    "dot_color": (255, 255, 255),
                    "dot_fill": 15,
                    "dot_vel": 450,  # for 45 degrees/sec
                    "dot_lifetime": 60,
                },
                "audio": {
                    "onset_tone": "fixation_tone",
                    "8KHz": None,  # "8KHz",
                    "16KHz": None,  # "16KHz",
                },
            },
            "update_stimulus": None,
            "initiate_reinforcement": {
                "background_color": (0, 0, 0),
                "audio": {
                    "correct": "correct_tone",
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
            "must_respond_epoch": {
                "clear_queue": False,
                "init_func": "initiate_fixation",
                "update_func": None,
            },
            "reinforcement_epoch": {
                "clear_queue": True,
                "init_func": "initiate_fixation",
                "update_func": None,
            },
            "intertrial_epoch": {
                "clear_queue": True,
                "init_func": "initiate_fixation",
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
