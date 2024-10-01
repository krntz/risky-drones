import argparse
import logging
import math
from pathlib import Path
from turtle import Screen, Turtle

from goals_helper import Goal, write_to_file

logger = logging.getLogger(__name__)


def exponential_difficulty(num):
    if num == 1:
        return 1
    else:
        return max(1, exponential_difficulty(num - 1) * 2)


def generate_goals(radius, num_arcs, num_goals, offset):
    goals = []
    goal_number = 0

    for arc in range(1, num_arcs + 1):
        row = []

        arc_span = 180 - (offset * 2)

        # need to subtract one to account for the first goal
        goals_separation = math.radians(arc_span / (num_goals - 1))

        for p in range(num_goals):
            rotation = p * goals_separation + math.radians(offset)

            x = round(radius * arc * math.cos(rotation), 2)
            y = round(radius * arc * math.sin(rotation), 2)

            # assign a letter label to each goal for easy identification

            label = chr(goal_number + 65)

            row.append(Goal(x, y, exponential_difficulty(arc), label))
            goal_number += 1

        goals.append(row)

    return goals


def visualize_goals(goals, radius, num_arcs):
    screen_width = 2048
    screen_height = 1024
    screen = Screen()
    screen.setup(screen_width, screen_height)
    screen.colormode(255)

    turtle = Turtle(visible=False)
    turtle.speed("fastest")
    scale = 500
    dot_size = 5 * 5
    turtle.width(5)

    turtle.teleport(0, -screen_height / 2 + 50)
    turtle.dot(dot_size, "red")

    for arc in range(1, num_arcs + 1):
        turtle.teleport(radius * arc * scale, -screen_height / 2 + 50)
        turtle.setheading(90)
        turtle.circle(radius * arc * scale, 180)

    for row in goals:
        for goal in row:
            turtle.teleport(
                goal.position[0] * scale,
                goal.position[1] * scale - screen_height / 2 + 50,
            )
            turtle.dot(dot_size, "blue")
            turtle.write(
                goal.label, align="center", font=("Arial", dot_size * 2, "normal")
            )

    screen.exitonclick()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser(
        description="Generates goals on arcs on a 2D plane to land in for the risky drones experiment"
    )

    parser.add_argument(
        "--width",
        dest="width",
        required=True,
        type=float,
        help="Width (in m) of the plane to generate goals in",
    )

    parser.add_argument(
        "--height",
        dest="height",
        required=True,
        type=float,
        help="Height (in m) of the plane to generate goals in",
    )

    parser.add_argument(
        "-a",
        "--arc",
        dest="num_arcs",
        required=True,
        type=int,
        help="The number of arcs (difficulties) to generate",
    )

    parser.add_argument(
        "-g",
        "--goals",
        dest="num_goals",
        required=True,
        type=int,
        help="The number of goals on each arc",
    )

    parser.add_argument(
        "-d",
        "--degrees",
        dest="offset_degrees",
        type=int,
        default=0,
        help="Optionally specify how many degrees to offset the first goal on each arc",
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        type=Path,
        default="goals.bin",
        help="If defined, will output the coordinates of the goals to the specified file, otherwise will output to goals.bin",
    )

    parser.add_argument(
        "-v",
        "--visualize",
        dest="visualize",
        action="store_true",
        help="Shows a visualization of the generated goals",
    )

    args = parser.parse_args()

    # TODO: At some point I want to remove this requirement

    if args.width < args.height:
        raise ValueError("The width of the plane must be at least equal to its height")

    logger.debug(
        "Generating goals on plane of dimensions ({}, {}), with {} arc(s) and {} goal(s) per arc, with {} offset".format(
            args.width, args.height, args.num_arcs, args.num_goals, args.offset_degrees
        )
    )
    radius = args.height / args.num_arcs

    goals = generate_goals(radius, args.num_arcs, args.num_goals, args.offset_degrees)

    if args.visualize:
        visualize_goals(goals, radius, args.num_arcs)

    if args.output_file:
        write_to_file(goals, args.output_file)
