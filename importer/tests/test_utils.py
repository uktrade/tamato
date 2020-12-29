from importer import utils


def test_generate_key():
    key = utils.generate_key("test", ["1", "2"], {"1": 1, "2": 2})
    assert key == "a98ec5c5044800c88e862f007b98d89815fc40ca155d6ce7909530d792e909ce"
