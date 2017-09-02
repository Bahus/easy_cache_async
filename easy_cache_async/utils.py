import inspect
from collections import namedtuple
from inspect import Parameter


ArgSpec = namedtuple('ArgSpec', 'args varargs keywords defaults')


def getargspec(func):
    signature = inspect.signature(func)

    args = []
    varargs = None
    keywords = None
    defaults = []

    for param in signature.parameters.values():  # type: Parameter
        if param.kind == Parameter.VAR_POSITIONAL:
            varargs = param.name
        elif param.kind in (
                Parameter.POSITIONAL_ONLY,
                Parameter.KEYWORD_ONLY,
                Parameter.POSITIONAL_OR_KEYWORD):
            args.append(param.name)
        elif param.kind == Parameter.VAR_KEYWORD:
            keywords = param.name

        # noinspection PyProtectedMember
        if param.default is not inspect._empty:
            defaults.append(param.default)

    return ArgSpec(args, varargs, keywords, tuple(defaults))


def force_text(obj, encoding='utf-8'):
    if isinstance(obj, str):
        return obj

    elif not isinstance(obj, bytes):
        return str(obj)

    try:
        return obj.decode(encoding=encoding)
    except UnicodeDecodeError:
        return obj


def force_binary(obj, encoding='utf-8'):
    if isinstance(obj, bytes):
        return obj
    elif not isinstance(obj, str):
        return bytes(obj)

    try:
        return obj.encode(encoding=encoding)
    except UnicodeEncodeError:
        return obj


def get_function_path(function, bound_to=None):
    """Get received function path (as string), to import function later
    with `import_string`.
    """
    if isinstance(function, str):
        return function

    # static and class methods
    if hasattr(function, '__func__'):
        real_function = function.__func__
    elif callable(function):
        real_function = function
    else:
        return function

    func_path = []

    module = getattr(real_function, '__module__', '__main__')
    if module:
        func_path.append(module)

    if not bound_to:
        try:
            bound_to = function.__self__
        except AttributeError:
            pass

    if bound_to:
        if isinstance(bound_to, type):
            func_path.append(bound_to.__name__)
        else:
            func_path.append(bound_to.__class__.__name__)
        func_path.append(real_function.__name__)
    else:
        func_path.append(real_function.__qualname__)

    return '.'.join(func_path)
