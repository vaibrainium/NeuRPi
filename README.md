# NeuRPi
 New version of RDK-Task


## TODO:
Re-work on:
    1) logger module
    2) networking module
        Using ZMQ push and pull via router. 
        Layout will be Rig receives via msgport and pushes via pushport. 
        Communication happens through router/dealer structure. 
    3) invoker:
        Updating GUI from subthreads. Alternate option is use Qthread and QtCore.pyqtSignal signal. This has been previously implemented by me in MOCO of RDK-Task.