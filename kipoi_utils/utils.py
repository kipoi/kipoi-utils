from io import open

import os
import os.path
import hashlib
import errno
# import psutil
from tqdm import tqdm
import pickle
import glob
import os
import sys
import subprocess
from subprocess import Popen, PIPE, STDOUT
import numpy as np
import functools
import yaml
from collections import OrderedDict
from contextlib import contextmanager
import inspect
import logging
import collections
import ast

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


# def kill_process_and_children(proc_pid):
#     process = psutil.Process(proc_pid)
#     for proc in process.children(recursive=True):
#         proc.terminate()
#         try:
#             proc.wait(timeout=1)
#         except TimeoutError:
#             proc.kill()
#     process.terminate()
#     try:
#         proc.wait(timeout=1)
#     except TimeoutError:
#         proc.kill()


def _call_command(cmd, extra_args, use_stdout=False,
                  return_logs_with_stdout=False, dry_run=False, **kwargs):
    """
    Args:
      return_logs_with_stdout (bool): If True, return also the logged lines
          (it only takes an effect with use_stdout)
    """
    # call conda with the list of extra arguments, and return the tuple
    # stdout, stderr
    cmd_list = [cmd]  # just use whatever conda is on the path

    cmd_list.extend(extra_args)
    if dry_run:
        return cmd, extra_args
    try:
        p = Popen(cmd_list, stdout=PIPE, universal_newlines=True, **kwargs)
            # Poll process for new output until finished
        error_out = []
        if return_logs_with_stdout:
            out = []
        for stdout_line in iter(p.stdout.readline, ""):
            stripped_line = stdout_line.rstrip()
            if use_stdout:
                print(stdout_line, end='')
            error_out.append(stripped_line.replace('\x1b', '\n'))
            if return_logs_with_stdout:
                out.append(stripped_line)
        p.stdout.close()
        return_code = p.wait()
        if return_code:
            raise Exception("could not invoke {0} \nreturn code:{1}\nadditional info:{2}".format(cmd_list, return_code, "".join(error_out)))
                #raise subprocess.CalledProcessError(return_code, cmd_list)
        if return_logs_with_stdout:
            return return_code, out
        else:
            return return_code
    except OSError as e:
        raise Exception("could not invoke {0}\n".format(cmd_list) + str(e))

    return p.communicate()

# recursive get and setattr
# https://stackoverflow.com/a/31174427
def rgetattr(obj, attr, *args):
    """Recursively get attributes:
    rgetattr(obj, 'attr.subattr')
    """
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return functools.reduce(_getattr, [obj] + attr.split('.'))


def rsetattr(obj, attr, val):
    """Recursively set attributes:
    rsetattr(obj, 'attr.subattr', 10)
    """
    pre, _, post = attr.rpartition('.')
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)


