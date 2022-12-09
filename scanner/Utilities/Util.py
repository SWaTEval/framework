import random
import string
from typing import List

from pandas import DataFrame


def random_string(character_count: int = 200):
    """
    Random string generator

    :param character_count: Length of the generated string
    :type: int

    :return: Random string
    :rtype: str
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=character_count))


def get_hash_padding(seed):
    random.seed(seed)
    return random_string(200)


def extract_hashes(data_query: List[dict]):
    """
    A helper method that extracts the 'hash' field of a data query

    :param data_query: A list of dicts, which have a 'hash' attribute
    :type data_query: List[dict]

    :return: List of all hashes in the data query
    :rtype: List[str]
    """

    hashes = []
    for query in data_query:
        hashes.append(query['hash'])
    return hashes


def generate_hash2vec_dataset(hashes: List[str]):
    """
    A helper method creates a dataset from hashes split by characters and transformed to ascii integeres

    :param hashes: List of all hashes from which the dataset should be created
    :type hashes: List[str]

    :return: A numerical dataset created from the hashes
    :rtype: pandas.DataFrame
    """
    # Split hashes by character
    split_hashes = []
    for entry in hashes:
        split_hash = [char for char in entry]
        split_hashes.append(split_hash)

    # Create dataframe from hashes
    hash2vec_df = DataFrame(split_hashes)
    hash2vec_df = hash2vec_df.applymap(ord)

    return hash2vec_df


local_config = None


def set_config(config):
    global local_config
    local_config = config


def get_config():
    global local_config
    return local_config
