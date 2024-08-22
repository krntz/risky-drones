import argparse
import csv
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
from goals_helper import read_from_file

logger = logging.getLogger(__name__)

app = Flask(__name__)
sock = Sock(app)

# Destinations have a name, easy_location, hard_location
destinations = []

SCORE = 0

NUM_TRIALS = 10
DRONE_URI = 'radio://0/80/2M/E7E7E7E7E0'
MOVE_DISTANCE = 0.10
FLIGHT_ZONE = FlightZone(2.0, 3.0, 1.25, 0.3)
BASE_SCORE = 10
GOAL_MARGIN = 0.5  # radius (in m) around a goal considered "valid"

DATA_FOLDER = Path('./data')
PARTICIPANT_DATA_FOLDER = DATA_FOLDER / 'performance-data'
LOG_FOLDER = DATA_FOLDER / 'logs'

DATA_FIELDNAMES = ['Participant ID',
                   'Condition',
                   'Trial',
                   'Score',
                   'Avg. time per action',
                   'Time to complete trial',
                   'Closest goal']


def move_home(cf):
    if not cf.swarm_flying:
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


def update_score(sock, score_update):
    global SCORE

    SCORE += score_update

    send_message(sock,
                 action='score',
                 data=SCORE)


def write_row_to_csv(experiment_trial,
                     trial_time,
                     closest_goal):
    row = {'Participant ID': app.config['id'],
           'Condition': app.config['condition'],
           'Trial': experiment_trial,
           'Score': SCORE,
           'Avg. time per action': None,
           'Time to complete trial': trial_time,
           'Closest goal': closest_goal}

    participant_file = (PARTICIPANT_DATA_FOLDER /
                        app.config['id']).with_suffix('.csv')
    with participant_file.open(mode='a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=DATA_FIELDNAMES)

        writer.writerow(row)


@app.route('/')
def index():
    return render_template('index.html')


@sock.route('/action')
def echo(sock):
    send_message(sock,
                 action='alert',
                 data='Welcome! This is your first flight.')

    cf = SimulatedController({DRONE_URI}, FLIGHT_ZONE, DRONE_URI)

    experiment_trial = 0

    while experiment_trial < NUM_TRIALS:

        data = recieve_message(sock)

        action = data['action']

        if action == 'out of time':
            trial_time = stop_trial_timer(sock, trial_start)

            score_update = -BASE_SCORE

            update_score(sock, score_update)

            message = "You've run out of time, you've lost {} points! Moving drone back to home.".format(
                abs(score_update))

            send_message(sock, 'alert', message)

            closest_goal = (math.inf, None)

            for row in destinations:
                for goal in row:
                    distance_to_current_goal = cf.distance_to_2D_point(DRONE_URI,
                                                                       goal.position)

                    distance_to_old_goal = closest_goal[0]

                    if distance_to_current_goal < distance_to_old_goal:
                        closest_goal = (distance_to_current_goal, goal)

            write_row_to_csv(experiment_trial,
                             trial_time,
                             closest_goal[1].label)

            # if the participant ran out of time, move to next trial
            move_home(cf)
            experiment_trial += 1

            continue

        if cf.swarm_flying:
            match action:
                case 'move':
                    direction = data['direction']

                    logger.info("Moving {}".format(direction))

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
                    trial_time = stop_trial_timer(sock, trial_start)

                    cf.swarm_land()

                    new_score = -BASE_SCORE

                    closest_goal = (math.inf, None)

                    try:
                        for row in destinations:
                            for goal in row:
                                distance_to_current_goal = cf.distance_to_2D_point(
                                    DRONE_URI, goal.position)

                                drone_in_goal = distance_to_current_goal < GOAL_MARGIN

                                if drone_in_goal:
                                    closest_goal = (distance_to_current_goal,
                                                    goal)
                                    new_score = BASE_SCORE * goal.difficulty_modifier

                                    send_message(sock,
                                                 action='alert',
                                                 data="You've gained {} points! Moving drone back to home.".format(new_score))

                                    # no need to continue searching
                                    # when we've found the closest goal

                                    raise StopIteration()

                                distance_to_old_goal = closest_goal[0]

                                if distance_to_current_goal < distance_to_old_goal:
                                    closest_goal = (distance_to_current_goal,
                                                    goal)

                    except StopIteration:
                        pass

                    if new_score < 0:
                        send_message(sock,
                                     action='alert',
                                     data="You've lost {} points! Moving drone back to home.".format(abs(new_score)))

                    update_score(sock, new_score)

                    write_row_to_csv(experiment_trial,
                                     trial_time,
                                     closest_goal[1].label)

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
                        required=True,
                        help='The id of the current participant')

    parser.add_argument('-g',
                        '--goal-file',
                        dest='goalsFile',
                        type=Path,
                        default='goals.bin',
                        help='The generated file with goals to use')

    args = parser.parse_args()

    PARTICIPANT_DATA_FOLDER.mkdir(parents=True, exist_ok=True)
    LOG_FOLDER.mkdir(parents=True, exist_ok=True)

    log_file = (LOG_FOLDER / args.id).with_suffix('.csv')

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.INFO,
                        handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)])

    app.config['condition'] = args.condition
    app.config['id'] = args.id

    try:
        destinations = read_from_file(args.goalsFile)
    except FileNotFoundError:
        logger.info("Could not find goal file {}".format(args.goalsFile))
        quit()

    participant_file = (PARTICIPANT_DATA_FOLDER / args.id).with_suffix('.csv')

    with participant_file.open(mode='w', newline='') as csvfile:
        logger.info("Creating new participant file {}".format(participant_file))
        writer = csv.DictWriter(csvfile, fieldnames=DATA_FIELDNAMES)
        writer.writeheader()

    app.run()
