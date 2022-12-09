cd ..
python main.py --replace \
max_revisits=1\

endpoint_detector.distance_type=tlsh\
endpoint_detector.field_for_distance=hash\
workers.endpoint_detector_module=scanner.Detection.ClusteringBased.EndpointDetector\

state_change_detector.distance_type=hash2vec\
state_change_detector.field_for_distance=hash\
workers.state_change_detector_module=scanner.Detection.ClusteringBased.StateChangeDetector\

state_detector.distance_type=hash2vec\
state_detector.field_for_distance=hash\
workers.state_detector_module=scanner.Detection.ClusteringBased.StateDetector\

random_seed=3\