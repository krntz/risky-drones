import uuid
import argparse
import csv
import logging
import os
import random
from pathlib import Path

logger = logging.getLogger(__name__)


class Participant:
    def __init__(self, data_fields, id=None, condition=None, dir=Path("./data")):
        if id is None:
            logger.info("No ID provided, generating new UUID...")
            self.id = str(uuid.uuid4())
        else:
            self.id = id
        logger.info("Participant ID is: {}".format(self.id))

        if condition is None:
            logger.info(
                "No condition given, attempting to read from pre-generated sequence..."
            )
            sequence = ParticipantSequence("participant_sequence.txt")
            self.condition = sequence.pop()
        else:
            self.condition = condition
        logger.info("Participant is in condition: {}".format(self.condition))

        self.data_fields = data_fields

        participant_data_folder = dir / "performance-data"
        participant_data_folder.mkdir(parents=True, exist_ok=True)

        self.participant_file = (participant_data_folder / self.id).with_suffix(".csv")

        logger.info(
            "Participant's performance data will be stored in {}".format(
                self.participant_file
            )
        )

        # Initialize participant data file
        with self.participant_file.open(mode="w", newline="") as csvfile:
            logger.info(
                "Creating new participant file {}".format(self.participant_file)
            )
            writer = csv.DictWriter(csvfile, fieldnames=self.data_fields)
            writer.writeheader()

    def write_data(
        self, experiment_trial, trial_time, time_per_action, closest_goal, score
    ):
        row = {
            "Participant ID": self.id,
            "Condition": self.condition,
            "Trial": experiment_trial,
            "Score": score,
            "Avg. time per action": time_per_action,
            "Time to complete trial": trial_time,
            "Closest goal": closest_goal,
        }

        with self.participant_file.open(mode="a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.data_fields)
            writer.writerow(row)


class ParticipantSequence:
    def __init__(self, filename):
        self.filename = filename
        self.sequence = []
        self.load_sequence()

    def load_sequence(self):
        """Load the sequence from the disk if it exists."""
        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                self.sequence = [line.strip() for line in f.readlines()]
            logging.info(f"Sequence loaded from {self.filename}.")
        else:
            logging.info(
                "No existing sequence file found. Starting with an empty sequence."
            )

    def save_sequence(self):
        """Save the sequence to the disk in a human-readable format."""
        with open(self.filename, "w") as f:
            for item in self.sequence:
                f.write(f"{item}\n")
        logging.debug(f"Sequence saved to {self.filename}.")

    def create_sequence_from_list(self, values):
        """Create a sequence from a list of string values."""
        self.sequence = list(values)  # Initialize the sequence with the provided list
        self.save_sequence()  # Save the new sequence to disk
        logging.debug(f"Sequence created from list: {values}")

    def create_block_randomized_sequence(
        self, num_participants, block_size, conditions
    ):
        """Create a sequence from a list of string values."""
        if num_participants % block_size != 0:
            raise ValueError("Number of participants must be a multiple of block size.")

        # Calculate the number of blocks
        num_blocks = num_participants // block_size

        # Create a list to hold the conditions for each block
        conditions_per_block = [
            conditions[i % len(conditions)] for i in range(block_size)
        ]

        # List to hold the final assignment
        assignment = []

        for _ in range(num_blocks):
            # Shuffle the conditions for the current block
            random.shuffle(conditions_per_block)
            assignment.extend(conditions_per_block)

        self.sequence = assignment
        self.save_sequence()  # Save the new sequence to disk
        logging.info("Created block randomized sequence.")

    def push(self, value):
        """Push a new string value onto the sequence."""
        self.sequence.append(value)  # Store the value as a string
        self.save_sequence()
        logging.debug(f"Pushed '{value}' onto the sequence.")

    def pop(self):
        """Pop the top string value from the sequence."""
        if self.sequence:
            value = self.sequence.pop()
            logging.debug(f"Popped value: '{value}' from the sequence.")
            self.save_sequence()
            return value  # Return the value as a string
        else:
            logging.error("Attempted to pop from an empty sequence.")
            raise IndexError("Popping from an empty sequence.")


def main():
    parser = argparse.ArgumentParser(
        description="Create block randomized participant sequences"
    )

    parser.add_argument(
        "--conditions", nargs="+", required=True, help="List of conditions"
    )

    parser.add_argument(
        "--num_participants", type=int, required=True, help="Number of participants"
    )

    parser.add_argument(
        "--block_size", type=int, default=4, help="Block size (default: 4)"
    )

    args = parser.parse_args()

    participantSequence = ParticipantSequence("participant_sequence.txt")
    participantSequence.create_block_randomized_sequence(
        args.num_participants, args.block_size, args.conditions
    )


if __name__ == "__main__":
    main()
