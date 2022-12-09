import logging
import sys

loggers = list()

def get_logger(name):
    target_logger = None
    for logger in loggers:
        if logger['name'] == name:
            target_logger = logger['object']
            break

    if target_logger is None:
        # create logger
        target_logger = logging.getLogger(name)
        target_logger.setLevel(logging.DEBUG)

        # create console handler and set level to debug
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(logging.DEBUG)

        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # add formatter to ch
        ch.setFormatter(formatter)

        # add ch to logger
        target_logger.addHandler(ch)

        loggers.append({'name':name,'object': target_logger})

    return target_logger
