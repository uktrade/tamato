class TaricXMLSourceBase:
    def get_xml_string(self):
        raise NotImplementedError("Implement on child class")


class TaricXMLFileSource(TaricXMLSourceBase):
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_xml_string(self):
        with open(self.file_path, "r") as file:
            return file.read()


class TaricXMLStringSource(TaricXMLSourceBase):
    def __init__(self, xml_string: str):
        self.xml_string = xml_string

    def get_xml_string(self):
        return self.xml_string
