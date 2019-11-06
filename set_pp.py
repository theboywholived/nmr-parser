import os
import platform
from sys import stdout

python_ver = platform.python_version()[0]

OrderedDict = None
if python_ver == 2:
    FileNotFoundError = IOError
    try:
        from thread import get_ident as _get_ident
    except ImportError:
        from dummy_thread import get_ident as _get_ident

    try:
        from _abcoll import KeysView, ValuesView, ItemsView
    except ImportError:
        pass


    class OrderedDict(dict):
        'Dictionary that remembers insertion order'

        # An inherited dict maps keys to values.
        # The inherited dict provides __getitem__, __len__, __contains__, and get.
        # The remaining methods are order-aware.
        # Big-O running times for all methods are the same as for regular dictionaries.

        # The internal self.__map dictionary maps keys to links in a doubly linked list.
        # The circular doubly linked list starts and ends with a sentinel element.
        # The sentinel element never gets deleted (this simplifies the algorithm).
        # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

        def __init__(self, *args, **kwds):
            '''Initialize an ordered dictionary.  Signature is the same as for
            regular dictionaries, but keyword arguments are not recommended
            because their insertion order is arbitrary.

            '''
            if len(args) > 1:
                raise TypeError('expected at most 1 arguments, got %d' % len(args))
            try:
                self.__root
            except AttributeError:
                self.__root = root = []  # sentinel node
                root[:] = [root, root, None]
                self.__map = {}
            self.__update(*args, **kwds)

        def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
            'od.__setitem__(i, y) <==> od[i]=y'
            # Setting a new item creates a new link which goes at the end of the linked
            # list, and the inherited dictionary is updated with the new key/value pair.
            if key not in self:
                root = self.__root
                last = root[0]
                last[1] = root[0] = self.__map[key] = [last, root, key]
            dict_setitem(self, key, value)

        def __delitem__(self, key, dict_delitem=dict.__delitem__):
            'od.__delitem__(y) <==> del od[y]'
            # Deleting an existing item uses self.__map to find the link which is
            # then removed by updating the links in the predecessor and successor nodes.
            dict_delitem(self, key)
            link_prev, link_next, key = self.__map.pop(key)
            link_prev[1] = link_next
            link_next[0] = link_prev

        def __iter__(self):
            'od.__iter__() <==> iter(od)'
            root = self.__root
            curr = root[1]
            while curr is not root:
                yield curr[2]
                curr = curr[1]

        def __reversed__(self):
            'od.__reversed__() <==> reversed(od)'
            root = self.__root
            curr = root[0]
            while curr is not root:
                yield curr[2]
                curr = curr[0]

        def clear(self):
            'od.clear() -> None.  Remove all items from od.'
            try:
                for node in self.__map.itervalues():
                    del node[:]
                root = self.__root
                root[:] = [root, root, None]
                self.__map.clear()
            except AttributeError:
                pass
            dict.clear(self)

        def popitem(self, last=True):
            '''od.popitem() -> (k, v), return and remove a (key, value) pair.
            Pairs are returned in LIFO order if last is true or FIFO order if false.

            '''
            if not self:
                raise KeyError('dictionary is empty')
            root = self.__root
            if last:
                link = root[0]
                link_prev = link[0]
                link_prev[1] = root
                root[0] = link_prev
            else:
                link = root[1]
                link_next = link[1]
                root[1] = link_next
                link_next[0] = root
            key = link[2]
            del self.__map[key]
            value = dict.pop(self, key)
            return key, value

        # -- the following methods do not depend on the internal structure --

        def keys(self):
            'od.keys() -> list of keys in od'
            return list(self)

        def values(self):
            'od.values() -> list of values in od'
            return [self[key] for key in self]

        def items(self):
            'od.items() -> list of (key, value) pairs in od'
            return [(key, self[key]) for key in self]

        def iterkeys(self):
            'od.iterkeys() -> an iterator over the keys in od'
            return iter(self)

        def itervalues(self):
            'od.itervalues -> an iterator over the values in od'
            for k in self:
                yield self[k]

        def iteritems(self):
            'od.iteritems -> an iterator over the (key, value) items in od'
            for k in self:
                yield (k, self[k])

        def update(*args, **kwds):
            '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

            If E is a dict instance, does:           for k in E: od[k] = E[k]
            If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
            Or if E is an iterable of items, does:   for k, v in E: od[k] = v
            In either case, this is followed by:     for k, v in F.items(): od[k] = v

            '''
            if len(args) > 2:
                raise TypeError('update() takes at most 2 positional '
                                'arguments (%d given)' % (len(args),))
            elif not args:
                raise TypeError('update() takes at least 1 argument (0 given)')
            self = args[0]
            # Make progressively weaker assumptions about "other"
            other = ()
            if len(args) == 2:
                other = args[1]
            if isinstance(other, dict):
                for key in other:
                    self[key] = other[key]
            elif hasattr(other, 'keys'):
                for key in other.keys():
                    self[key] = other[key]
            else:
                for key, value in other:
                    self[key] = value
            for key, value in kwds.items():
                self[key] = value

        __update = update  # let subclasses override update without breaking __init__

        __marker = object()

        def pop(self, key, default=__marker):
            '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
            If key is not found, d is returned if given, otherwise KeyError is raised.

            '''
            if key in self:
                result = self[key]
                del self[key]
                return result
            if default is self.__marker:
                raise KeyError(key)
            return default

        def setdefault(self, key, default=None):
            'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
            if key in self:
                return self[key]
            self[key] = default
            return default

        def __repr__(self, _repr_running={}):
            'od.__repr__() <==> repr(od)'
            call_key = id(self), _get_ident()
            if call_key in _repr_running:
                return '...'
            _repr_running[call_key] = 1
            try:
                if not self:
                    return '%s()' % (self.__class__.__name__,)
                return '%s(%r)' % (self.__class__.__name__, self.items())
            finally:
                del _repr_running[call_key]

        def __reduce__(self):
            'Return state information for pickling'
            items = [[k, self[k]] for k in self]
            inst_dict = vars(self).copy()
            for k in vars(OrderedDict()):
                inst_dict.pop(k, None)
            if inst_dict:
                return (self.__class__, (items,), inst_dict)
            return self.__class__, (items,)

        def copy(self):
            'od.copy() -> a shallow copy of od'
            return self.__class__(self)

        @classmethod
        def fromkeys(cls, iterable, value=None):
            '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
            and values equal to v (which defaults to None).

            '''
            d = cls()
            for key in iterable:
                d[key] = value
            return d

        def __eq__(self, other):
            '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
            while comparison to a regular mapping is order-insensitive.

            '''
            if isinstance(other, OrderedDict):
                return len(self) == len(other) and self.items() == other.items()
            return dict.__eq__(self, other)

        def __ne__(self, other):
            return not self == other

        # -- the following methods are only used in Python 2.7 --

        def viewkeys(self):
            "od.viewkeys() -> a set-like object providing a view on od's keys"
            return KeysView(self)

        def viewvalues(self):
            "od.viewvalues() -> an object providing a view on od's values"
            return ValuesView(self)

        def viewitems(self):
            "od.viewitems() -> a set-like object providing a view on od's items"
            return ItemsView(self)
