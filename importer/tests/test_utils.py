from importer import utils


def test_generate_key():
    key = utils.generate_key("test", ["1", "2"], {"1": 1, "2": 2})
    assert (
        key == b"\xa9\x8e\xc5\xc5\x04H\x00\xc8\x8e\x86/\x00{\x98\xd8"
        b"\x98\x15\xfc@\xca\x15]l\xe7\x90\x950\xd7\x92\xe9\t\xce"
    )
