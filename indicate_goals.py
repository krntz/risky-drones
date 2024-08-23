import argparse
import logging
from pathlib import Path

import numpy as np

from controllers.crazyflieController import CrazyflieController
from controllers.simulatedController import SimulatedController
from controllers.utils.utils import FlightZone
from goals_helper import read_from_file

logger = logging.getLogger(__name__)

DRONE_URI = 'radio://0/80/2M/E7E7E7E7E0'
FLIGHT_ZONE = FlightZone(2.0, 3.0, 1.25, 0.3)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Uses a connected drone to indicate where to place physical goal markers.")

    parser.add_argument('-g',
                        '--goal-file',
                        dest='goalFile',
                        type=Path,
                        default=Path('./goals.bin'),
                        help='The generated file with goals to use.')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    with SimulatedController({DRONE_URI}, FLIGHT_ZONE, DRONE_URI) as cf:
        try:
            try:
                destinations = read_from_file(args.goalFile)
            except:
                logger.info(
                    "Could not find goal file {}".format(args.goalFile))
                quit()

            for row in destinations:
                for goal in row:
                    cf.swarm_take_off()

                    position = np.append(
                        goal.position, FLIGHT_ZONE.floor_offset)
                    cf.swarm_move({DRONE_URI: position}, 0, 1.0, False)

                    cf.swarm_land()
                    input("Place goal indicator {} on drone's location and press ENTER...".format(
                        goal.label))
        except KeyboardInterrupt:
            print("\nExiting...")
            quit()

    logging.info("All goals placed, exiting...")