else:
    import collections

    OrderedDict = collections.OrderedDict


def get_paths(pattern):
    """
    Gets list of paths (in priority order) for pulse program and useful parameter files from the Bruker configuration
    file,"parfile-dirs.prop" located in the Python working directory
    :param pattern: heading under which it is stored in the Bruker configuration file
    :return: list of paths for the pattern
    """
    filepaths = []
    try:
        f = open('parfile-dirs.prop', 'r')
        for i in f:
            if pattern in i:
                filepaths += i[(len(pattern) + 1):].strip().split(';')
        f.close()

    except:
        raise FileNotFoundError("Couldn't get paths from parfile-dirs.prop in /topspin.../prog/curdir/go/")

    return filepaths


def get_pp():
    """
    Gets the original pulseprogram and the absolute path for the file
    :return: original pulseprogram, absolute path to the original pulseprogram
    """
    _py_working_dir = os.popen('pwd').read().strip()
    _nmr_wd = _py_working_dir[:_py_working_dir.find('/prog/curdir')] + '/exp/stan/nmr'
    pp_orig = []
    _pp_filename = GETPAR('PULPROG')
    pp_wd = ""
    for fp in get_paths("PP_DIRS"):
        pp_wd = ((_nmr_wd + '/') if fp[0] != '/' else '') + fp + '/'
        pp_abs_path = pp_wd + _pp_filename
        # MSG(cwd)
        if os.path.exists(pp_abs_path):
            pp = open(pp_abs_path)
            for i in pp:
                pp_orig += [i]
            pp.close()
            break
    if len(pp_orig) == 0:
        raise FileNotFoundError("Couldn't find the Pulse Program")
    return pp_orig, pp_wd


