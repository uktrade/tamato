"""TARIC3 XML namespaces."""

ENVELOPE = "env"
SEED_MESSAGE = "ns2"  # this is the prefix used in the seed file
TARIC_MESSAGE = "oub"  # this is the prefix used in EU TARIC3 xml files
XML_SCHEMA = "xs"

nsmap = {
    ENVELOPE: "urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0",
    SEED_MESSAGE: "urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0",
    TARIC_MESSAGE: "urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0",
    XML_SCHEMA: "http://www.w3.org/2001/XMLSchema",
}
