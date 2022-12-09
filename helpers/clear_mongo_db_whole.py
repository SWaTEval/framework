import os
import sys
sys.path.insert(0, '..') # Allow relative imports

import confuse
from pymongo import MongoClient

os.chdir("..") # Navigate to the upper directory (needed for reading the config file)

def clear_whole_db():
    config = confuse.Configuration('modular-state-aware-crawler')
    config.set_file('config.yaml')
    mongo_credentials_section = config['mongo_db_credentials'].get()

    username = mongo_credentials_section['username']
    password = mongo_credentials_section['password']
    host = mongo_credentials_section['mongo_host']
    port = mongo_credentials_section['mongo_port']

    client = MongoClient(host=host,port=port,username=username,password=password)

    dbs = client.list_database_names()
    dbs.remove('admin')
    for db in dbs:
        client.drop_database(db)

if __name__ == '__main__':
    clear_whole_db()
