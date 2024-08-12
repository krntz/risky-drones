import logging
import pickle
from collections import namedtuple

logger = logging.getLogger(__name__)

Point = namedtuple("Point", "x y")


def write_to_file(points, filename):
    logger.info("Writing points to file {}".format(filename))

    with open(filename, "wb") as fp:
        pickle.dump(points, fp)


def read_from_file(filename):
    logger.info("Reading points from file {}".format(filename))

    with open(filename, "rb") as fp:
        points = pickle.load(fp)

    return points
