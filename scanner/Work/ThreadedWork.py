import importlib
import time
from threading import Thread

from scanner.Base.BaseModule import BaseModule
from scanner.Base.BaseWork import BaseWork

def run_continuous(function, throttle_ms=0):
    while True:
        function()
        time.sleep(throttle_ms/1000)

class ThreadedBaseWork(BaseWork):
    _thread: Thread

    # Extend init method to create a redis connection at start
    def __init__(self, for_worker, module_name, class_name: str, **kwargs):
        # Dynamically load module and class
        module = importlib.import_module(module_name)
        module_class = getattr(module, class_name)

        # Chcek if the loaded class is of proper type
        assert issubclass(module_class, BaseModule), "The input class must be of type BaseModel"

        # Create an instance of te class
        class_instance: BaseModule = module_class(*kwargs)

        self._thread = Thread(name=for_worker, target=run_continuous, args=(class_instance.run,))

    def handle(self):
        self._thread.start()
