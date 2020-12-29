import os
import shutil
from collections import defaultdict
from pathlib import Path

from django.core.management import BaseCommand
from lxml import etree

from common.models import TrackedModel
from importer.management.commands.split_taric import split_taric
from importer.namespaces import nsmap
from importer.taric import EnvelopeParser
from workbaskets.validators import WorkflowStatus


XML_CHUNK_SIZE = 4096


def import_taric_file(taric_file, username, status):
    xmlparser = etree.iterparse(taric_file, ["start", "end", "start-ns"])
    handler = EnvelopeParser(
        workbasket_status=status,
        tamato_username=username,
    )
    for event, elem in xmlparser:
        if event == "start":
            handler.start(elem)

        if event == "start_ns":
            nsmap.update([elem])

        if event == "end":
            if handler.end(elem):
                elem.clear()


def build_file_map(dir_name):
    seed_dir = Path(dir_name)

    file_map = defaultdict(list)

    for seed_file in seed_dir.iterdir():
        if seed_file.is_file() and seed_file.suffix == ".xml":
            file_map[seed_file.name.split("-")[1]].append(seed_file)

    for file_list in file_map.values():
        file_list.sort()

    return file_map


def build_dependency_tree():
    dependency_map = {}
    record_codes = {subclass.record_code for subclass in TrackedModel.__subclasses__()}
    for subclass in TrackedModel.__subclasses__():
        if subclass.record_code not in dependency_map:
            dependency_map[subclass.record_code] = set()
        for _, relation in subclass.get_relations():
            if (
                relation.record_code != subclass.record_code
                and relation.record_code in record_codes
            ):
                dependency_map[subclass.record_code].add(relation.record_code)

    return dependency_map


def import_and_move_taric_file(file, username, status):
    print("importing", file)
    with open(file, "rb") as taric_file:
        import_taric_file(taric_file, username, status)
    dir_name, filename = os.path.split(file)
    new_path = os.path.join(dir_name, "done", filename)
    shutil.move(file, new_path)


def import_taric(
    taric3_file,
    username,
    status,
    skip_split=False,
    split_dir="_split_seed_import_files",
    record_code=None,
    chapter_heading=None,
    file=None,
):

    if file:
        path = Path(os.path.join(split_dir, file))
        print("loading", path)
        import_and_move_taric_file(path, username, status)
        return

    if not skip_split:
        print("splitting the file")
        with open(taric3_file, "rb") as seed_file:
            split_taric(seed_file, split_dir)
            print("file split")
    Path(os.path.join(split_dir, "done")).mkdir(exist_ok=True)

    file_map = build_file_map(split_dir)

    dependency_tree = build_dependency_tree()

    for key in list(dependency_tree.keys()):
        if key not in file_map:
            dependency_tree.pop(key)

    if record_code:
        for file in file_map.get(record_code, []):
            if chapter_heading and f"-{chapter_heading}-" not in str(file):
                continue
            import_and_move_taric_file(file, username, status)
        return

    while dependency_tree:
        for key, value in sorted(
            dependency_tree.items(), key=lambda x: (len(x[1]), x[0])
        ):
            if not value & dependency_tree.keys():
                for file in file_map[key]:
                    import_and_move_taric_file(file, username, status)
                break
        dependency_tree.pop(key)
        print("left to do:", dependency_tree.keys())


class Command(BaseCommand):
    help = "Import data from a TARIC XML file into TaMaTo"

    def add_arguments(self, parser):
        parser.add_argument(
            "taric3_file",
            help="The TARIC3 file to be parsed.",
            type=str,
        )
        parser.add_argument(
            "-u",
            "--username",
            help="The username to use for the owner of the workbaskets created.",
            type=str,
        )
        parser.add_argument(
            "-s",
            "--status",
            choices=[
                WorkflowStatus.NEW_IN_PROGRESS.value,
                WorkflowStatus.AWAITING_APPROVAL.value,
                WorkflowStatus.READY_FOR_EXPORT.value,
                WorkflowStatus.PUBLISHED.value,
            ],
            help="The status of the workbaskets containing the import changes.",
            type=str,
        )
        parser.add_argument(
            "-S",
            "--skip-split",
            action="store_true",
            help="Skip splitting the seed file if it has already been split.",
        )
        parser.add_argument(
            "-d",
            "--split-dir",
            help="The dir in which the split seed file is stored",
            default="_split_seed_import_files",
            type=str,
        )
        parser.add_argument(
            "-r",
            "--record-code",
            help="The record code to load",
            type=str,
        )
        parser.add_argument(
            "-c",
            "--chapter",
            help="The chapter heading to load",
            type=str,
        )
        parser.add_argument(
            "-f",
            "--file",
            help="The file to load",
            type=str,
        )

    def handle(self, *args, **options):
        print("importing taric file")
        import_taric(
            taric3_file=options["taric3_file"],
            username=options["username"],
            status=options["status"],
            skip_split=options["skip_split"],
            split_dir=options["split_dir"],
            record_code=options["record_code"],
            chapter_heading=options["chapter"],
            file=options["file"],
        )
