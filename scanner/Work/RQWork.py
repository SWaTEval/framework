import importlib
import time

from typing import Any

from omegaconf import OmegaConf
from redis.client import Redis
from rq import Queue

from scanner.Base.BaseModule import BaseModule
from scanner.Base.BaseWork import BaseWork

# This function is used by the RQ worker. It loads a scanner module dynamically and runs it continuously
def _start_module(module_name, class_name: str, class_args=(), throttle_ms=200):
    # Dynamically load module and class
    module = importlib.import_module(module_name)
    module_class = getattr(module, class_name)

    # Chcek if the loaded class is of proper type
    assert issubclass(module_class, BaseModule), "The input class must be of type BaseModel"

    # Create an instance of te class
    class_instance = module_class(class_args)

    # Run run() implementation of the class
    while True:
        class_instance.run()
        time.sleep(throttle_ms/1000)

class RQBaseWork(BaseWork):
    _redis_connection: Redis
    _queue: Queue

    _for_worker: str
    _module_name: str
    _class_name: str
    _class_args: Any

    # Extend init method to create a redis connection at start
    def __init__(self, for_worker, module_name, class_name: str, **kwargs):
        self._for_worker = for_worker
        self._module_name = module_name
        self._class_name = class_name
        self._kwargs = kwargs

        config = OmegaConf.load('config.yaml')
        
        redis_section = config['redis_credentials']

        redis_host = redis_section['host']
        redis_port = int(redis_section['port'])
        redis_db = int(redis_section['db'])

        self._redis_connection = Redis(host=redis_host, port=redis_port, db=redis_db)
        self._queue = Queue(name=for_worker, connection=self._redis_connection)

    def handle(self):
        self._queue.enqueue(_start_module, args=(self._module_name, self._class_name, *self._kwargs))