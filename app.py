import argparse
import json
import logging
import math
import random
import sys
import time
from operator import truediv
from pathlib import Path

from flask import Flask, render_template
from flask_sock import Sock

from controllers.crazyflieController import CrazyflieController
from controllers.simulatedController import SimulatedController
from controllers.utils.utils import FlightZone
from points_helper import Point, read_from_file

logger = logging.getLogger(__name__)

app = Flask(__name__)
sock = Sock(app)

# Destinations have a name, easy_location, hard_location
destinations = []


NUM_TRIALS = 10
DRONE_URI = 'radio://0/80/2M/E7E7E7E7E0'
MOVE_DISTANCE = 0.10
FLIGHT_ZONE = FlightZone(2.0, 3.0, 1.25, 0.3)


def move_home(cf):
    drone_position = cf.positions[DRONE_URI]
    drone_position[0] = -(drone_position[0])
    drone_position[1] = -(drone_position[1])
    drone_position[2] = 0

    cf.swarm_move({DRONE_URI: drone_position}, None, 2, True)


def send_data(sock, action, message, data_type='na'):
    sock.send(json.dumps({'action': action,
                          'type': data_type,
                          'message': message}))


def recieve_data(sock):
    data = sock.receive()

    logger.debug(data)

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

    send_data(sock,
              action='alert',
              message='Welcome! This is your first flight.')

    cf = SimulatedController({DRONE_URI}, FLIGHT_ZONE, DRONE_URI)

    experiment_trial = 0
    score = 0

    start_time = time.time()
    start_time_action = time.time()

    while experiment_trial < NUM_TRIALS:
        data = recieve_data(sock)

        # Log movement
        logger.info(f"{data}")

        action = data['action']

        if action == 'failed trial':
            # if the participant ran out of time, move to next trial
            move_home(cf)
            experiment_trial += 1

            # TODO: mark in participant .csv that the trial was failed

            continue

        if cf.swarm_flying:
            if action == 'move':
                direction = data['direction']

                if direction == 'forward':
                    cf.swarm_move({DRONE_URI: [MOVE_DISTANCE, 0, 0]},
                                  None,
                                  2.,
                                  True)
                elif direction == 'back':
                    cf.swarm_move({DRONE_URI: [-MOVE_DISTANCE, 0, 0]},
                                  None,
                                  2.,
                                  True)
                elif direction == 'left':
                    cf.swarm_move({DRONE_URI: [0, MOVE_DISTANCE, 0]},
                                  None,
                                  2.,
                                  True)
                elif direction == 'right':
                    cf.swarm_move({DRONE_URI: [0, -MOVE_DISTANCE, 0]},
                                  None,
                                  2.,
                                  True)
                else:
                    raise RuntimeError("Unknown direction: " + direction)
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
                raise RuntimeError("Illegal action: " + action)

        else:

            # if drone has not taken off

            if action == 'take off':
                cf.swarm_take_off()
            elif action == 'move':
                send_data(sock,
                          action='alert',
                          data_type='no takeoff',
                          message='Please take off before attempting to move!')
            else:
                raise RuntimeError("Illegal action: " + action)

    send_data(sock,
              action='alert',
              message='Destination reached! Well done! Going back to homebase.')


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

    parser.add_argument('-p',
                        '--points-file',
                        dest='pointsFile',
                        type=Path,
                        default='points.bin',
                        help='The generated file with points to use')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.INFO,
                        handlers=[logging.FileHandler(args.logFile), logging.StreamHandler(sys.stdout)])

    app.config['condition'] = args.condition
    app.config['id'] = args.id

    destinations = read_from_file(args.pointsFile)

    # TODO: Create .csv file for each participant with name <id>.csv

    app.run()