def write_file(dir, name, content):
    """
    Writes the pulseprogram in the given directory
    :param dir: path to the folder of the pulseprogram
    :param name: name of the pulseprogram
    :param content: content to be written
    """
    try:
        # MSG(dir + name)
        # MSG(str(content))
        f = open(dir + name, 'w')
        # MSG("WRITING")
        for i in content:
            f.write(i)
        f.close()
    except:
        raise IOError("Couldn't write the Pulse Program")


def change_pp(pp_local, pp_directory):
    """
    Handles User interaction, if the user changes the pulseprogram present in the modified txt file
    :param pp_local: the new pulseprogram written by the user
    :param pp_directory: path for the pulseprogram currently used by the dataset
    :return: filename for the new pulseprogram or None (if same as old)
    """
    result = INPUT_DIALOG(title="Pulseprogram Changed",
                          header="The pulseprogram has been changed. \nPlease enter a name for the new pulse "
                                 "program.\nIt will be stored in:\n" + pp_directory + "\nPress OK to Accept.\nPress Can"
                                                                                      "cel to Ignore.",
                          items=["Name:"],
                          values=[GETPAR("PULPROG")],
                          )
    if result is not None:
        new_pp_filename = str(result[0]).strip()
        if new_pp_filename == pp_filename:
            value = SELECT(title="Filename Same",
                           message="Do you want to overwrite the existing Pulse Program?\nThis option CANNOT be "
                                   "reversed.",
                           buttons=["Yes", "No"]
                           )
            if value == 0:
                write_file(pp_directory, new_pp_filename, pp_local)
            elif value == 1:
                change_pp(pp_local, pp_directory)
            elif value == 2 or value < 0:
                EXIT()
        else:
            write_file(pp_directory, new_pp_filename, pp_local)
            return new_pp_filename


dd = CURDATA()
# Data Directory, i.e, where the working dataset is located
# Calculate the data directory path
data_dir = dd[3] + os.sep + dd[0] + os.sep + dd[1]

result_axis = OrderedDict()
result_nonaxis = OrderedDict()
# pp_local: pulseprogram present in the modified file
pp_local = []
pp_modified_filename = "pp_modified.txt"
try:
    f = open(data_dir + os.sep + pp_modified_filename, 'r')

    for i in f:
        if i == ';***Axis Parameters***\n':
            break
        pp_local += [i]
    for i in f:
        if i == ';***Non-Axis Parameters***\n':
            break
        each_line = i.strip()
        each_line = each_line.split(';')[1]
        result_axis[each_line.split('=')[0]] = each_line.split('=')[1]
    for i in f:
        each_line = i.strip()
        each_line = each_line.split(';')[1]
        result_nonaxis[each_line.split('=')[0]] = each_line.split('=')[1]

    f.close()
except IOError:
    raise IOError("Couldn't Find/Open the modified txt file")
except IndexError:
    raise IndexError(
        "Parameters not modified properly. Please run get_pp, make your changes again, and then run set_pp")

# pp_global: pulseprogram used by the working dataset
pp_global, pp_dir = get_pp()
pp_filename = GETPAR("PULPROG")

if pp_global != pp_local:
    PULPROG_user = change_pp(pp_local, pp_dir)

    # if pulseprogram name has changed, modify the same in Topspin
    if PULPROG_user is not None:
        PUTPAR("PULPROG", PULPROG_user)

# Setting each parameter according to the modified txt file
for key, value in result_axis.items():
    PUTPAR(key, value)
for key, value in result_nonaxis.items():
    PUTPAR(key, value)
