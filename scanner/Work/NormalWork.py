import importlib
import time

from scanner.Base.BaseModule import BaseModule
from scanner.Base.BaseWork import BaseWork


class NormalBaseWork(BaseWork):
    _class_instance: BaseModule

    def __init__(self, for_worker, module_name, class_name: str, **kwargs):
        # Dynamically load module and class
        module = importlib.import_module(module_name)
        module_class = getattr(module, class_name)

        # Check if the loaded class is of proper type
        assert issubclass(module_class, BaseModule), "The input class must be of type BaseModule"

        # Create an instance of te class
        self._class_instance = module_class(**kwargs)

    def handle(self):
        return self._class_instance.run()
