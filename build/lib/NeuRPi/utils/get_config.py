def get_configuration(directory=None, filename=None):
    """
    Getting configuration from respective config.yaml file.

    Arguments:
        directory (str): Path to configuration directory relative to root directory (as Protocols/../...)
        filename (str): Specific file name of the configuration file
    """
    import hydra

    path = directory
    hydra.initialize(version_base=None, config_path=path)
    return hydra.compose(filename, overrides=[])
