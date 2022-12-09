import argparse
import time
from urllib.parse import urlparse

from omegaconf import OmegaConf

from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Dataclasses.State import State
from scanner.Utilities.DockerizedWebapp import DockerizedWebapp
from scanner.Utilities.Logging import get_logger
from scanner.Utilities.MongoHelper import MongoHelper
from scanner.Utilities.Util import get_hash_padding, set_config
from scanner.Work.WorkManager import WorkManager

ignore_endpoints = []


def init_evaluation_framework(batch_name, config):
    mongo_helper = MongoHelper(batch_name)

    export_config = dict(config)
    export_config['hash_padding'] = get_hash_padding(export_config['random_seed'])
    mongo_helper.add_params(export_config)

    app = DockerizedWebapp(batch_name=batch_name)
    app.start()
    app_address = urlparse(app.get_address())

    host = app_address.netloc
    scheme = app_address.scheme

    initial_state = State(previous_state_id="No previous state",
                          caused_by_interaction_id="No interaction",
                          initial=True,
                          current=True)

    initial_state_id = mongo_helper.add_state(initial_state)

    # Add initial endpoints to db
    initial_endpoint = Endpoint(host=host,
                                path='/views/home',
                                state_id=initial_state_id,
                                clean=True,
                                scheme=scheme,
                                from_interaction_id="User defined")

    state_machine_reset_endpoint = Endpoint(host=host,
                                            path='/views/state/reset',
                                            state_id=initial_state_id,
                                            clean=True,
                                            method="GET",
                                            is_reset=True,
                                            scheme=scheme,
                                            from_interaction_id="User defined")
    global ignore_endpoints
    ignore_endpoints.append(state_machine_reset_endpoint)

    mongo_helper.add_endpoint(initial_endpoint)
    mongo_helper.add_endpoint(state_machine_reset_endpoint)
    return app

def parse_conf_replace_cli():
    # Load config
    config = OmegaConf.load('config.yaml')

    # Replace existing
    parser = argparse.ArgumentParser()
    parser.add_argument('--replace', required=False, nargs='+')

    args = parser.parse_args()
    if args.replace is not None:
        cli_conf = OmegaConf.from_dotlist(args.replace)
        config.merge_with(cli_conf)

    return config


def run(batch_name):
    config = parse_conf_replace_cli()
    set_config(dict(config))
    workers_config = config['workers']

    logger = get_logger('Main')
    logger.info("Intializing app")
    app = init_evaluation_framework(batch_name=batch_name, config=config)
    logger.info(f"App address: {app.get_address()}")

    manager = WorkManager(execution_type=workers_config['execution_type'])

    manager.create_work(for_worker='crawler',
                        module_name=workers_config['crawler_module'],
                        class_name=workers_config['crawler_class'],
                        for_batch=batch_name,
                        config=config)

    manager.create_work(for_worker='DummyFuzzer',
                        module_name='scanner.ExternalScanners.EvaluationFrameworkDummyFuzzer',
                        class_name='EvaluationFrameworkDummyFuzzer',
                        for_batch=batch_name,
                        app_address=app.get_address())

    global ignore_endpoints
    manager.create_work(for_worker='endpoint_extractor',
                        module_name=workers_config['endpoint_extractor_module'],
                        class_name='EndpointExtractor',
                        for_batch=batch_name,
                        ignore_endpoints=ignore_endpoints,
                        config=config)

    manager.create_work(for_worker='endpoint_detector',
                        module_name=workers_config['endpoint_detector_module'],
                        class_name='EndpointDetector',
                        for_batch=batch_name,
                        config=config)

    manager.create_work(for_worker='state_change_detector',
                        module_name=workers_config['state_change_detector_module'],
                        class_name='StateChangeDetector',
                        for_batch=batch_name,
                        config=config)

    manager.create_work(for_worker='state_detector',
                        module_name=workers_config['state_detector_module'],
                        class_name='StateDetector',
                        for_batch=batch_name,
                        config=config)

    manager.get_work_done()
    logger.info('Stopping app container')
    app.stop()


if __name__ == "__main__":
    timestamp = str(int(time.time()))
    run(batch_name=timestamp)
