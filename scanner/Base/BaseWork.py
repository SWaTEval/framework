from abc import ABC, abstractmethod


class BaseWork(ABC):
    """
    Interface for the :class:`Work` classes.
    """

    @abstractmethod
    def __init__(self, for_worker: str, module_name: str, class_name: str, class_args=()):
        """
        Work constructor

        :param for_worker: Name of the worker that will take this type of work
        :type for_worker: str

        :param module_name: Path to the module using the Python convention (Example my_library.my_module.Module)
        :type module_name: str

        :param class_name: Name of the class that will be taken from the selected module
        :type class_name: str

        :param class_args: Tuple of arguments that are going to be supplied by the worker to the :class:`BaseModule` used by the :class:`BaseWork` class (Warning: This feature is not properly tested and may not work as intended.)
        :type class_args: tuple
        """
        pass

    @abstractmethod
    def handle(self):
        """
        This method implements the functionality of the work to be done
        """
        pass
