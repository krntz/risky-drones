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


NUM_TRIALS = 10
DRONE_URI = 'radio://0/80/2M/E7E7E7E7E0'
MOVE_DISTANCE = 0.10
FLIGHT_ZONE = FlightZone(2.0, 3.0, 1.25, 0.3)
BASE_SCORE = 10
GOAL_MARGIN = 0.5  # radius (in m) around a goal considered "valid"

DATA_FOLDER = 'participant-data'
DATA_FIELDNAMES = ['Participant ID',
                   'Condition',
                   'Trial',
                   'Score',
                   'Avg. time per action',
                   'Time to complete trial',
                   'Closest goal']


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


def write_row_to_csv(experiment_trial,
                     score,
                     trial_time,
                     closest_goal):
    row = {'Participant ID': app.config['id'],
           'Condition': app.config['condition'],
           'Trial': experiment_trial,
           'Score': score,
           'Avg. time per action': None,
           'Time to complete trial': trial_time,
           'Closest goal': closest_goal}

    with open('{}/performance-data/{}.csv'.format(DATA_FOLDER, app.config['id']), 'w+', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=DATA_FIELDNAMES)

        writer.writerow(row)


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

                    closest_goal = None

                    try:
                        for row in destinations:
                            for goal in row:
                                distance_to_current_goal = cf.distance_to_2D_point(
                                    DRONE_URI, goal.position)

                                drone_in_goal = distance_to_current_goal < GOAL_MARGIN

                                if drone_in_goal:
                                    closest_goal = goal
                                    new_score = BASE_SCORE * goal.difficulty_modifier

                                    send_message(sock,
                                                 action='alert',
                                                 data="You've gained {} points! Moving drone back to home.".format(new_score))

                                    # no need to continue searching
                                    # when we've found the closest goal

                                    raise StopIteration()

                                distance_to_old_goal = cf.distance_to_2D_point(
                                    DRONE_URI, closest_goal.position)

                                if distance_to_current_goal < distance_to_old_goal:
                                    closest_goal = goal

                    except StopIteration:
                        pass

                    if new_score < 0:
                        send_message(sock,
                                     action='alert',
                                     data="You've lost {} points! Moving drone back to home.".format(abs(new_score)))

                    score += new_score
                    send_message(sock,
                                 action='score',
                                 data=score)

                    write_row_to_csv(experiment_trial,
                                     score,
                                     trial_time,
                                     closest_goal.label)

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

    parser.add_argument('-l',
                        '--log-folder',
                        dest='logFolder',
                        default='{}/logs/'.format(DATA_FOLDER),
                        help='Folder into which to write the log. Default = {}/logs'.format(DATA_FOLDER))

    parser.add_argument('-g',
                        '--goal-file',
                        dest='goalsFile',
                        type=Path,
                        default='goals.bin',
                        help='The generated file with goals to use')

    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.INFO,
                        handlers=[logging.FileHandler('{}/{}.log'.format(args.logFolder, args.id)), logging.StreamHandler(sys.stdout)])

    logging.info('Log for participant with ID {} is stored in {}{}.log'.format(
        args.id, args.logFolder, args.id))

    app.config['condition'] = args.condition
    app.config['id'] = args.id

    try:
        destinations = read_from_file(args.goalsFile)
    except FileNotFoundError:
        logger.info("Could not find file {}".format(args.goalsFile))
        quit()

    with open('{}/{}.csv'.format(DATA_FOLDER, args.id), 'w+', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=DATA_FIELDNAMES)
        writer.writeheader()

    app.run()
