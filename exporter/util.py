import sys
import time
from itertools import count
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generator
from typing import List
from typing import Sequence
from typing import Tuple


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


class UploadTaskResultData(dict):
    """
    Manage an underlying dict that is used to pass data from Task to Task that
    will eventually be displayed to the user, whether on the commandline or in
    the GUI.

    By allowing conversion to / from a dict this sidesteps issues that can come
    up using more complex classes in Celery.
    """

    def add_messages(self, messages: list):
        """
        :param messages:  list of messages as strings.

        Add a list of general messages for display to the user, associated with something other than an Envelope in the upload.
        """

        self.setdefault("messages", [])
        self["messages"].extend(messages)
        return self

    def add_errors(self, errors: list):
        """
        :param errors:  list of errors as strings.

        Add a list of general errors for display to the user, associated with something other than an Envelope in the upload.

        Adding errors, will also make the .success property return False.
        """
        self.setdefault("errors", [])
        self["errors"].extend(errors)
        return self

    def add_envelope_messages(self, envelope_id, messages):
        """
        :param envelope_id:  envelope_id as integer
        :param messages:  list of messages associated with an Envelope

        Add a list of messages for display to the user, associated with an Envelope in an upload.
        """
        self.setdefault("envelope_messages", {})
        self["envelope_messages"].setdefault(envelope_id, [])
        self["envelope_messages"][envelope_id].extend(messages)
        return self

    def add_envelope_errors(self, envelope_id, errors: List[str]):
        """
        :param envelope_id:  envelope_id as integer
        :param errors:  list of errors associated with an Envelope

        Add a list of errors for display to the user, associated with an upload.

        Adding envelope errors, will also make the .success property return False.
        """
        self.setdefault("envelope_errors", {})
        self["envelope_errors"].setdefault(envelope_id, [])
        self["envelope_errors"][envelope_id].extend(errors)
        return self

    def add_upload_pk(self, pk):
        """Store the primary key of an Upload object associated with an
        upload."""
        self.setdefault("upload_pks", [])
        self["upload_pks"].append(pk)
        return self

    def output(self, output_file=None):
        """Output user messages and errors to a stream (usually stdout)."""
        if output_file is None:
            output_file = sys.stdout

        for message in self.get("errors", []):
            # Errors not associated with an envelope
            output_file.write(message)

        for message in self.get("messages", []):
            # Messages not associated with an envelope
            output_file.write(message)

        if "envelope_errors" in self:
            # Error messages and the Envelope ids they are associated with.
            output_file.write("Envelope:         Error:")
            for envelope_id, message in self.get("envelope_errors", {}).items():
                output_file.write(f"{envelope_id}            {message}")

        if "envelope_messages" in self:
            # User messages and the Envelope ids they are associated with.
            output_file.write("Envelope:         Message:")
            for envelope_id, message in self.get("envelope_messages", {}).items():
                output_file.write(f"{envelope_id}            {message}")

    @property
    def success(self) -> bool:
        return not (self.get("errors") or self.get("envelope_errors"))


def exceptions_as_messages(
    error_dict: Dict[int, List[Exception]],
) -> Dict[int, List[str]]:
    """
    :param error_dict: dict of lists of exceptions.
    :return: dict of lists of human-readable strings containing the exception name.
    """
    new_errors = {}
    for k, errors in error_dict.items():
        new_errors[k] = [f"raised an {exc}" for exc in errors]
    return new_errors


def item_timer(items: Sequence[Any]) -> Generator[Tuple[float, Any], None, None]:
    """
    :param items: Sequence of items.

    Iterates over the items and yield a tuple of (time_taken, item).
    """
    start_time = time.time()
    for o in items:
        time_taken = time.time() - start_time
        yield time_taken, o
        start_time = time.time()
