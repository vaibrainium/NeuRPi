# import Pilot
# @hydra.main(config_path=None)
# def app(cfg: DictConfig) -> None:
#     global app_cfg
#     app_cfg = cfg
#     fn()


# if __name__ == "__main__":
#     app()

if __name__ == "__main__":
    from NeuRPi.agents import test_pilot

    test_pilot.main()

    pass
