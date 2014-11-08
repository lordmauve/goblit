"""Utilities for binding extra directives and stage directions."""
import re
from .errors import ScriptError
from collections import OrderedDict


# A list of all registered stage directions
STAGE_DIRECTIONS = []


def make_regex(pattern):
    pattern = pattern.strip()
    pattern = re.escape(pattern)
    pattern = pattern.replace(r'\*', r'([A-Z ]+)')
    return re.compile(pattern)


def stagedirection(pattern):
    """Register a stage direction that matches pattern.

    pattern is a regular expression, with the extended feature that underscore
    matches an uppercase identifier (possibly containing spaces).

    """
    def decorator(func):
        STAGE_DIRECTIONS.append((
            make_regex(pattern),
            func
        ))
        return func
    return decorator


# Missing bindings are accumulated here
# So that we can print them all at once
SUGGESTED_BINDINGS = OrderedDict()


def suggest_binding(expression):
    """Generate code that would match the given expression."""
    pattern = re.sub(r'[A-Z][A-Z ]*[A-Z]', '*', expression)
    if pattern in SUGGESTED_BINDINGS:
        return
    func = re.sub(r'\s*\*\s*', ' ', pattern).strip()
    func = re.sub(r'\s+', '_', func.lower())
    func = re.sub(r'\W+', '', func)
    if not func:
        func = 'handler'

    num_args = pattern.count('*')
    if num_args == 1:
        args = ['character']
    elif num_args == 2:
        args = ['character', 'target']
    else:
        args = ('noun%d' % i for i in range(1,  + 1))

    code = """
@stagedirection({pattern!r})
def {func}({args}):
    raise NotImplementedError('{func} should return an action chain')
""".format(pattern=pattern, func=func, args=', '.join(args))
    SUGGESTED_BINDINGS[pattern] = code


def print_suggestions():
    if not SUGGESTED_BINDINGS:
        return
    print("\n\nSome stage direction bindings were missing.\n")
    print(
        "Below is skeleton code to implement the bindings. You will need to\n"
        "copy and paste this code, and change the function implementations\n"
        "to return appropriate action chains."
    )
    for pattern, code in SUGGESTED_BINDINGS.items():
        print(code)


def lookup_stagedirection(expression):
    """Look up a stage direction, returning a callable."""
    for pat, func in STAGE_DIRECTIONS:
        mo = pat.match(expression)
        if mo:
            params = mo.groups()
            required_args = func.__code__.co_argcount
            if required_args != len(params):
                raise ScriptError(
                    "Incorrect number of patterns for binding of %s (found %d, function takes %d)" % (
                        func.__qualname__, len(params), required_args
                    )
                )
            return func(*params)
    suggest_binding(expression)
    raise ScriptError("No stage direction found matching %r." % expression)
