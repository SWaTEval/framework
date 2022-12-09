import logging
import bson
from bson import ObjectId
from flask import Flask, jsonify, request

from main import run
from scanner.Dataclasses.Endpoint import Endpoint
from scanner.Dataclasses.State import StateReachabilityInfo
from scanner.Utilities.KillableThread import KillableThread
from scanner.Utilities.MongoHelper import MongoHelper

import time
log = logging.getLogger('werkzeug')
#log.setLevel(logging.ERROR)

app = Flask(__name__)

mongo_helper: MongoHelper = None
scanner_thread: KillableThread = None

@app.route("/start", methods=["POST"])
def start_crawler():
    global scanner_thread, mongo_helper
    if not scanner_thread or scanner_thread.killed:
        batch_name = request.json['batch_name']
        target_url = request.json['target_url']

        mongo_helper = MongoHelper(for_batch=batch_name)
        scanner_thread = KillableThread(target=run, args=(batch_name, target_url,))
        scanner_thread.start()
        status = jsonify({'status': 'Started',
                          })
    else:
        batch_name = mongo_helper.get_batch_name()
        status = jsonify({'status': 'Already running',
                          'batch_name': batch_name,
                          })
    return status


@app.route("/stop")
def stop_crawler():
    global scanner_thread
    if scanner_thread:
        scanner_thread.kill()
        scanner_thread = None
        status = jsonify({'status': 'Killed'})
    else:
        status = jsonify({'status': 'Already stopped'})
    return status


@app.route("/endpoints")
def endpoints():
    global mongo_helper

    endpoints_collection = mongo_helper.get_endpoints_collection()

    available = endpoints_collection.count_documents({'allow_visit': True, 'clean': True})
    visited = endpoints_collection.count_documents({'visited': True})

    output = {'available': available, 'visited': visited}
    return jsonify(output)


@app.route("/interactions")
def interactions():
    global mongo_helper

    interactions_collection = mongo_helper.get_interactions_collection()
    count = interactions_collection.count_documents({})
    output = {'count': count}
    return jsonify(output)


@app.route("/state_graph")
def state_graph():
    global mongo_helper

    states_collection = mongo_helper.get_states_collection()
    interactions_collection = mongo_helper.get_interactions_collection()
    states_query = states_collection.find({'collapsed': False})

    nodes = []
    edges = []

    initial_state_id = mongo_helper.get_initial_state_id()
    initial_state_label = 'Initial state'
    current_state_id = mongo_helper.get_current_state_id()

    for state_query in states_query:
        state_id = str(state_query['_id'])
        previous_state_id = str(state_query['previous_state_id'])

        if initial_state_id == state_id:
            node_label = initial_state_label
        else:
            node_label = state_id

        nodes.append({"id": state_id, "label": node_label})

        causing_interaction_id = state_query['caused_by_interaction_id']
        try:
            causing_interaction_id = ObjectId(causing_interaction_id)
        except bson.errors.InvalidId:
            continue

        causing_interaction_query = interactions_collection.find_one({'_id': causing_interaction_id})

        if causing_interaction_query is not None:
            interaction_endpoint = Endpoint.from_dict(causing_interaction_query['request']['endpoint'])
            before = previous_state_id
            after = state_id
            label = interaction_endpoint.method + " " + \
                    interaction_endpoint.path + \
                    interaction_endpoint.parameters_as_string

            edges.append({"from": before,
                          "to": after,
                          "label": label,
                          "length": 300,
                          "font": {"align": "horizontal"},
                          "arrows": "to"})

    states_query = states_collection.find({'collapsed': False})

    # Add state reachability
    for state_query in states_query:
        for reachability_info in state_query['reachable_from']:
            state_reachability: StateReachabilityInfo = StateReachabilityInfo.from_dict(reachability_info)
            before = state_reachability.from_state_id
            after = str(state_query['_id'])
            interaction_query = interactions_collection.find_one(
                {'_id': ObjectId(state_reachability.caused_by_interaction_id)})
            interaction_endpoint = Endpoint.from_dict(interaction_query['request']['endpoint'])
            label = interaction_endpoint.method + " " + \
                    interaction_endpoint.path + " " + \
                    interaction_endpoint.parameters_as_string

            label = label[:-1]

            edges.append({"from": before,
                          "to": after,
                          "label": label,
                          "length": 300,
                          "font": {"align": "horizontal"},
                          "arrows": "to"})

    output = {'nodes': nodes, 'edges': edges, 'current_state_id': current_state_id}
    return jsonify(output)


# TODO: Remove this in future
# Allow cors for every request
@app.after_request
def after_request(response):
    header = response.headers
    header['Access-Control-Allow-Origin'] = '*'
    header['Access-Control-Allow-Headers'] = '*'
    return response

