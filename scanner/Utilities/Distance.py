from typing import List

import Levenshtein
import textdistance
import tlsh
from omegaconf import ListConfig
from pandas import DataFrame
from tqdm import tqdm


class Distance:
    """
    A wrapper class for has distance calculation and distance matrix generation
    """
    _distance_implementations = dict()

    @classmethod
    def __init__(cls):
        # Define a dict containing the distance types and a reference to their implementation
        # so that we can select it at runtime
        cls._distance_implementations = {
            'levenshtein': Levenshtein.distance,
            'tlsh': tlsh.diff,
            'jaro-winkler-inverted': cls._jaro_winkler_inverted,
            'hamming': textdistance.hamming,
            'mlipns': cls._mlipns_inverted,
            'damerau_levenshtein': textdistance.damerau_levenshtein

            # Those under come from bioinformatics and give a weird output
            # TODO: Read more about them and check if they could be used
            # 'gotoh': textdistance.gotoh,
            # 'needleman-wunsch': textdistance.needleman_wunsch,
            # 'smith-waterman': textdistance.smith_waterman,
        }

    @classmethod
    def calculate(cls, input1: str, input2: str, distance_type: str):
        """
        Calculates the distance between two hashes

        :param hash1: First hash string
        :type hash1: str

        :param hash2: Second hash string
        :type hash2: str

        :param distance_type: Distance type name ('levenshtein','tlsh','jaro-winkler-inverted','hamming','mlipns' or 'damerau_levenshtein')
        :type distance_type: str

        """
        distance_function = cls._distance_implementations.get(distance_type)
        return distance_function(input1, input2)

    @classmethod
    def get_distance_types(cls):
        """
        :return: All available distance type names
        :rtype: List[str]
        """
        return list(cls._distance_implementations.keys())

    @classmethod
    def generate_distance_matrix(cls,
                                 data_query: List[dict],
                                 distance_type: str,
                                 field_for_index: str = None,
                                 field_for_distance="hash"):
        """
        Generates a distance matrix for a given data query. The query is expected to be a dict and by default is searched
        for a 'hash' key, which is then used as an input for the distance calculation. The field can be changed using the
        field_for_distance parameter.

        :param data_query: A list of dicts, which contain a 'hash' attribute
        :type data_query: List[dict]

        :param distance_type: Name of the distance type
        :type distance_type: str

        :param field_for_index: Name of the key that will be used as index for the distance matrix (Use None for arbitrary index)
        :type field_for_index: str

        :param field_for_distance: Name of the key that will be used as input for the distance calculation
        :type field_for_distance: str or list

        :return: A square matrix containing the pairwise distances.
        :rtype: pandas.DataFrame
        """
        distance_matrix = []
        interaction_ids = []

        for query in tqdm(data_query):
            # for query in data_query:
            if field_for_index is not None:
                interaction_id = str(query[field_for_index])
                interaction_ids.append(interaction_id)

            # OmegaConf parsed case: Cast ListConfig to List
            if isinstance(field_for_distance, ListConfig):
                field_for_distance = list(field_for_distance)

            # Parse field for distance if it's nested in the data query
            if isinstance(field_for_distance, list):
                keys = field_for_distance
                sub_section = query
                for key in keys:
                    sub_section = sub_section[key]
                data_for_distance_calculation = sub_section
            elif isinstance(field_for_distance, str):
                data_for_distance_calculation = query[field_for_distance]
            else:
                raise TypeError("field_for_distance must be str or list")

            current_distance_array = []
            for secondary_interaction_query in data_query:

                if isinstance(field_for_distance, list):
                    sub_section = secondary_interaction_query
                    for key in keys:
                        sub_section = sub_section[key]
                    secondary_data_for_distance_calculation = sub_section
                elif isinstance(field_for_distance, str):
                    secondary_data_for_distance_calculation = secondary_interaction_query[field_for_distance]
                else:
                    raise TypeError("field_for_distance must be str or list")

                distance = cls.calculate(input1=data_for_distance_calculation,
                                         input2=secondary_data_for_distance_calculation,
                                         distance_type=distance_type)

                current_distance_array.append(distance)
            distance_matrix.append(current_distance_array)

        if field_for_index is not None:
            distance_matrix = DataFrame(distance_matrix, columns=interaction_ids, index=interaction_ids)
        else:
            distance_matrix = DataFrame(distance_matrix)

        return distance_matrix

    # Jaro-Winkler is a similarity metric, this is why we subtract it from one (i.e. convert to similarity to distance)
    # https://en.wikipedia.org/wiki/Jaro%E2%80%93Winkler_distance#:~:text=In%20computer%20science%20and%20statistics,edit%20distance%20between%20two%20sequences.&text=The%20original%20paper%20actually%20defined,distance%20%3D%201%20%E2%88%92%20similarity).
    @classmethod
    def _jaro_winkler_inverted(cls, hash1, hash2):
        return 1 - textdistance.jaro_winkler(hash1, hash2)

    # MLIPNS seems also to be a similarity metric
    # Paper: https://www.sial.iias.spb.su/files/386-386-1-PB.pdf
    @classmethod
    def _mlipns_inverted(cls, hash1, hash2):
        return 1 - textdistance.mlipns(hash1, hash2)
