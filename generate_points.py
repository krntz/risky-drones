import argparse
import logging
import math
from pathlib import Path
from turtle import Screen, Turtle

from points_helper import Point, write_to_file

logger = logging.getLogger(__name__)


def generate_points(height, num_arcs, num_points, offset):
    # TODO: This doesn't evenly distribute the points along the arc?
    # The first point is further down than the last one...

    points = []

    for a in range(num_arcs):
        row = []

        radius = (height/2) / num_arcs * (a+1)

        points_separation = 180/num_points

        for p in range(num_points):
            rotation = offset + (points_separation*p)
            x = radius * math.cos(rotation)
            y = radius * math.sin(rotation)

            row.append(Point(x, y))
        points.append(row)

    return points


def visualize_points(points, height, num_arcs):
    screen = Screen()
    screen.setup()
    screen.colormode(255)

    turtle = Turtle(visible=False)
    turtle.speed('fastest')
    turtle.width(5)

    for a in range(num_arcs):
        radius = (height/2)/num_arcs * (a+1)

        turtle.teleport(radius*5, 0)
        turtle.setheading(90)
        turtle.circle(radius*5, 180)

    for row in points:
        for point in row:
            turtle.teleport(point.x*5, point.y*5)
            turtle.dot(15, 'blue')

    screen.exitonclick()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Generates points on arcs on a 2D plane to land in for the risky drones experiment")

    parser.add_argument('--width',
                        dest='width',
                        required=True,
                        type=int,
                        help="Width of the plane to generate points in")

    parser.add_argument('--height',
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
                        default=0,
                        help="Optionally specify how many degrees to offset the first point on each arc")

    parser.add_argument('-o',
                        '--output',
                        dest='output_file',
                        type=Path,
                        help="If defined, will output the coordinates of the points to the specified file")

    parser.add_argument('-v',
                        '--visualize',
                        dest='visualize',
                        action='store_true',
                        help="Shows a visualization of the generated points")

    args = parser.parse_args()

    if args.width < args.height:
        raise ValueError(
            "The width of the plane must be at least equal to its height")

    logger.debug("Generating points on plane of dimensions ({} {}), with {} arcs and {} points per arc, with {} offset".format(args.width,
                                                                                                                               args.height,
                                                                                                                               args.num_arcs,
                                                                                                                               args.num_points,
                                                                                                                               args.offset_degrees))

    points = generate_points(args.height, args.num_arcs,
                             args.num_points, args.offset_degrees)

    if args.visualize:
        visualize_points(points, args.height, args.num_arcs)

    if args.output_file:
        write_to_file(points, args.output_file)
