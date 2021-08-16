from typing import Dict, Sequence

from importer import utils


def get_dependency_tree(use_subrecord_codes: bool) -> Dict[str, Sequence[str]]:
    dependency_tree = utils.build_dependency_tree(use_subrecord_codes)

    d = {k: list(v) for k, v in dependency_tree.items()}
    with open(f"z{int(use_subrecord_codes)}", "w") as f:
        import json
        json.dump(d, f, indent=3)

    key_lens = {len(key) for key in dependency_tree}
    value_lens = {
        len(value)
        for values in dependency_tree.values()
        for value in values
    }

    return (key_lens, value_lens)

def test_generate_key():
    key = utils.generate_key("test", ["1", "2"], {"1": 1, "2": 2})
    assert key == "a98ec5c5044800c88e862f007b98d89815fc40ca155d6ce7909530d792e909ce"


def test_dependency_tree_structure_default():
    key_lens, value_lens = get_dependency_tree(False)

    assert len(key_lens) == len(value_lens) == 1
    assert list(key_lens)[0] == list(value_lens)[0] == 3


def test_dependency_tree_structure_subrecord_codes():
    key_lens, value_lens = get_dependency_tree(True)

    assert len(key_lens) == len(value_lens) == 1
    assert list(key_lens)[0] == list(value_lens)[0] == 5
