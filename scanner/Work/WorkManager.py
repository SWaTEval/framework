from typing import List
from redis import Redis
from scanner.Work.NormalWork import NormalBaseWork
from scanner.Work.RQWork import RQBaseWork
from scanner.Work.ThreadedWork import ThreadedBaseWork
from scanner.Base.BaseWork import BaseWork

class WrongWorkTypeException(BaseException):
    pass

class WorkManager:
    _redis_connection: Redis
    _work_list: List[BaseWork] = list()
    _execution_type: str

    def __init__(self, execution_type):
        assert execution_type in ['sequential', 'parallel-rq', 'parallel-threaded'], "Wrong execution type"
        self._execution_type = execution_type

    def create_work(self, for_worker, module_name, class_name: str, **kwargs):
        if self._execution_type == 'sequential':
            work = NormalBaseWork(for_worker, module_name, class_name, **kwargs)
        elif self._execution_type == 'parallel-rq':
            work = RQBaseWork(for_worker, module_name, class_name, **kwargs)
        elif self._execution_type == 'parallel-threaded':
            work = ThreadedBaseWork(for_worker, module_name, class_name, **kwargs)
        else:
            raise WrongWorkTypeException('Bad work type')

        self._work_list.append(work)

    def get_work_done(self):
        if self._execution_type == 'sequential':
            # Execute each scanner module in the local thread
            while True:
                for work in self._work_list:
                    work_output = work.handle()
                    if work_output == "crawling converged":
                        return

        elif self._execution_type == 'parallel-rq':
            # Send work to redis
            for work in self._work_list:
                work.handle()
        elif self._execution_type == 'parallel-threaded':
            # Send work to redis
            for work in self._work_list:
                work.handle()
        else:
            raise WrongWorkTypeException('Bad work type')
