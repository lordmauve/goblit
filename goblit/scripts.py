#!/usr/bin/env python3
"""Script system.

The entire script for the game is loaded from an RST-like file.

"""
import re
from collections import namedtuple

COMMENT_RE = re.compile(r'\s*#.*')
DIRECTIVE_RE = re.compile(r'.. ([\w-]+)::\s*(.+)?')
LINE_RE = re.compile(r'([A-Z ]+): (.*)')

PAUSE_RE = re.compile(r'\[pause\]')
ACTION_RE = re.compile(r'{(.*)}')
STAGE_DIRECTION_RE = re.compile(
    r'\[([A-Z ]+)? +(enters|leaves|appears|disappears|removes glasses)\]'
)
INDENT_RE = re.compile(r'^([ \t]+)(.*)')
UNDERLINE_RE = re.compile(r'^(-+|=+)')
TITLE_RE = re.compile(r'^(\w.*)')
GIFT_RE = re.compile(
    r'\[([A-Z ]+)? +gives +([A-Z ]+)\]'
)


class Pause:
    """A brief pause."""
    def __repr__(self):
        return '[pause]'


class Underline:
    def __init__(self, s):
        self.length = len(s)
        if s[0] == '=':
            self.level = 1
        else:
            self.level = 2


Action = namedtuple('Action', 'verb')
Line = namedtuple('Line', 'character line')
StageDirection = namedtuple('StageDirection', 'character verb')
Title = namedtuple('SceneTitle', 'name level')
Gift = namedtuple('Gift', 'character object')


class Directive:
    indent = None

    def __init__(self, name, data):
        self.name = name
        self.data = data
        self.contents = []

    def __repr__(self):
        return '<%s %r>' % (self.name, self.data)


TOKEN_TYPES = [
    (DIRECTIVE_RE, Directive),
    (LINE_RE, Line),
    (PAUSE_RE, Pause),
    (ACTION_RE, Action),
    (STAGE_DIRECTION_RE, StageDirection),
    (UNDERLINE_RE, Underline),
    (GIFT_RE, Gift)
]


def read_lines(file):
    with open(file, 'rU', encoding='utf8') as f:
        yield from f


def tokenize(lines):
    """Tokenise the lines."""
    for lineno, l in enumerate(lines, start=1):
        if COMMENT_RE.match(l) or not l.strip():
            continue
        l = l.rstrip()

        indent_mo = INDENT_RE.match(l)
        if indent_mo:
            indents, l = indent_mo.groups()
            indent = 0
            for c in indents:
                if c == ' ':
                    indent += 1
                elif c == '\t':
                    indent += 8 - (indent % 8)
        else:
            indent = 0
        for regex, cls in TOKEN_TYPES:
            mo = regex.match(l)
            if mo:
                yield lineno, indent, cls(*mo.groups())
                break
        else:
            if TITLE_RE.match(l):
                yield lineno, indent, l
            else:
                raise ParseError(
                    "Couldn't parse line %r" % l
                )


class Script:
    """A whole script."""
    indent = 0

    def __init__(self):
        self.contents = []

    def __repr__(self):
        return repr(self.contents)


class ParseError(Exception):
    """Failed to parse the script"""


def parse_file(file):
    """Parse a whole file."""
    directives = [Script()]
    lines = read_lines(file)
    last_indent = 0
    for lineno, indent, tok in tokenize(lines):
        top = directives[-1]

        if top.contents and isinstance(top.contents[-1], str):
            if isinstance(tok, Underline):
                if indent != last_indent:
                    raise ParseError('Unexpected indent (at line %d)' % lineno)
                lastlen = len(top.contents[-1])
                if tok.length > lastlen:
                    print(
                        "Warning: underline is too long (at line %d)" % lineno
                    )
                elif tok.length < lastlen:
                    print(
                        "Warning: underline is too short (at line %d)" % lineno
                    )

                top.contents[-1] = Title(top.contents[-1], tok.level)
                continue
            else:
                raise ParseError("Underline expected (at line %d)" % lineno)

        if indent == last_indent:
            if top.indent is None:
                directives.pop()
                top = directives[-1]
        elif indent > last_indent:
            if top.indent is None:
                top.indent = indent
            else:
                raise ParseError('Unexpected indent (at line %d)' % lineno)
        elif indent < last_indent:
            while directives:
                if top.indent is None or indent < top.indent:
                    directives.pop()
                    top = directives[-1]
                elif indent == top.indent:
                    break
            else:
                raise ParseError(
                    "Indent matches no previous indentation level "
                    "(at line %d)" % lineno
                )

        top.contents.append(tok)

        if isinstance(tok, Directive):
            directives.append(tok)

        last_indent = indent

    return directives[0].contents


if __name__ == '__main__':
    script = parse_file('script.txt')
    print(script)
