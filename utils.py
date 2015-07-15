import inspect
from functools import partial
from time import clock


def get_frame_at_level(level):
    seen = set()
    for obj in inspect.stack():
        frame, path = obj[:2]
        seen.add(path)
        if len(seen) > level:
            return frame


def get_global_vars(module=None):
    if module is not None:
        return module, get_global_vars_from_module(module)
    else:
        user_frame = get_frame_at_level(2)
        return user_frame, get_global_vars_from_frame(user_frame)


def get_global_vars_from_module(module):
    return vars(module).items()


def get_global_vars_from_frame(frame):
    return frame.f_globals.items()


def filter_variables(filter_rules, variables):
    '''Given an iterable of tuples 'variables' (name, value),
    filter variables according to filter_rules (applied to name).'''
    return [(name, _) for name, _ in variables
            if partial(is_valid_name, filter_rules)(name)]


def is_valid_name(filter_rules, name):
    return any(rule(name) for rule in filter_rules)


def find(L, x):
    try:
        return L.index(x)
    except ValueError:
        return -1


def categorize(rules, variables):
    '''Assign each variable to the rule it obeys.'''
    res = [[] for _ in xrange(len(rules))]
    for name, val in variables:
        for index, rule in enumerate(rules):
            if rule(name):
                res[index].append((name, val))
                break
    return res


def by_appearance(frame, var):
    name, value = var
    if inspect.isframe(frame):
        return frame.f_code.co_names.index(name)
    elif inspect.ismodule(frame):
        pass


def split(text, sep=None, maxsplit=-1):
    return [t.strip() for t in text.strip().split(sep, maxsplit)]



def timedcall(fn, *args, **kwgs):
    t = clock()
    result = fn(*args, **kwgs)
    return result, clock()-t


def memo(fn):
    '''Memoization decorator.'''
    cache = {}
    def _f(*args):
        try:
            return cache[args]
        except KeyError:
            cache[args] = result = fn(*args)
            return result
        except TypeError:  # unhashable args
            return fn(*args)
    return _f
        


def for_all(predicate, L):
    '''Return True if predicate is True for all elements in L.'''
    return all(map(predicate, L))


def for_any(predicate, L):
    '''Return True if predicate is True for any element in L.'''
    return any(map(predicate, L))
