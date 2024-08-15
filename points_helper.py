import logging
import pickle

import numpy as np

logger = logging.getLogger(__name__)


class Point:
    def __init__(self, x, y, difficulty_modifier):
        self._position = np.array([x, y])
        self._difficulty_modifier = difficulty_modifier

    @property
    def position(self):
        return self._position

    @property
    def difficulty_modifier(self):
        return self._difficulty_modifier


def write_to_file(points, filename):
    logger.info("Writing points to file {}".format(filename))

    with open(filename, "wb") as fp:
        pickle.dump(points, fp)


def read_from_file(filename):
    logger.info("Reading points from file {}".format(filename))

    with open(filename, "rb") as fp:
        points = pickle.load(fp)

    return points
