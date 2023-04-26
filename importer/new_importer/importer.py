import bs4
from bs4 import BeautifulSoup
from bs4 import NavigableString
from bs4 import Tag

from common.validators import UpdateType


class MessageInfo:
    transaction_id: int
    record_code: str
    subrecord_code: str
    sequence_number: int
    update_type: int
    update_type_name: str
    object_type: str
    message: Tag
    data: dict

    def __init__(self, message: bs4.Tag):
        # get transaction_id, record_code, subrecord_code, sequence.number, update.type and object type
        self.message = message
        self.transaction_id = self.message.find("oub:transaction.id").value
        self.record_code = self.message.find("oub:record.code").value
        self.subrecord_code = self.message.find("oub:subrecord.code").value
        self.sequence_number = self.message.find("oub:record.sequence.number").value
        self.update_type = int(self.message.find("oub:update.type").text)
        self.object_type = ""
        # get object type
        sibling = self.message.find("oub:update.type").next_sibling

        while self.object_type == "":
            if sibling is None:
                break
            elif isinstance(sibling, NavigableString):
                sibling = sibling.next_sibling
                continue
            elif isinstance(sibling, Tag):
                self.object_type = sibling.name
                break

        for update_type in UpdateType:
            if update_type.value == self.update_type:
                self.update_type_name = update_type.name.lower()

        self._populate_data_dict()

    def _populate_data_dict(self):
        """Iterates through properties in the object tag and returns a
        dictionary of those properties."""
        self.data = dict()
        for tag in self.message.find(self.object_type).children:
            if isinstance(tag, NavigableString):
                continue
            elif isinstance(tag, Tag):
                self.data[tag.name] = tag.text

        return


class NewElementParser:
    record_code: str
    subrecord_code: str
    xml_object_tag: str

    def __init__(self, message: Tag, message_info: MessageInfo):
        pass


class NewImporter:
    """
    todo : write something meaningful
    """

    bs_taric3_file: BeautifulSoup
    raw_xml: str
    objects = []

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
                print(message_info.data)
                if key in update_stats.keys():
                    update_stats[key] += 1
                else:
                    update_stats[key] = 1

        update_stats["transactions"] = transaction_count
        update_stats["messages"] = total_message_count
        self.print_import_file_stats(update_stats)

    def create_tmp_object(self, message, message_info: MessageInfo):
        self.get_parser(message_info.object_type)

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
