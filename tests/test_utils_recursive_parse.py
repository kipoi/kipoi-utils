from kipoi_utils.utils import recursive_dict_parse
import pytest


def test_recursive_dict_parse():
    def f_must_not_be_called(d):
        assert False # <= should not be called
    a = {"a": 1,
         "b": 2}
    assert a == recursive_dict_parse(a, "url", f_must_not_be_called)

    a = {"a": 1,
         "b": 2,
         "c": {"e": 3}}
    assert a == recursive_dict_parse(a, "url", f_must_not_be_called)

    def f_must_be_called(d):
        assert 'url' in d
        assert 'md5' in d
        assert 'foo' not in d

        ret = {
            'url' : d['url'] + 'new1',
            'md5' : d['md5'] + 'new2',
            'foo' : 'bar'
        }
        return ret

    a = {"a": 1,
         "b": 2,
         "c": {"url": "a",
                "md5": "b"}}
    out = recursive_dict_parse(a, "url", f_must_be_called)
    assert a != out
    assert out['a'] == a['a']
    assert out['b'] == a['b']
    assert out['c'] == {'url':'anew1','md5':"bnew2",'foo':'bar'}

    a = {"a": 1,
         "b": 2,
         "c": [{"url": "a",
                "md5": "b"}]}
    out = recursive_dict_parse(a, "url", f_must_be_called)
    assert a != out
    assert out['a'] == a['a']
    assert out['b'] == a['b']
    assert out['c'] == [{'url':'anew1','md5':"bnew2",'foo':'bar'}]