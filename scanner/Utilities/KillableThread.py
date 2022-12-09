import sys
import trace
import threading


class KillableThread(threading.Thread):
    """
    An extension of the Thread class adding thread kill functionality.
    """

    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        self.__run_backup = self.run
        self.run = self.__run
        threading.Thread.start(self)

    def __run(self):
        sys.settrace(self._globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def _globaltrace(self, frame, event, arg):
        if event == 'call':
            return self._localtrace
        else:
            return None

    def _localtrace(self, frame, event, arg):
        if self.killed:
            if event == 'line':
                raise SystemExit()
        return self._localtrace

    def kill(self):
        """
    Kill the created Thread and force stop any process currentyl running
    """
        self.killed = True