# temporarily add an object to path
class add_sys_path(object):
    """
    """

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        sys.path.insert(0, self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        sys.path.remove(self.path)


def load_obj(obj_import):
    """Load object from string
    """
    import importlib
    if "." not in obj_import:
        raise ValueError("Object descripiton needs to be of the form: "
                         "module.submodule.Object. currently lacking a dot (.)")

    # with add_sys_path(os.getcwd()):
    module_name, obj_name = obj_import.split(".", 1)
    # manually run the import (don't rely on importlib.import_module)
    # the latter was caching modules which caused trouble when
    # loading multiple modules of the same kind
    module = None
    try:
        module = importlib.import_module(module_name)
        obj = rgetattr(module, obj_name)  # recursively get the module
    except Exception as e:
        try:
            spec = importlib.util.spec_from_file_location(module_name, f"{os.getcwd()}/{module_name}.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            obj = rgetattr(module, obj_name)  # recursively get the module
        except Exception as e:
            raise ImportError("object {} couldn't be imported. Error {}".format(obj_import, str(e)))
    return obj


def load_module(path, module_name=None):
    """Load python module from file

    Args:
       path: python file path
       module_name: import as `module_name` name. If none, use `path[:-3]`
    """
    assert path.endswith(".py")
    if module_name is None:
        module_name = os.path.basename(path)[:-3]  # omit .py

    logger.debug("loading module: {0} as {1}".format(path, module_name))
    if sys.version_info[0] == 3:
        """
        import importlib.machinery
        loader = importlib.machinery.SourceFileLoader
        handle = loader.load_module
        """
        if sys.version_info[1] == 4:
            # way 1 (=python3.4)
            from importlib.machinery import SourceFileLoader
            module = SourceFileLoader(module_name, path).load_module()
        if sys.version_info[1] >= 5:
            # way 2 (>=python3.5)
            import importlib.util

            # alternative
            import types
            loader = importlib.machinery.SourceFileLoader(module_name, path)
            module = types.ModuleType(loader.name)
            loader.exec_module(module)

            # module_spec_ = importlib.util.spec_from_file_location(module_name, path)
            # module = importlib.util.module_from_spec(module_spec_)
            # module_spec_.loader.exec_module(module)
        else:
            raise RuntimeError(
                'dynamic loading of preprocessor module is not implemented for python3!')
    return module


def inherits_from(cls, parent):
    """Check if an object interits from the parent at some point
    """
    for x in inspect.getmro(cls):
        if x == parent:
            return True
    return False


def infer_parent_class(cls, class_dict):
    """Figure out the parent class
    """
    type_inferred = None
    for dl_type in reversed(class_dict):
        dl_cls = class_dict[dl_type]
        if inherits_from(cls, dl_cls):
            return dl_type
    return type_inferred

# todo move to kipoi conda
def pip_install_requirements(requirements_fname):
    if os.path.exists(requirements_fname):  # install dependencies
        logger.info('Running pip install -r {}...'.format(requirements_fname))
        subprocess.call(['pip', 'install', '-r', requirements_fname])
    else:
        logger.info('requirements.txt not found under {}'.format(requirements_fname))


def compare_numpy_dict(a, b, exact=True, decimal=7):
    """
    Compare two recursive numpy dictionaries or lists
    """
    if type(a) != type(b) and type(a) != np.ndarray and type(b) != np.ndarray:
        return False

    # Compare two dictionaries
    if type(a) == dict and type(b) == dict:
        if not a.keys() == b.keys():
            return False
        for key in a.keys():
            res = compare_numpy_dict(a[key], b[key], exact, decimal)
            if not res:
                print("false for key = ", key)
                return False
        return True

    # compare two lists
    if type(a) == list and type(b) == list:
        assert len(a) == len(b)
        return all([compare_numpy_dict(a[i], b[i], exact=exact, decimal=decimal)
                    for i in range(len(a))])

    # if type(a) == np.ndarray and type(b) == np.ndarray:
    if type(a) == np.ndarray or type(b) == np.ndarray:
        if exact:
            return (a == b).all()
        else:
            return np.testing.assert_almost_equal(a, b, decimal=decimal)

    if a is None and b is None:
        return True

    raise NotImplementedError


def parse_json_file_str(extractor_args):
    """Parse a string either as a json string or
    as a file path to a .json file
    """
    extractor_args = extractor_args.strip("'").strip('"')
    if extractor_args.startswith("{") or extractor_args.endswith("}"):
        logger.debug("Parsing the extractor_args as a json string")
        return yaml.load(extractor_args, Loader=yaml.FullLoader)
    else:
        if not os.path.exists(extractor_args):
            raise ValueError("File path: {0} doesn't exist".format(extractor_args))
        logger.debug("Parsing the extractor_args as a json file path")
        with open(extractor_args, "r", encoding="utf-8") as f:
            return yaml.load(f.read(), Loader=yaml.FullLoader)


def parse_json_file_str_or_arglist(dataloader_args, parser=None):
    """Parse a list strings as json string, or as file path to a .json file
        Format 1, json string, or as custom format 
            ['{key:val, key2:val2}']

        Format 2, filenamew:
            ['foo/bar/foobar.json']

        Format 3 custom: 
            ['key=val', 'key2=val2']
    """
    if dataloader_args is not None and not isinstance(dataloader_args, list):
        raise RuntimeError("wrong usage, dataloader_args must be a list")

    if dataloader_args is None or len(dataloader_args) == 0:
        return dict()

    elif len(dataloader_args) == 1:
        arg0 = dataloader_args[0].strip("'").strip('"')

        if arg0.startswith('{') and arg0.endswith('}'):
            return parse_json_file_str(dataloader_args[0])

        elif "=" not in arg0:
            return parse_json_file_str(dataloader_args[0])

    kwargs = {}
    for arg_str in dataloader_args:
        if "=" not in arg_str:
            if parser is not None:
                parser.error('cannot parse arg {0}'.format(str(arg_str)))
            else:
                raise RuntimeError('cannot parse arg {0}'.format(str(arg_str)))
        else:
            splitted = arg_str.split("=")
            if len(splitted) != 2:
                if parser is not None:
                    parser.error('cannot parse arg {0}'.format(str(arg_str)))
                else:
                    raise RuntimeError('cannot parse arg {0}'.format(str(arg_str)))
            else:
                key, valstr = splitted
                try:
                    pr = ast.literal_eval(valstr)
                    kwargs[key] = ast.literal_eval(valstr)
                except:
                    kwargs[key] = valstr

    return kwargs


# https://stackoverflow.com/questions/5121931/in-python-how-can-you-load-yaml-mappings-as-ordereddicts


def yaml_ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass

    def dict_constructor(loader, node):
        return OrderedDict(loader.construct_pairs(node))

    _mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG
    OrderedLoader.add_constructor(_mapping_tag, dict_constructor)
    return yaml.load(stream, OrderedLoader)


def yaml_ordered_dump(data, stream=None, Dumper=yaml.Dumper, **kwds):
    class OrderedDumper(Dumper):
        pass

    def dict_representer(dumper, data):
        return dumper.represent_dict(data.items())
    OrderedDumper.add_representer(OrderedDict, dict_representer)
    return yaml.dump(data, stream, OrderedDumper, **kwds)


@contextmanager
def cd(newdir):
    """Temporarily change the directory
    """
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


def getargs(x):
    """Get function arguments
    """
    if sys.version_info[0] == 2:
        if inspect.isfunction(x):
            return set(inspect.getargspec(x).args)
        else:
            # skip the self parameter
            return set(inspect.getargspec(x.__init__).args[1:])
    else:
        return set(inspect.signature(x).parameters.keys())


def _get_arg_name_values(fn_cls):
    """Get the function/class default argument list (and their values)

    Args:
      fn_cls: function or a class. In the class case,
          arguments for  `__init__` are returned
    """
    if sys.version_info[0] == 2:
        getargspec = inspect.getargspec
    else:
        getargspec = inspect.getfullargspec

    if inspect.isfunction(fn_cls):
        args = getargspec(fn_cls).args
        values = fn_cls.__defaults__
    else:
        # skip the self parameter
        args = getargspec(fn_cls.__init__).args[1:]
        values = fn_cls.__init__.__defaults__
    return args, values


def default_kwargs(fn_cls):
    """Get the default kwargs of a function
    """
    args, values = _get_arg_name_values(fn_cls)
    if values is None:
        return {}
    return {args[-i - 1]: values[-i - 1] for i in range(len(values))}


def copy_func(f, name=None):
    """Return a function with same code, globals, defaults, closure, and name (or provide a new name)
    Implemented by: https://stackoverflow.com/a/30714299/7529152

    # Arguments
      f: function
      name: new function name

    # Returns
      function  copy
    """
    import types
    fn = types.FunctionType(f.__code__, f.__globals__, name or f.__name__,
                            f.__defaults__, f.__closure__)
    # in case f was given attrs (note this dict is a shallow copy):
    fn.__dict__.update(f.__dict__)
    return fn


def override_default_kwargs(fn_cls, kwargs):
    """Override default kwargs in fn_cls. It keeps the original
    function / class intact.

    # Arguments
      fn_cls: function or a class

    # Returns
      new function or a class with the original attributes overriden
    """
    if inspect.isfunction(fn_cls):
        # make a copy of the object
        fn_cls = copy_func(fn_cls)
    else:
        def factory(BaseClass):
            """Copy the class and copy also the __init__
            """
            class NewClass(BaseClass):
                __init__ = copy_func(BaseClass.__init__)
            NewClass.__name__ = "Overridden" + BaseClass.__name__
            if sys.version_info[0] == 3:
                NewClass.__qualname__ = "Overridden" + BaseClass.__qualname__
            return NewClass
        fn_cls = factory(fn_cls)

    args, values = _get_arg_name_values(fn_cls)
    # check that all kwargs are specified
    for k in kwargs:
        if k not in args:
            raise ValueError("argument '{}' not specified in "
                             "function/class.__init__ {} with args: {}".format(k, fn_cls, args))

    # set the appropriate args
    out = []
    for arg_name in args[:-len(values)]:
        if arg_name in kwargs:
            out.append(kwargs[arg_name])

    for i, k in enumerate(args[-len(values):]):
        if k in kwargs:
            out.append(kwargs[k])
        else:
            out.append(values[i])

    new_values = tuple(out)
    if not inspect.isfunction(fn_cls):
        if sys.version_info[0] == 2:
            fn_cls.__init__.__func__.__defaults__ = new_values
        else:
            fn_cls.__init__.__defaults__ = new_values
    else:
        fn_cls.__defaults__ = new_values
    return fn_cls


def read_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def cmd_exists(cmd):
    """Check if a certain command exists
    """
    return subprocess.call("type " + cmd, shell=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE) == 0


def lfs_installed(raise_exception=False):
    """Check if git lfs is installed localls
    """
    ce = cmd_exists("git-lfs")
    if not ce:
        if raise_exception:
            raise OSError("git-lfs not installed")
        else:
            logger.warning("git-lfs not installed")
    return ce


def get_file_path(file_dir, basename, extensions=[".yml", ".yaml"],
                  raise_err=True):
    """Get the file path allowing for multiple file extensions
    """
    for ext in extensions:
        path = os.path.join(file_dir, basename + ext)
        if os.path.exists(path):
            return path
    if raise_err:
        raise ValueError("File path doesn't exists: {0}/{1}{2}".
                         format(file_dir, basename, set(extensions)))
    else:
        return None


def du(path):
    """disk usage in human readable format (e.g. '2,1GB')"""
    try:
        return subprocess.check_output(['du', '-sh', path]).split()[0].decode('utf-8')
    except Exception:
        return "NA"


class Slice_conv:

    def __getitem__(self, key):
        return key


def unique_list(seq):
    """Make a list unique and preserve the elements order

    Modified version of Dave Kirby solution
    """
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def read_txt(file_path, comment_str="#"):
    """Txt file reader that ignores comments and
    empty lines
    """
    out = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.partition(comment_str)[0]
            line = line.strip()
            if len(line) > 0:
                out.append(line)
    return out


def read_pickle(f):
    with open(f, "rb") as f:
        return pickle.load(f)


def merge_dicts(x, y):
    """https://stackoverflow.com/questions/38987/how-to-merge-two-dictionaries-in-a-single-expression
    """
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z


def list_files_recursively(root_dir, basename, suffix='y?ml'):
    """search for filenames matching the pattern: {root_dir}/**/{basename}.{suffix}
    """
    root_dir = os.path.join(root_dir, "")  # make sure root dir ends with "/"
    # TODO - implement skip
    if sys.version_info >= (3, 5):
        return [filename[len(root_dir):] for filename in
                glob.iglob(root_dir + '**/{0}.{1}'.format(basename, suffix), recursive=True)]
    else:
        # TODO - implement skip
        import fnmatch
        return [os.path.join(root, filename)[len(root_dir):]
                for root, dirnames, filenames in os.walk(root_dir)
                for filename in fnmatch.filter(filenames, '{0}.{1}'.format(basename, suffix))]


def map_nested(dd, fn):
    """Map a function to a nested data structure (containing lists or dictionaries

    Args:
      dd: nested data structure
      fn: function to apply to each leaf
    """
    if isinstance(dd, dict):
        return {key: map_nested(dd[key], fn) for key in dd}
    elif isinstance(dd, list):
        return [map_nested(x, fn) for x in dd]
    else:
        return fn(dd)


def take_first_nested(dd):
    """Get a single element from the nested list/dictionary

    Args:
      dd: nested data structure

    Example: take_first_nested({"a": [1,2,3], "b": 4}) == 1
    """
    if isinstance(dd, collections.abc.Mapping):
        return take_first_nested(list(dd.values())[0])
    elif isinstance(dd, collections.abc.Sequence):
        return take_first_nested(dd[0])
    else:
        return dd


class classproperty(object):
    """https://stackoverflow.com/questions/128573/using-property-on-classmethods
    Allow using @classproperty
    """

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


def is_subdir(path, directory):
    """Check if the path is in a particular directory

    Example:

    In [102]: is_subdir("/a/b/c", '/a/b')
    Out[105]: True

    In [106]: is_subdir("/a/b/c", '/a/c')
    Out[106]: False
    """
    path = os.path.realpath(path)
    directory = os.path.realpath(directory)
    relative = os.path.relpath(path, directory)
    return not (relative == os.pardir or relative.startswith(os.pardir + os.sep))


def relative_path(full_path, parent_subpath):
    """Get the relative path

    Args:
      path: long path: example /a/b/c
      parent_subpath: sub-directory.

    Example:

    In [78]: relative_path("/a/b/c", '/a')
    Out[78]: 'b/c'

    In [79]: relative_path("/a/b/c", '/a/')
    Out[79]: 'b/c'
    """
    full_path = os.path.realpath(full_path)
    assert parent_subpath != ""
    parent_subpath = os.path.realpath(parent_subpath)
    relative = os.path.relpath(full_path, parent_subpath)
    return relative


def recursive_dict_parse(d, key, fn):
    """Recursively parse the dictionary and apply
    fn once a child dictionary with a key has been observed

    Args:
      d: nested data structure
      key: dictionary key to watch.
      fn: when a dict with `key` is found, apply a function
         to this dictionary
    """
    if isinstance(d, collections.abc.Mapping):
        if key in d:
            return fn(d)
        else:
            return OrderedDict([(k, recursive_dict_parse(v, key, fn)) for k, v in d.items()])
    elif isinstance(d, list):
        return [recursive_dict_parse(v, key, fn) for v in d]
    else:
        # nothing to iterate over. stop recursion
        return d


def makedir_exist_ok(dirpath):
    """Python2 support for os.makedirs(.., exist_ok=True)
    """
    try:
        os.makedirs(dirpath)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise OSError(str(e))


def get_subsuffix(file_path):
    """
    >>> get_subsufix("asds.lmdb.zarr")
    >>> ('zarr', 'lmdb')
    """
    elems = file_path.split(".")
    if len(elems) == 1:
        return "", ""
    elif len(elems) == 2:
        return elems[-1], ""
    else:
        return elems[-1], elems[-2]
