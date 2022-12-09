from experiment_runner import run_experimetns
from clear_mongo_db_whole import clear_whole_db
from export_mongo_db_whole import export_whole_db
import random

if __name__ == '__main__':
    seeds = [2, 1, 4, 20, 2, 19, 4, 3, 16, 20, 13, 17, 14, 20, 4, 20, 6, 13, 10, 14]
    experiment_run_count = 20
    for experiment_run in range(experiment_run_count):
        print(f'Experiment run {experiment_run}')
        run_experimetns(seeds[experiment_run])
        export_whole_db(f'experiments/{experiment_run}')
        clear_whole_db()
