from collections import OrderedDict as odict

from NeuRPi.config.setup_config import Scopes

_DEFAULTS = odict(
    {
        "NAME": {"type": "str", "text": "Agent Name:", "scope": Scopes.COMMON},
        "PUSHPORT": {
            "type": "int",
            "text": "Push Port - Router port used by the Terminal or upstream agent:",
            "default": "5560",
            "scope": Scopes.COMMON,
        },
        "MSGPORT": {
            "type": "int",
            "text": "Message Port - Router port used by this agent to receive messages:",
            "default": "5565",
            "scope": Scopes.COMMON,
        },
        "TERMINALIP": {
            "type": "str",
            "text": "Terminal IP:",
            "default": "192.168.0.100",
            "scope": Scopes.COMMON,
        },
        "LOGLEVEL": {
            "type": "choice",
            "text": "Log Level:",
            "choices": ("DEBUG", "INFO", "WARNING", "ERROR"),
            "default": "WARNING",
            "scope": Scopes.COMMON,
        },
        "LOGSIZE": {
            "type": "int",
            "text": "Size of individual log file (in bytes)",
            "default": 5 * (2**20),  # 5MB
            "scope": Scopes.COMMON,
        },
        "LOGNUM": {
            "type": "int",
            "text": "Number of logging backups to keep of LOGSIZE",
            "default": 4,
            "scope": Scopes.COMMON,
        },
        # 4 * 5MB = 20MB per module
        "CONFIG": {
            "type": "list",
            "text": "System Configuration",
            "hidden": True,
            "scope": Scopes.COMMON,
        },
        "VENV": {
            "type": "str",
            "text": "Location of virtual environment, if used.",
            "scope": Scopes.COMMON,
            "default": str(Path(sys.prefix).resolve())
            if hasattr(sys, "real_prefix") or (sys.base_prefix != sys.prefix)
            else False,
        },
        "AUTOPLUGIN": {
            "type": "bool",
            "text": "Attempt to import the contents of the plugin directory",
            "scope": Scopes.COMMON,
            "default": True,
        },
        "PLUGIN_DB": {
            "type": "str",
            "text": "filename to use for the .json plugin_db that keeps track of installed plugins",
            "default": str(_basedir / "plugin_db.json"),
            "scope": Scopes.COMMON,
        },
        "BASEDIR": {
            "type": "str",
            "text": "Base Directory",
            "default": str(_basedir),
            "scope": Scopes.DIRECTORY,
        },
        "DATADIR": {
            "type": "str",
            "text": "Data Directory",
            "default": str(_basedir / "data"),
            "scope": Scopes.DIRECTORY,
        },
        "SOUNDDIR": {
            "type": "str",
            "text": "Sound file directory",
            "default": str(_basedir / "sounds"),
            "scope": Scopes.DIRECTORY,
        },
        "LOGDIR": {
            "type": "str",
            "text": "Log Directory",
            "default": str(_basedir / "logs"),
            "scope": Scopes.DIRECTORY,
        },
        "VIZDIR": {
            "type": "str",
            "text": "Directory to store Visualization results",
            "default": str(_basedir / "viz"),
            "scope": Scopes.DIRECTORY,
        },
        "PROTOCOLDIR": {
            "type": "str",
            "text": "Protocol Directory",
            "default": str(_basedir / "protocols"),
            "scope": Scopes.DIRECTORY,
        },
        "PLUGINDIR": {
            "type": "str",
            "text": "Directory to import ",
            "default": str(_basedir / "plugins"),
            "scope": Scopes.DIRECTORY,
        },
        "REPODIR": {
            "type": "str",
            "text": "Location of Autopilot repo/library",
            "default": Path(__file__).resolve().parents[1],
            "scope": Scopes.DIRECTORY,
        },
        "CALIBRATIONDIR": {
            "type": "str",
            "text": "Location of calibration files for solenoids, etc.",
            "default": str(_basedir / "calibration"),
            "scope": Scopes.DIRECTORY,
        },
        "PIGPIO": {
            "type": "bool",
            "text": "Launch pigpio daemon on start?",
            "default": True,
            "scope": Scopes.PILOT,
        },
        "PIGPIOMASK": {
            "type": "str",
            "text": "Binary mask controlling which pins pigpio controls according to their BCM numbering, see the -x parameter of pigpiod",
            "default": "1111110000111111111111110000",
            "scope": Scopes.PILOT,
        },
        "PIGPIOARGS": {
            "type": "str",
            "text": "Arguments to pass to pigpiod on startup",
            "default": "-t 0 -l",
            "scope": Scopes.PILOT,
        },
        "PULLUPS": {
            "type": "list",
            "text": "Pins to pull up on system startup? (list of form [1, 2])",
            "scope": Scopes.PILOT,
        },
        "PULLDOWNS": {
            "type": "list",
            "text": "Pins to pull down on system startup? (list of form [1, 2])",
            "scope": Scopes.PILOT,
        },
        "PING_INTERVAL": {
            "type": "float",
            "text": "How many seconds should pilots wait in between pinging the Terminal?",
            "default": 5,
            "scope": Scopes.PILOT,
        },
        "DRAWFPS": {
            "type": "int",
            "text": "FPS to draw videos displayed during acquisition",
            "default": "20",
            "scope": Scopes.TERMINAL,
        },
        "PILOT_DB": {
            "type": "str",
            "text": "filename to use for the .json pilot_db that maps pilots to subjects (relative to BASEDIR)",
            "default": str(_basedir / "pilot_db.json"),
            "scope": Scopes.TERMINAL,
        },
        "TERMINAL_SETTINGS_FN": {
            "type": "str",
            "text": "filename to store QSettings file for Terminal",
            "default": str(_basedir / "terminal.conf"),
            "scope": Scopes.TERMINAL,
        },
        "TERMINAL_WINSIZE_BEHAVIOR": {
            "type": "choice",
            "text": "Strategy for resizing terminal window on opening",
            "choices": ("remember", "moderate", "maximum", "custom"),
            "default": "remember",
            "scope": Scopes.TERMINAL,
        },
        "TERMINAL_CUSTOM_SIZE": {
            "type": "list",
            "text": "Custom size for window, specified as [px from left, px from top, width, height]",
            "default": [0, 0, 1000, 400],
            "depends": ("TERMINAL_WINSIZE_BEHAVIOR", "custom"),
            "scope": Scopes.TERMINAL,
        },
        "LINEAGE": {
            "type": "choice",
            "text": "Are we a parent or a child?",
            "choices": ("NONE", "PARENT", "CHILD"),
            "scope": Scopes.LINEAGE,
        },
        "CHILDID": {
            "type": "list",
            "text": "List of Child ID:",
            "default": [],
            "depends": ("LINEAGE", "PARENT"),
            "scope": Scopes.LINEAGE,
        },
        "PARENTID": {
            "type": "str",
            "text": "Parent ID:",
            "depends": ("LINEAGE", "CHILD"),
            "scope": Scopes.LINEAGE,
        },
        "PARENTIP": {
            "type": "str",
            "text": "Parent IP:",
            "depends": ("LINEAGE", "CHILD"),
            "scope": Scopes.LINEAGE,
        },
        "PARENTPORT": {
            "type": "str",
            "text": "Parent Port:",
            "depends": ("LINEAGE", "CHILD"),
            "scope": Scopes.LINEAGE,
        },
        "AUDIOSERVER": {
            "type": "bool",
            "text": "Enable jack audio server?",
            "scope": Scopes.AUDIO,
        },
        "NCHANNELS": {
            "type": "int",
            "text": "Number of Audio channels (deprecated; used OUTCHANNELS)",
            "default": 1,
            "depends": "AUDIOSERVER",
            "scope": Scopes.AUDIO,
            "deprecation": "Deprecated and will be removed, use OUTCHANNELS instead",
        },
        "OUTCHANNELS": {
            "type": "list",
            "text": "List of Audio channel indexes to connect to",
            "default": "",
            "depends": "AUDIOSERVER",
            "scope": Scopes.AUDIO,
        },
        "FS": {
            "type": "int",
            "text": "Audio Sampling Rate",
            "default": 192000,
            "depends": "AUDIOSERVER",
            "scope": Scopes.AUDIO,
        },
        "ALSA_NPERIODS": {
            "type": "int",
            "text": "number of buffer periods to use with ALSA sound driver",
            "default": 3,
            "depends": "AUDIOSERVER",
            "scope": Scopes.AUDIO,
        },
        "JACKDSTRING": {
            "type": "str",
            "text": "Arguments to pass to jackd, see the jackd manpage",
            "default": "jackd -P75 -p16 -t2000 -dalsa -dhw:sndrpihifiberry -P -rfs -nper -s &",
            "depends": "AUDIOSERVER",
            "scope": Scopes.AUDIO,
        },
    }
)