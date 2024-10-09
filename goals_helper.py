import logging
import pickle
import argparse
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


class Goal:
    def __init__(self, x, y, difficulty_modifier, label, radius):
        self._position = np.array([x, y])
        self._difficulty_modifier = difficulty_modifier
        self._label = label
        self._radius = radius

    def __repr__(self):
        return f'Goal(position = ({self.position[0]}, {self.position[1]}), difficulty_modifier = {self.difficulty_modifier}, label = "{self.label}", radius = {self.radius})'

    def __str__(self):
        return f"({self.label}: ({self.position[0]}, {self.position[1]}), {self.difficulty_modifier}, {self.radius})"

    @property
    def position(self):
        return self._position

    @property
    def difficulty_modifier(self):
        return self._difficulty_modifier

    @property
    def label(self):
        return self._label

    @property
    def radius(self):
        return self._radius


def write_to_file(goals, filename):
    logger.info("Writing goals to file {}".format(filename))

    with open(filename, "wb") as fp:
        pickle.dump(goals, fp)


def read_from_file(filename):
    logger.info("Reading goals from file {}".format(filename))

    with open(filename, "rb") as fp:
        goals = pickle.load(fp)

    return goals


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input", dest="filename", required=False, type=Path, default="goals.bin"
    )

    args = parser.parse_args()

    goals = read_from_file(args.filename)

    for row in goals:
        for goal in row:
            print(goal)
