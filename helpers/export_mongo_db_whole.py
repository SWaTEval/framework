from configparser import ConfigParser
import shutil
from bson.json_util import dumps, loads
from pymongo import MongoClient
import os
import json

 ##### Parse config ######
host = "mongo.docker"
port = 27017


endpoints_db_name = 'endpoints'
interactions_db_name = 'interactions'
states_db_name = 'states'
endpoint_clustering_db_name = 'endpoint_clustering'
interaction_clustering_db_name = 'interaction_clustering'

####### Export data ######
client = MongoClient(host=host,port=port)
# Check server connection
try:
    client.server_info()
except:
    raise ConnectionError("Something went wrong when trying to connect to mongo host")


def export_whole_db(root_dir):
    all_batches = client['experiments'].list_collection_names()

    os.makedirs(root_dir, exist_ok=True)
    os.chdir(root_dir)

    for batch_name in all_batches:
        os.makedirs(batch_name)
        os.chdir(batch_name)
        collections_to_export = dict()
        collections_to_export["endpoints"] = client[endpoints_db_name][batch_name]
        collections_to_export["interactions"] = client[interactions_db_name][batch_name]
        collections_to_export["states"] = client[states_db_name][batch_name]
        collections_to_export["endpoint_clustering"] = client[endpoint_clustering_db_name][batch_name]
        collections_to_export["interaction_clustering"] = client[interaction_clustering_db_name][batch_name]
        collections_to_export["experiments"] = client['experiments'][batch_name]

        output_folder = 'mongo_data'
        path = os.path.join(os.getcwd(), output_folder)

        if os.path.exists(path):
            if input(f"There is a folder called {output_folder}. Do you want to replace it's content? (y/n)") != "y":
                print("Operation canceled")
                exit()
            shutil.rmtree(path)

        os.makedirs(path)

        for db_name, collection in collections_to_export.items():
            cursor = collection.find({})
            export_path = os.path.join(os.getcwd(), output_folder, f'{db_name}.json')
            with open(export_path, 'w') as file:
                data = json.loads(dumps(cursor))
                json.dump(data, file)

        os.chdir('..')
    os.chdir('../..')

if __name__ == '__main__':
    root_dir = input("Give a name of the root dir where data is going to be saved: ")
    export_whole_db(root_dir)
