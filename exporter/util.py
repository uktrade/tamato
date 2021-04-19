import sys
from collections import defaultdict
from itertools import count
from pathlib import Path
from typing import Dict
from typing import List


def dit_filename_generator(start=1):
    """Generate incrementing DIT filenames."""
    counter = count(start)
    while True:
        yield f"DIT{next(counter):06}.xml"


def dit_file_generator(directory: str, start: int = 1):
    """Generate iterating DIT named files in the supplied directory for
    writing."""

    def generate_files():
        filenames = dit_filename_generator(start)

        while True:
            with open(Path(directory) / next(filenames), "wb+") as f:
                yield f

    files = generate_files()
    return lambda: next(files)


class UploadStatus:
    """
    Updatable envelope errors and messages, using default dicts.

    Once data is ready for returning from serialize will output data as a dict.
    """

    def __init__(
        self,
        initial_status=None,
        envelope_errors=None,
        envelope_messages=None,
        errors=None,
        messages=None,
        upload_pks=None,
    ):
        self.envelope_errors = defaultdict(list)
        self.envelope_messages = defaultdict(list)
        self.errors = []
        self.messages = []
        self.upload_pks = []

        if initial_status is not None:
            self.errors.extend(initial_status.errors)
            self.messages.extend(initial_status.messages)
            self.envelope_errors.update(initial_status.envelope_errors)
            self.envelope_messages.update(initial_status.envelope_messages)
            self.upload_pks.extend(initial_status.upload_pks)

        if envelope_errors is not None:
            self.envelope_errors.update(envelope_errors)

        if envelope_messages is not None:
            self.envelope_messages.update(envelope_messages)

        if errors:
            self.errors.extend(errors)

        if messages:
            self.messages.extend(messages)

        if upload_pks:
            self.upload_pks.extend(upload_pks)

    def output(self, output_file=None):
        if output_file is None:
            output_file = sys.stdout

        if self.errors:
            for message in self.errors:
                # Messages not associated with an envelope
                output_file.write(message)

        if self.messages:
            for message in self.messages:
                # Messages not associated with an envelope
                output_file.write(message)

        if self.envelope_messages:
            # Envelope statuses
            output_file.write("Envelope:         Error:")
            for envelope_id, message in self.envelope_messages.items():
                output_file.write(f"{envelope_id}            {message}")

        if self.envelope_messages:
            # Envelope statuses
            output_file.write("Envelope:         Message:")
            for envelope_id, message in self.envelope_messages.items():
                output_file.write(f"{envelope_id}            {message}")

    @property
    def success(self) -> bool:
        return not (self.errors or self.envelope_errors)

    def serialize(self):
        """
        :return:  class serialized to dict, suitable for returning over celery.
        """
        return {
            "envelope_errors": dict(self.envelope_errors),
            "envelope_messages": dict(self.envelope_messages),
            "errors": self.errors,
            "messages": self.messages,
            "upload_pks": self.upload_pks,
        }


def exceptions_as_messages(
    error_dict: Dict[int, List[Exception]],
) -> Dict[int, List[str]]:
    """
    :param error_dict: dict of lists of exceptions.
    :return: dict of lists of human readable strings containing the exception name.
    """
    new_errors = {}
    for k, errors in error_dict.items():
        new_errors[k] = [f"raised an {exc}" for exc in errors]
    return new_errors
