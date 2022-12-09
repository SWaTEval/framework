import sys
sys.path.insert(0, '..') # Allow relative imports

import subprocess
import sys

from experiment_creator import create_experiments


def run_experimetns(seed):
    experiments = create_experiments()
    experiment_count = len(experiments)

    # Run experiments
    for idx, product in enumerate(experiments):
        setup = f"random_seed={seed} "
        if product[0] is not None:
            setup += f"state_navigator.max_revisits={product[0]} "

        if product[1] is not None:
            setup += f"endpoint_detector.distance_type={product[1]} "
        if product[2] is not None:
            setup += f"workers.endpoint_detector_module={product[2]} "

        if product[3] is not None:
            setup += f"state_change_detector.distance_type={product[3]} "
        if product[4] is not None:
            setup += f"workers.state_change_detector_module={product[4]} "
        if product[5] is not None:
            setup += f"state_change_detector.field_for_distance={product[5]} "

        if product[6] is not None:
            setup += f"state_detector.distance_type={product[6]} "
        if product[7] is not None:
            setup += f"workers.state_detector_module={product[7]} "

        print(25*"===" + f"    Run {idx+1}/{experiment_count}    " + 25*"===" )

        command = f"python main.py --replace {setup}"
        command_as_list = command.split(' ')
        print(command)

        proc = subprocess.Popen(command_as_list, stdout=subprocess.PIPE, stderr=sys.stderr)
        for line in proc.stdout:
            line_str = line.decode('utf-8')
            sys.stdout.write(line_str)
        proc.communicate()

        print()
        
if __name__ == '__main__':
    seed = input("Please enter an integer seed for the TLSH padding generation")
    seed = int(seed)
    run_experimetns(seed)
