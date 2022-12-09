import itertools

def create_experiments():
    all_experiments = list()
    max_revisits_options = [0] # List that defines the number of revisits

    ############# Clustering Based Experiments #############

    # Run on interaction's hash field for state detector

    # ---- Endpoint Cleaner Setup ----
    endpoint_detector_distance_types = list()
    endpoint_detector_distance_types.append('hash2vec')
    endpoint_detector_distance_types.append('tlsh')

    endpoint_detector_modules = list()
    endpoint_detector_modules.append("scanner.Detection.Basic.EndpointDetector")
    endpoint_detector_modules.append("scanner.Detection.ClusteringBased.EndpointDetector")

    # ---- State Detector Setup ----
    state_change_detector_distance_types = list()
    state_change_detector_distance_types.append('hash2vec')
    state_change_detector_distance_types.append('tlsh')

    state_change_detector_fields_for_distance = list()
    state_change_detector_fields_for_distance.append('hash')

    state_change_detector_modules = list()
    state_change_detector_modules.append("scanner.Detection.ClusteringBased.StateChangeDetector")

    # ---- State Collapser Setup ----
    state_detector_distance_types = list()
    state_detector_distance_types.append('hash2vec')
    state_detector_distance_types.append('tlsh')

    state_detector_modules = list()
    state_detector_modules.append("scanner.Detection.ClusteringBased.StateDetector")

    products = itertools.product(max_revisits_options,              #0
                                 endpoint_detector_distance_types,   #1
                                 endpoint_detector_modules,          #2
                                 state_change_detector_distance_types,     #3
                                 state_change_detector_modules,            #4
                                 state_change_detector_fields_for_distance,#5
                                 state_detector_distance_types,    #6
                                 state_detector_modules,           #7
                                 )

    all_experiments.extend(list(products))

    # Run on interaction's response data field for state detector
    # ---- Endpoint Cleaner Setup ----
    endpoint_detector_distance_types = list()
    endpoint_detector_distance_types.append('hash2vec')
    endpoint_detector_distance_types.append('tlsh')

    endpoint_detector_modules = list()
    endpoint_detector_modules.append("scanner.Detection.Basic.EndpointDetector")
    endpoint_detector_modules.append("scanner.Detection.ClusteringBased.EndpointDetector")

    # ---- State Detector Setup ----
    state_change_detector_distance_types = list()
    state_change_detector_distance_types.append('levenshtein')

    state_change_detector_fields_for_distance = list()
    state_change_detector_fields_for_distance.append("['response','data']")

    state_change_detector_modules = list()
    state_change_detector_modules.append("scanner.Detection.ClusteringBased.StateChangeDetector")

    # ---- State Collapser Setup ----
    state_detector_distance_types = list()
    state_detector_distance_types.append('hash2vec')
    state_detector_distance_types.append('tlsh')

    state_detector_modules = list()
    state_detector_modules.append("scanner.Detection.ClusteringBased.StateDetector")

    products = itertools.product(max_revisits_options,              #0
                                 endpoint_detector_distance_types,   #1
                                 endpoint_detector_modules,          #2
                                 state_change_detector_distance_types,     #3
                                 state_change_detector_modules,            #4
                                 state_change_detector_fields_for_distance,#5
                                 state_detector_distance_types,    #6
                                 state_detector_modules,           #7
                                 )

    all_experiments.extend(list(products))
    return all_experiments
