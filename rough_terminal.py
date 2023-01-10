import time

if __name__ == "__main__":

    from NeuRPi.agents.test_terminal import Terminal

    terminal = Terminal()
    terminal.run()
    pass


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    StartWindow = RDK_Application(StimMsg, Camera)
    StartWindow.show()
    sys.exit(app.exec_())
    StimMsg.put(["quit"])
    Display.join()
