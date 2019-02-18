"""Test 
"""
import os
from kipoi_utils.utils import list_files_recursively


def test_list_files_recursively():
    a = list_files_recursively("tests", 'model', suffix='foobar')
    b = list_files_recursively("tests/", 'model', suffix='foobar')
    c = list_files_recursively(os.path.abspath("tests"), 'model', suffix='foobar')
    assert a == b
    assert a == c
    assert len(a) == 3
    assert a[0] in [
        'test_foo/bar/model.foobar',
        'test_foo/foo/bar/model.foobar',
        'test_foo/foobar/model.foobar',
    ]
    assert a[1] in [
        'test_foo/bar/model.foobar',
        'test_foo/foo/bar/model.foobar',
        'test_foo/foobar/model.foobar',
    ]
    assert a[2] in [
        'test_foo/bar/model.foobar',
        'test_foo/foo/bar/model.foobar',
        'test_foo/foobar/model.foobar',
    ]
    assert a[0] != a[1]
    assert a[1] != a[2]
    assert a[0] != a[2]
    assert all([x.endswith("model.foobar") for x in a])
    assert all([os.path.exists(os.path.join("tests", x)) for x in a])
