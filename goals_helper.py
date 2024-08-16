import logging
import pickle

import numpy as np

logger = logging.getLogger(__name__)


class Goal:
    def __init__(self, x, y, difficulty_modifier):
        self._position = np.array([x, y])
        self._difficulty_modifier = difficulty_modifier

    @property
    def position(self):
        return self._position

    @property
    def difficulty_modifier(self):
        return self._difficulty_modifier


def write_to_file(goals, filename):
    logger.info("Writing goals to file {}".format(filename))

    with open(filename, "wb") as fp:
        pickle.dump(goals, fp)


def read_from_file(filename):
    logger.info("Reading goals from file {}".format(filename))

    with open(filename, "rb") as fp:
        goals = pickle.load(fp)

    return goals
