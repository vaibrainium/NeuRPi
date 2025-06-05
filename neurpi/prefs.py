from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any

from omegaconf import DictConfig, OmegaConf


class Prefs:
    """Class to manage configuration files."""

    def __init__(
        self,
        directory: Path | None = None,
        filename: str | None = None,
        mode: str | None = None,
    ) -> None:
        self.directory = directory
        self.filename = filename
        self.mode = mode
        self._prefs: dict[str, Any] = {}
        self._initialized = False
        self._lock = Lock()
        self.run()

    def import_configuration(self) -> DictConfig:
        """Import saved config file."""
        # Determine config file based on mode if filename not provided
        if not self.filename and self.mode:
            if self.mode in ["server", "terminal"]:
                self.filename = "config_terminal.yaml"
            elif self.mode in ["rig", "pilot"]:
                self.filename = "config_pilot.yaml"
            else:
                # Default to terminal config
                self.filename = "config_terminal.yaml"

        if self.directory and self.filename:
            config_path = Path(self.directory) / self.filename
            if config_path.exists():
                config = OmegaConf.load(config_path)
                # Ensure we return a DictConfig, not ListConfig
                if isinstance(config, DictConfig):
                    return config
                # If it's a ListConfig, wrap it in a dict
                return OmegaConf.create({"data": config})

        # If file doesn't exist or no directory/filename specified, return empty config
        return OmegaConf.create({})

    def get(self, key: str | None = None) -> Any:
        """Get parameter value."""
        if key is None:
            # if no key provided, return whole dictionary
            return self._prefs.copy()
        return self._prefs[key]

    def set(self, key: str, val: Any) -> None:
        """
        Change parameter value.

        Args:
            key: Dictionary key that needs to be changed
            val: updated value of the key parameter

        """
        if (
            key in self._prefs
            and isinstance(self._prefs[key], dict)
            and "default" in self._prefs[key]
        ):
            # Preserve existing structure if it has a 'default' field
            temp_dict_holder = self._prefs[key].copy()
            temp_dict_holder["default"] = val
            self._prefs[key] = temp_dict_holder
        else:
            # Simple value assignment
            self._prefs[key] = val

        if self._initialized:
            self.save_prefs()

    def save_prefs(self, prefs_filename: str | None = None) -> None:
        """Save preferences to file."""
        if not prefs_filename:
            if self.filename:
                prefs_filename = str(Path.cwd() / "neurpi" / "config" / self.filename)
            else:
                msg = "No filename specified for saving preferences"
                raise ValueError(msg)

        with self._lock:
            Path(prefs_filename).parent.mkdir(parents=True, exist_ok=True)
            with Path(prefs_filename).open("w", encoding="utf-8") as f:
                OmegaConf.save(self._prefs, f)

    def run(self) -> None:
        """Initialize configuration from file."""
        try:
            config = self.import_configuration()
            self._prefs.update(config)
            self._initialized = True
        except (FileNotFoundError, OSError, ValueError) as e:
            print(f"Warning: Could not load configuration: {e}")
            self._initialized = True
    def clear(self) -> None:
        """Clear loaded prefs (for testing)."""
        self._prefs.clear()

    def set_mode(self, mode: str) -> None:
        """Set the mode and reload configuration if needed."""
        if self.mode != mode:
            self.mode = mode
            self.filename = None  # Reset filename to let import_configuration determine it
            config = self.import_configuration()
            self._prefs.clear()
            self._prefs.update(config)


# Global instance for backward compatibility
# Use absolute path based on the location of this file
_neurpi_dir = Path(__file__).parent
prefs = Prefs(directory=_neurpi_dir / "config")


def configure_prefs(mode: str = None) -> Prefs:
    """
    Configure the global prefs instance for a specific mode.

    Args:
        mode: The mode to configure for ('server'/'terminal' or 'rig'/'pilot')

    Returns:
        The configured prefs instance
    """
    global prefs
    if mode:
        prefs.set_mode(mode)
    return prefs
