from itertools import count
from pathlib import Path


def dit_filename_generator(start=1):
    """Generate incrementing DIT filenames."""
    counter = count(start)
    while True:
        yield f"DIT{next(counter):06}.xml"


def dit_file_generator(directory: str, start: int = 1):
    """Generate iterating DIT named files in the supplied directory for writing."""

    def generate_files():
        filenames = dit_filename_generator(start)

        while True:
            with open(Path(directory) / next(filenames), "wb+") as f:
                yield f

    files = generate_files()
    return lambda: next(files)
