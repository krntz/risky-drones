import argparse
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Generates points on arcs on a 2D plane to land in for the risky drones experiment")

    parser.add_argument('-w',
                        '--width',
                        dest='width',
                        required=True,
                        type=int,
                        help="Width of the plane to generate points in")

    parser.add_argument('-h',
                        '--height',
                        dest='height',
                        required=True,
                        type=int,
                        help="Height of the plane to generate points in")

    parser.add_argument('-a',
                        '--arc',
                        dest='num_arcs',
                        required=True,
                        type=int,
                        help="The number of arcs (difficulties) to generate")

    parser.add_argument('-p',
                        '--points',
                        dest='num_points',
                        required=True,
                        type=int,
                        help="The number of points on each arc")

    parser.add_argument('-d',
                        '--degrees',
                        dest='offset_degrees',
                        type=int,
                        help="Optionally specify how many degrees to offset the first point on each arc")

    parser.add_argument('-o',
                        '--output',
                        dest='output_file',
                        type=Path,
                        help="If defined, will output the coordinates of the points to the specified file")

    args = parser.parse_args()

    generate_points(args.width, args.height, args.num_arcs, args.num_points)
