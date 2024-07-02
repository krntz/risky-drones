import argparse
import json
import logging
import math
import random
import sys
import time
from operator import truediv

from flask import Flask, render_template
from flask_sock import Sock

from controllers.crazyflieController import CrazyflieController
from controllers.simulatedController import SimulatedController
from controllers.utils.utils import FlightZone

logger = logging.getLogger(__name__)

app = Flask(__name__)
sock = Sock(app)


class Destination:
    def __init__(self, name, easy_location, hard_location, default_location):
        self.name = name
        self.easy_location = easy_location
        self.hard_location = hard_location
        self.default_location = default_location


# Destinations have a name, easy_location, hard_location
destinations = [
    Destination("A", [0.60, 0.3, .5], [0.6, -0.3, .5], [1., 0, 0.5]),
    Destination("D", [0.3, -0.6, .5], [-0.3, -0.6, .5], [0, -1.0, .5]),
    Destination("B", [-0.6, 0.60, .4], [0.3, 0.6, .5], [0, 1., .5]),
    Destination("C", [-0.6, -0.3, .5], [-0.6, 0.3, .5], [-1., 0.0, .5])
]

score = 0  # participant's total score

num_trials = 10


def move_home():
    drone_position = cf.positions[drone_uri]
    drone_position[0] = -(drone_position[0])
    drone_position[1] = -(drone_position[1])
    drone_position[2] = 0

    cf.swarm_move({drone_uri: drone_position}, None, 2, True)


def recieve_data(sock):
    data = sock.receive()

    if isinstance(data, str):
        json_data = json.loads(data)

        if 'action' in json_data:
            return json_data
        else:
            raise Exception("Recieved data is not in expected format!")
    else:
        raise Exception("Recieved data is not string!")


@app.route('/')
def index():
    return render_template('index.html')


@sock.route('/action')
def echo(sock):
    global score
    global goal_reached

    sock.send(json.dumps({
        'action': 'welcome',
        'message': 'Welcome! This is your first flight.'
    }))

    move_distance = 0.10

    drone_uri = 'radio://0/80/2M/E7E7E7E7E0'
    flight_zone = FlightZone(2.0, 3.0, 1.25, 0.3)
    cf = SimulatedController({drone_uri}, flight_zone, drone_uri)

    experiment_trial = 0

    start_time = time.time()
    start_time_action = time.time()

    while experiment_trial < num_trials:
        data = recieve_data(sock)

        # Log movement
        logger.info(f"{data}")

        action = data['action']

        if action == 'failed trial':
            # if the participant ran out of time, move to next trial
            experiment_trial += 1

            # TODO: mark in participant .csv that the trial was failed

            continue

        if cf.swarm_flying:
            if action == 'move':
                direction = data['direction']

                if direction == 'forward':
                    cf.swarm_move({drone_uri: [move_distance, 0, 0]},
                                  None,
                                  2.,
                                  True)
                elif direction == 'back':
                    cf.swarm_move({drone_uri: [-move_distance, 0, 0]},
                                  None,
                                  2.,
                                  True)
                elif direction == 'left':
                    cf.swarm_move({drone_uri: [0, move_distance, 0]},
                                  None,
                                  2.,
                                  True)
                elif direction == 'right':
                    cf.swarm_move({drone_uri: [0, -move_distance, 0]},
                                  None,
                                  2.,
                                  True)
            elif action == 'land':
                # TODO:
                # 1. land drone
                # 2. check if the drone is inside a point
                #    a. if drone is inside the closest point, increase score
                #    b. if drone is not inside closest point
                #      A. decrease score
                #      B. find which point it's closest to
                # 3. send score update to front end
                # 4. show message on front end
                # 5. move drone back to home
                # 6. start next trial

                # TODO: Store participant score, time to complete, and
                # avg. time per action for each trial

                cf.swarm_land()

        else:

            # if drone has not taken off

            if action == 'take off':
                cf.swarm_take_off()

    sock.send(json.dumps(
        {'action': 'finish', 'message': 'Destination reached! Well done! Going back to homebase.'}))


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="Runs the risky drones experiment")

    parser.add_argument('-c',
                        '--condition',
                        dest='condition',
                        required=True,
                        choices=['control', 'fail'],
                        help='Which experimental condition to run')

    parser.add_argument('-i',
                        '--id',
                        help='The id of the current participant')

    parser.add_argument('-l',
                        '--log-file',
                        dest='logFile',
                        default='movements.log',
                        help='File into which to write the log')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.INFO,
                        handlers=[logging.FileHandler(args.logFile), logging.StreamHandler(sys.stdout)])

    app.config['condition'] = args.condition
    app.config['id'] = args.id

    # TODO: Create .csv file for each participant with name <id>.csv

    app.run()
