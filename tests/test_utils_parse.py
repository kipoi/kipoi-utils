from kipoi_utils.utils import parse_json_file_str_or_arglist
import tempfile

def test_parse_json_file_str_or_arglist_from_json():
    
    input_list = ["""{
        "key_a":1.0,
        "key_b":true,
        "key_c":["hello", 42],
        "key_d":"42"
    }
    """]

    res =  parse_json_file_str_or_arglist(input_list)

    assert 'key_a' in res
    assert res['key_a'] == 1.0

    assert 'key_b' in res
    assert res['key_b'] == True

    assert 'key_c' in res
    assert res['key_c'] == ["hello", 42]

    assert 'key_d' in res
    assert res['key_d'] == "42"

    assert len(res) == 4


def test_parse_json_file_str_or_arglist_from_arglist():
    
    input_list = [
          "key_a=1.0",
          "key_b=True",
        """key_c=["hello",42]""",
        """key_d='42'"""
    ]

    res =  parse_json_file_str_or_arglist(input_list)

    assert 'key_a' in res
    assert res['key_a'] == 1.0

    assert 'key_b' in res
    assert res['key_b'] == True

    assert 'key_c' in res
    assert res['key_c'] == ["hello", 42]

    assert 'key_d' in res
    assert res['key_d'] == "42"

    assert len(res) == 4



def test_parse_json_file_str_or_arglist_from_arglist():
    

    json_str = """{
        "key_a":1.0,
        "key_b":true,
        "key_c":["hello", 42],
        "key_d":"42"
    }
    """




    import tempfile

    tmp = tempfile.NamedTemporaryFile()

    # Open the file for writing.
    with open(tmp.name, 'w') as f:
        f.write(json_str) 



    res =  parse_json_file_str_or_arglist([tmp.name])

    assert 'key_a' in res
    assert res['key_a'] == 1.0

    assert 'key_b' in res
    assert res['key_b'] == True

    assert 'key_c' in res
    assert res['key_c'] == ["hello", 42]

    assert 'key_d' in res
    assert res['key_d'] == "42"

    assert len(res) == 4