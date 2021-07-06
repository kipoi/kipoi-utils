"""Test load module
"""
import kipoi_utils
from kipoi_utils.utils import load_obj, inherits_from, override_default_kwargs, infer_parent_class, cd, default_kwargs
# %from kipoi_utils.data import BaseDataLoader, Dataset, AVAILABLE_DATALOADERS
import pytest

from collections import OrderedDict


def test_import_module_fn():
    fn = load_obj("kipoi_utils.utils.read_pickle")
    assert fn == kipoi_utils.utils.read_pickle


def test_import_module_cls():
    cls = load_obj("kipoi_utils.utils.Slice_conv")
    assert cls == kipoi_utils.utils.Slice_conv


def test_inherits_from():
    class MyBaseDataLoader(object):
        pass

    class MyDataset(MyBaseDataLoader):
        pass

    class A(MyDataset):
        pass

    class B(object):
        pass

    assert inherits_from(A, MyBaseDataLoader)
    assert inherits_from(A, MyDataset)
    assert inherits_from(MyDataset, MyBaseDataLoader)
    assert not inherits_from(B, MyBaseDataLoader)
    assert not inherits_from(B, MyDataset)


def test_infer_parent_class():
    class MyBaseDataLoader(object):
        pass
    class MyPreloadedDataset(MyBaseDataLoader):
        pass
    class MyDataset(MyBaseDataLoader):
        pass
    class MyBatchDataset(MyBaseDataLoader):
        pass
    class A(MyDataset):
        pass
    class B(object):
        pass

    MY_AVAILABLE_DATALOADERS = OrderedDict([
    ("MyPreloadedDataset", MyPreloadedDataset),
    ("MyDataset", MyDataset),
    ("MyBatchDataset", MyBatchDataset),
    ])

    assert 'MyDataset' == infer_parent_class(A, MY_AVAILABLE_DATALOADERS)
    assert infer_parent_class(B, MY_AVAILABLE_DATALOADERS) is None


def test_default_kwargs():
    class A(object):
        def __init__(self, a, b=2):
            self.a = a
            self.b = b

        def get_values(self):
            return self.a, self.b

    assert default_kwargs(A) == {"b": 2}

    def fn(a, b=2):
        return a, b
    assert default_kwargs(fn) == {"b": 2}

    def fn(b=2):
        return b
    assert default_kwargs(fn) == {"b": 2}

    def fn(b):
        return b
    assert default_kwargs(fn) == {}


def test_override_default_args():
    def fn(a, b=2):
        return a, b
    assert fn(1) == (1, 2)
    assert override_default_kwargs(fn, {})(1) == (1, 2)

    fn2 = override_default_kwargs(fn, {"b": 4})
    assert fn2(1) == (1, 4)
    assert fn2(1, 3) == (1, 3)
    # original function unchangd
    assert fn(1) == (1, 2)

    class A(object):
        def __init__(self, a, b=2):
            self.a = a
            self.b = b

        def get_values(self):
            return self.a, self.b

    assert A(1).get_values() == (1, 2)
    B = override_default_kwargs(A, dict(b=4))
    assert B(1).get_values() == (1, 4)
    # original class unchangd
    assert A(1).get_values() == (1, 2)
    assert B(1, 3).get_values() == (1, 3)

    with pytest.raises(ValueError):
        override_default_kwargs(A, dict(c=4))

def test_override_multiple_default_args():
    def fn(a, b, c, d=4, e=5):
        return a, b, c, d, e
    assert fn(1, 2, 3) == (1, 2, 3, 4, 5)
    assert override_default_kwargs(fn, {})(1, 2, 3, 4, 5) == (1, 2, 3, 4, 5)

    fn2 = override_default_kwargs(fn, {"d": 20})
    assert fn2(1, 2, 3) == (1, 2, 3, 20, 5)
    assert fn2(1, 2, 3, 10, 20) == (1, 2, 3, 10, 20)
    # original function unchangd
    assert fn(1, 2, 3) == (1, 2, 3, 4, 5)

    with pytest.raises(TypeError) as e:
        fn2(1)
    assert "fn() missing 2 required positional arguments: 'b' and 'c'" in str(e.value)
    
    class A(object):
        def __init__(self, a, b, c, d=4, e=5):
            self.a = a
            self.b = b
            self.c = c
            self.d = d
            self.e = e

        def get_values(self):
            return self.a, self.b, self.c, self.d, self.e
    with pytest.raises(TypeError) as e:
        A(1).get_values()
    assert "__init__() missing 2 required positional arguments: 'b' and 'c'" in str(e.value)
    
    B = override_default_kwargs(A, dict(b=10, c=20))
    assert B(1).get_values() == (1, 10, 20, 4, 5)
    # original class unchangd
    with pytest.raises(TypeError) as e:
        A(1).get_values()
    assert "__init__() missing 2 required positional arguments: 'b' and 'c'" in str(e.value)
    assert B(1, 30, 40).get_values() == (1, 30, 40, 4, 5)
    with pytest.raises(ValueError) as err:
        override_default_kwargs(A, dict(f=8))
    assert str(err.value) == "argument 'f' not specified in function/class.__init__ <class 'kipoi_utils.utils.Overriddentest_override_multiple_default_args.<locals>.A'> with args: ['a', 'b', 'c', 'd', 'e']"

def test_load_obj():
    with pytest.raises(ImportError):
        load_obj("asd.dsa")

    with pytest.raises(ImportError):
        load_obj("keras.dsa")


@pytest.mark.skip(reason="is a kipoi test, not kipoi_utils test")
def test_sequential_model_loading():
    m2 = kipoi.get_model("example/models/extended_coda", source='dir')
    m1 = kipoi.get_model("example/models/kipoi_dataloader_decorator", source='dir')

    with cd(m2.source_dir):
        next(m2.default_dataloader.init_example().batch_iter())
    with cd(m1.source_dir):
        next(m1.default_dataloader.init_example().batch_iter())
