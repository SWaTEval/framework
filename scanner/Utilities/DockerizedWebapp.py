import time
from socket import socket

import docker
import requests
from omegaconf import OmegaConf


class DockerizedWebapp:
    """
    Wrapper for the dockerized webapp
    """

    def __init__(self, batch_name):
        config = OmegaConf.load('config.yaml')
        vuln_app_config_section = config['vulnerable_web_app']

        self._docker_image = vuln_app_config_section['docker_image']
        self._container_name = vuln_app_config_section['docker_image'] + '_' + batch_name
        self._app_port = vuln_app_config_section['app_port']
        self._app_scheme = vuln_app_config_section['app_scheme']

    def start(self):
        client = docker.from_env()
        bind_to = self._find_free_port('127.0.0.1')
        container = client.containers.run(image=self._docker_image,
                                          name=self._container_name,
                                          ports={self._app_port: bind_to},
                                          detach=True)
        container.reload()
        self._app_address = f'{self._app_scheme}://localhost:{bind_to}'
        return self._app_address

    def stop(self):
        client = docker.from_env()
        container = client.containers.get(self._container_name)
        container.stop()
        container.remove()

    def get_address(self):
        return self._app_address

    @staticmethod
    def _find_free_port(host: str):
        # https://stackoverflow.com/questions/2838244/get-open-tcp-port-in-python
        s = socket()
        s.bind((host, 0))
        return s.getsockname()[1]