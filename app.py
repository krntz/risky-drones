import argparse
import json
import csv
import logging
import math
from pathlib import Path
import random
import statistics
import time

from urllib.parse import urlencode

from flask import Flask, render_template
from flask_sock import Sock

from controllers.crazyflieController import CrazyflieController
from controllers.simulatedController import SimulatedController
from controllers.utils.utils import FlightZone
from goals_helper import read_from_file
from participant_helper import Participant

logger = logging.getLogger(__name__)

app = Flask(__name__)
sock = Sock(app)

# Destinations have a name, easy_location, hard_location
destinations = []

DRONE_URI = "radio://0/80/2M/E7E7E7E7E0"
FLIGHT_ZONE = FlightZone(2.0, 3.0, 1.25, 0.3)

SCORE = 0
BASE_SCORE = 1

NUM_TRIALS = 10

BASE_MOVEMENT_DISTANCE = 0.25
MOVEMENT_RANGE = (0.1, 1.0)
MOVEMENT_STEPS = 0.1

GOAL_MARGIN = 0.15  # radius (in m) around a goal considered "valid"

DATA_FOLDER = Path("./data")
MOVEMENT_FOLDER = DATA_FOLDER / "movements"

DATA_FIELDNAMES = [
    "Participant ID",
    "Condition",
    "Trial",
    "Score",
    "Total Score",
    "Avg. time per action",
    "Time to complete trial",
    "Closest goal",
    "Drone position",
]


def is_point_in_circle(radius, point):
    # Check if the distance is less than or equal to the radius
    return math.sqrt(point[0] ** 2 + point[1] ** 2) <= radius


def move_home():
    logger.info("Moving drone to home position")

    if not cf.swarm_flying:
        cf.swarm_take_off()
        time.sleep(2)

    cf.swarm_move({DRONE_URI: [0, 0, FLIGHT_ZONE.floor_offset]}, 0, 2, False)

    cf.swarm_land()


def send_message(sock, action, data, data_type="na"):
    sock.send(json.dumps({"action": action, "type": data_type, "data": data}))


def recieve_message(sock):
    data = sock.receive()

    if isinstance(data, str):
        json_data = json.loads(data)

        if "action" in json_data:
            return json_data
        else:
            raise Exception("Recieved data is not in expected format!")
    else:
        raise Exception("Recieved data is not string!")


def start_trial_timer(sock):
    send_message(sock, action="timer", data="start")

    return time.time()


def stop_trial_timer(sock, start_time):
    send_message(sock, action="timer", data="stop")

    return round(time.time() - start_time, 2)


def update_score(sock, score_update):
    global SCORE

    SCORE += score_update

    send_message(sock, action="score", data=SCORE)


