from bs4 import BeautifulSoup

from importer.new_parsers import MessageInfo
from importer.new_parsers import NewElementParser


class NewImporter:
    """
    todo : write something meaningful
    """

    bs_taric3_file: BeautifulSoup
    raw_xml: str
    objects = []
    _parsers = {}

    def __init__(
        self,
        taric3_file: str,
        # username: str,
        # status: str,
        # partition_scheme_setting: str,
        # name: str,
        # split_codes: bool = False,
        # dependencies=None,
        # record_group: Sequence[str] = None
    ):
        # Read xml into string
        with open(taric3_file, "r") as file:
            self.raw_xml = file.read()

        # load the taric3 file into memory, via beautiful soup
        self.bs_taric3_file = BeautifulSoup(self.raw_xml, "xml")

        # tmp : report on file stats
        self.report_taric3_stats()

        # iterate through and virtually create objects

        # Validate each relationship

        # if all good, commit to workbasket

    def message_info(self, message) -> MessageInfo:
        return MessageInfo(message)

    def print_import_file_stats(self, update_stats: dict):
        for key in update_stats.keys():
            print(f"{key} : {update_stats[key]}")

    def report_taric3_stats(self):
        transactions = self.bs_taric3_file.find_all("env:transaction")
        transaction_count = len(transactions)
        total_message_count = 0
        update_stats = {}

        for transaction in transactions:
            messages = transaction.find_all("env:app.message")
            message_count = len(messages)
            total_message_count += message_count

            for message in messages:
                message_info = self.message_info(message)
                # add to stats
                key = (
                    message_info.object_type.replace(".", "_")
                    + "_"
                    + message_info.update_type_name
                )
                if key in update_stats.keys():
                    update_stats[key] += 1
                else:
                    update_stats[key] = 1

                self.objects.append(self.create_tmp_object(message_info))

        update_stats["transactions"] = transaction_count
        update_stats["messages"] = total_message_count
        self.print_import_file_stats(update_stats)

    def create_tmp_object(self, message_info: MessageInfo):
        parser_cls = self.get_parser(message_info.object_type)
        parser = parser_cls()

        for data_item_key in message_info.data.keys():
            mapped_data_item_key = data_item_key
            if data_item_key in parser.value_mapping:
                mapped_data_item_key = parser.value_mapping[data_item_key]

            if hasattr(parser, mapped_data_item_key):
                setattr(parser, mapped_data_item_key, message_info.data[data_item_key])
            else:
                raise Exception(
                    f"{parser.xml_object_tag} {parser} does not have a {data_item_key} attribute, and "
                    f"can't assign value {message_info.data[data_item_key]}",
                )

        return parser

    def get_parser(self, object_type: str):
        classes = self._get_parser_classes()

        for cls in classes:
            if cls.xml_object_tag == object_type:
                return cls

        raise Exception(f"No parser class matching {object_type}")

    def _get_parser_classes(self):
        return self._get_all_subclasses(NewElementParser)

    def _get_all_subclasses(self, cls):
        all_subclasses = []

        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(self._get_all_subclasses(subclass))

        return all_subclasses
