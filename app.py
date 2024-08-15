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
BASE_SCORE = 10
POINT_MARGIN = 0.5  # radius (in m) around a point considered "valid"


def move_home(cf):
    cf.swarm_take_off()

    drone_position = cf.positions[DRONE_URI]
    drone_position[0] = -(drone_position[0])
    drone_position[1] = -(drone_position[1])
    drone_position[2] = 0

    cf.swarm_move({DRONE_URI: drone_position}, None, 2, True)

    cf.swarm_land()


def send_message(sock, action, data, data_type='na'):
    sock.send(json.dumps({'action': action,
                          'type': data_type,
                          'data': data}))


def recieve_message(sock):
    data = sock.receive()

    if isinstance(data, str):
        json_data = json.loads(data)

        if 'action' in json_data:
            return json_data
        else:
            raise Exception("Recieved data is not in expected format!")
    else:
        raise Exception("Recieved data is not string!")


def start_trial_timer(sock):
    send_message(sock,
                 action='timer',
                 data='start')

    return time.time()


def stop_trial_timer(sock, start_time):
    send_message(sock,
                 action='timer',
                 data='stop')

    return time.time() - start_time


@app.route('/')
def index():
    return render_template('index.html')


@sock.route('/action')
def echo(sock):
    global score
    global goal_reached

    send_message(sock,
                 action='alert',
                 data='Welcome! This is your first flight.')

    cf = SimulatedController({DRONE_URI}, FLIGHT_ZONE, DRONE_URI)

    experiment_trial = 0
    score = 0

    while experiment_trial < NUM_TRIALS:

        data = recieve_message(sock)

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
            match action:
                case 'move':
                    direction = data['direction']

                    match direction:
                        case 'forward':
                            cf.swarm_move({DRONE_URI: [MOVE_DISTANCE, 0, 0]},
                                          None,
                                          2.,
                                          True)
                        case 'back':
                            cf.swarm_move({DRONE_URI: [-MOVE_DISTANCE, 0, 0]},
                                          None,
                                          2.,
                                          True)
                        case 'left':
                            cf.swarm_move({DRONE_URI: [0, MOVE_DISTANCE, 0]},
                                          None,
                                          2.,
                                          True)
                        case 'right':
                            cf.swarm_move({DRONE_URI: [0, -MOVE_DISTANCE, 0]},
                                          None,
                                          2.,
                                          True)
                        case _:
                            raise RuntimeError(
                                "Unknown direction: " + direction)
                case 'land':
                    # TODO: Store participant score, time to complete, and
                    # avg. time per action for each trial

                    trial_time = stop_trial_timer(sock, trial_start)

                    cf.swarm_land()

                    new_score = -BASE_SCORE

                    for row in destinations:
                        for point in row:
                            drone_within_point = cf.distance_to_2D_point(
                                DRONE_URI, point.position) < POINT_MARGIN

                            if drone_within_point:
                                new_score = BASE_SCORE * point.difficulty_modifier

                                send_message(sock,
                                             action='alert',
                                             data="You've gained {} points! Moving drone back to home.".format(new_score))

                                # no need to continue searching
                                # when we've found the closest point

                                break

                    if new_score < 0:
                        send_message(sock,
                                     action='alert',
                                     data="You've lost {} points! Moving drone back to home.".format(abs(new_score)))

                    score += new_score
                    send_message(sock,
                                 action='score',
                                 data=score)

                    move_home(cf)

                    experiment_trial += 1

                case _:
                    raise RuntimeError("Illegal action: " + action)

        else:

            # if drone has not taken off

            match action:
                case 'take off':
                    trial_start = start_trial_timer(sock)
                    cf.swarm_take_off()
                case 'move':
                    send_message(sock,
                                 action='alert',
                                 data_type='no takeoff',
                                 data='Please take off before attempting to move!')
                case _:
                    raise RuntimeError("Illegal action: " + action)

    send_message(sock,
                 action='alert',
                 data='Destination reached! Well done! Going back to homebase.')


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