def log_movements(trial, time_list, movement_list):
    file = (MOVEMENT_FOLDER / str(participant.id) / str(trial)).with_suffix(".csv")

    with file.open(mode="w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["Time to Move", "Movement"])

        for time, movement in zip(time_list, movement_list):
            writer.writerow([time, movement])


@app.route("/")
def index():
    return render_template("index.html")


@sock.route("/action")
def echo(sock):
    send_message(
        sock,
        action="alert",
        data='Welcome! This is your first flight. Your time will start when you take off. Please press "Take Off" when you are ready',
    )

    move_home()

    experiment_trial = 0
    action_times = []
    movement_list = []
    trial_start = 0.0
    action_timer_start = 0.0

    while experiment_trial < NUM_TRIALS:
        data = recieve_message(sock)

        action = data["action"]

        if action == "move":
            if cf.swarm_flying:
                action_timer_stop = round(time.time() - action_timer_start, 2)
                action_times.append(action_timer_stop)

                action_timer_start = time.time()

                direction = data["direction"]

                movement_distance = BASE_MOVEMENT_DISTANCE

                if participant.condition == "manipulation":
                    movement_distance = (
                        random.randrange(
                            int(MOVEMENT_RANGE[0] * 100),
                            int(MOVEMENT_RANGE[1] * 100),
                            int(MOVEMENT_STEPS * 100),
                        )
                        / 100
                    )

                logger.info("Moving {}".format(direction))

                movement = None

                drone_position = cf.positions[DRONE_URI]
                match direction:
                    case "forward":
                        if (drone_position[1] + movement_distance) > FLIGHT_ZONE.y:
                            movement_distance = FLIGHT_ZONE.y - drone_position[1]
                        movement = [0.0, movement_distance, 0.0]
                    case "back":
                        if (drone_position[1] - movement_distance) < 0.0:
                            movement_distance = drone_position[1]
                        movement = [0.0, -movement_distance, 0.0]
                    case "left":
                        if (drone_position[0] - movement_distance) < -(
                            FLIGHT_ZONE.x / 2
                        ):
                            movement_distance = abs(
                                -(FLIGHT_ZONE.x / 2) - drone_position[0]
                            )
                        movement = [-movement_distance, 0.0, 0.0]
                    case "right":
                        if (drone_position[0] + movement_distance) > (
                            FLIGHT_ZONE.x / 2
                        ):
                            movement_distance = (FLIGHT_ZONE.x / 2) - drone_position[0]
                        movement = [movement_distance, 0.0, 0.0]
                    case _:
                        raise RuntimeError("Unknown direction: " + direction)

                # TODO: if the resulting movement would put the drone outside
                # the flight zone, only move to the edge of the zone

                logger.info("Movement: {}".format(movement))
                movement_list.append(f"{','.join(map(str, movement))}")
                cf.swarm_move({DRONE_URI: movement}, 0, 2.0, True)
            else:
                send_message(
                    sock,
                    action="alert",
                    data_type="no takeoff",
                    data="Please take off before attempting to move!",
                )

        elif action == "take off":
            if cf.swarm_flying:
                raise RuntimeError("Recieved take off command when already flying!")

            trial_start = start_trial_timer(sock)
            action_timer_start = time.time()
            cf.swarm_take_off()
            logger.info("Take off")
            movement_list = []

        elif action == "land" or action == "out of time":
            if not cf.swarm_flying:
                raise RuntimeError("Recieved land command when not flying!")

            trial_time = stop_trial_timer(sock, trial_start)

            action_timer_stop = round(time.time() - action_timer_start)
            action_times.append(action_timer_stop)

            cf.swarm_land()

            closest_goal = (math.inf, "")

            point_modifier = 0

            # find the closest goal
            try:
                for row in destinations:
                    for goal in row:
                        distance_to_current_goal = cf.distance_to_2D_point(
                            DRONE_URI, goal.position
                        )

                        logger.debug(
                            "Distance to goal {}: {}".format(
                                goal.label, distance_to_current_goal
                            )
                        )

                        drone_in_goal = distance_to_current_goal < GOAL_MARGIN

                        if drone_in_goal:
                            logger.info(
                                "Drone has landed in goal: {}".format(goal.label)
                            )
                            closest_goal = (distance_to_current_goal, goal)
                            point_modifier = goal.difficulty_modifier

                            # no need to continue searching
                            # when we've found we're *in* a goal

                            raise StopIteration()

                        distance_to_old_goal = closest_goal[0]

                        if distance_to_current_goal < distance_to_old_goal:
                            closest_goal = (distance_to_current_goal, goal.label)
                else:
                    logger.info("Drone has not landed in any goal!")
                    radius = FLIGHT_ZONE.y / len(destinations)

                    for i, arc in enumerate(destinations, 1):
                        if is_point_in_circle(radius * i, cf.positions[DRONE_URI]):
                            point_modifier = -arc[0].difficulty_modifier
            except StopIteration:
                pass

            new_score = BASE_SCORE * point_modifier
            update_score(sock, new_score)
            logger.info(f"Landed, points scored: {new_score}")

            message = f"You scored {new_score} points! Moving drone back to home."

            if action == "out of time":
                message = "You ran out of time! " + message
                movement_list.append("OUT OF TIME")
            elif action == "land":
                movement_list.append("LAND")

            send_message(
                sock,
                action="alert",
                data=message,
            )

            log_movements(experiment_trial, action_times, movement_list)

            if action_times:
                avg_time_per_action = statistics.fmean(action_times)
            else:
                avg_time_per_action = None

            drone_position = f"{','.join(map(str, cf.positions[DRONE_URI]))}"

            participant.write_data(
                experiment_trial,
                trial_time,
                avg_time_per_action,
                closest_goal[1],
                new_score,
                SCORE,
                drone_position,
            )

            move_home()
            action_times = []
            experiment_trial += 1

        else:
            raise RuntimeError("Illegal action: " + action)

    send_message(
        sock,
        action="alert",
        data="You are done! Let the experiment leader know you are ready for the final questionnaire and debriefing.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runs the risky drones experiment")

    parser.add_argument(
        "-c",
        "--condition",
        dest="condition",
        choices=["control", "manipulation"],
        help="Which experimental condition to run",
    )

    parser.add_argument("-i", "--id", help="The id of the current participant")

    parser.add_argument(
        "-s",
        "--simulation",
        action="store_true",
        help="The generated file with goals to use",
    )

    parser.add_argument(
        "-log",
        "--log-level",
        default="warning",
        help="Set the log level. Example --log-level debug, default=warning",
    )
    parser.add_argument(
        "-g",
        "--goal-file",
        dest="goalFile",
        type=Path,
        default="goals.bin",
        help="The generated file with goals to use",
    )

    parser.add_argument(
        "-l", dest="survey_link", required=True, help="Link to the survey."
    )

    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=args.log_level.upper(),
    )

    if args.simulation:
        cf = SimulatedController({DRONE_URI}, FLIGHT_ZONE, DRONE_URI)
    else:
        cf = CrazyflieController({DRONE_URI}, FLIGHT_ZONE, DRONE_URI)

    try:
        destinations = read_from_file(args.goalFile)
    except FileNotFoundError:
        logger.info("Could not find goal file {}".format(args.goalFile))
        quit()

    participant = Participant(
        id=args.id, condition=args.condition, data_fields=DATA_FIELDNAMES
    )

    (MOVEMENT_FOLDER / participant.id).mkdir(parents=True, exist_ok=True)

    params = {"PID": participant.id, "CONDITION": participant.condition}

    url = args.survey_link + "&" + urlencode(params)

    print("Survey is available at: " + url)

    app.run(host="0.0.0.0")
