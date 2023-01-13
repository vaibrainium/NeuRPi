from PyQt5 import QtCore

_INVOKER = None


class InvokeEvent(QtCore.QEvent):
    """
    Sends signals to the main QT thread from spawned message threads
    See `stackoverflow <https://stackoverflow.com/a/12127115>`_
    """

    EVENT_TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, fn, *args, **kwargs):
        """
        Accepts a function, its args and kwargs and wraps them as a
        :class:`QtCore.QEvent`
        """
        QtCore.QEvent.__init__(self, InvokeEvent.EVENT_TYPE)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs


class Invoker(QtCore.QObject):
    """
    Wrapper that calls an evoked event made by :class:`.InvokeEvent`
    """

    def event(self, event):
        """
        Args:
            event:
        """
        event.fn(*event.args, **event.kwargs)
        return True


def get_invoker():
    if globals()["_INVOKER"] is None:
        globals()["_INVOKER"] = Invoker()
    return globals()["_INVOKER"]
